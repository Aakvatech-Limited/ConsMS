"""Payment certificates (IPC / Substantial Completion / Final) and BOQ tender summaries.

The rules are not in the code: they come from a Certificate Template, a list of lines
worked out from top to bottom. Each line adds to or takes from a running total:

	Work this certificate                  Work This Certificate
	Less: Retention 10%                    10% of Work This Certificate, limit 5% of contract value
	Less: Advance recovery 30%             30% of Work to Date, less earlier certificates
	Add: Release of 50% retention          50% of Retention Held (Substantial Completion only)
	Add: VAT 18%                           18% of Work This Certificate (excl. VAT-Exempt)

The last running total is the amount due (or the bid price on a BOQ). A line's role
(Retention, Advance Recovery, VAT...) tells the rest of the system what it is, so the
contract balances, the invoice VAT and the reports keep working whatever the template.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, money_in_words

LINE_FIELDS = (
	"label", "line_type", "calculation", "rate", "percentage_of", "line_no", "deduct_previous",
	"limit", "limit_rate", "applies_to", "role", "calculation_only",
)
CERTIFICATE_TITLES = {
	"Interim": "Interim Payment Certificate",
	"Substantial Completion": "Substantial Completion Payment Certificate",
	"Final": "Final Payment Certificate",
}


def money(value):
	"""Round to cents half-up, like the clients' Excel certificates (116,334,289.925 -> .93)."""
	return float(Decimal(repr(round(flt(value), 6))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------- template lines

def applies(row, certificate_type):
	scope = row.applies_to or "All Certificates"
	kind = certificate_type or "Interim"
	return (
		scope == "All Certificates"
		or (scope == "Interim Only" and kind == "Interim")
		or (scope == "Substantial Completion" and kind == "Substantial Completion")
		or (scope == "Final" and kind == "Final")
		or (scope == "Substantial Completion and Final" and kind in ("Substantial Completion", "Final"))
	)


def build_lines(doc, table, template, certificate_type=None):
	"""Copy the template's lines onto the document, keeping amounts already typed on 'Typed Amount' lines."""
	typed = {row.label: flt(row.amount) for row in doc.get(table) or [] if row.calculation == "Typed Amount"}
	doc.set(table, [])
	if not template:
		return
	for row in frappe.get_doc("BF Certificate Template", template).lines:
		if certificate_type is not None and not applies(row, certificate_type):
			continue
		line = {field: row.get(field) for field in LINE_FIELDS}
		line["template_line_no"] = row.idx
		if row.calculation == "Typed Amount":
			line["amount"] = typed.get(row.label, 0)
		doc.append(table, line)


def run_lines(lines, bases, previous_by_label=None, previous_by_role=None, contract_value=0, advance=0):
	"""Work the lines out top to bottom. Returns (final total, amount per role)."""
	previous_by_label = previous_by_label or {}
	previous_by_role = previous_by_role or {}
	this_role = defaultdict(float)
	at_line = {}
	running = final = 0.0

	def retention_held():
		return (previous_by_role.get("Retention", 0) - previous_by_role.get("Retention Release", 0)
			+ this_role["Retention"] - this_role["Retention Release"])

	def advance_balance():
		return flt(advance) - previous_by_role.get("Advance Recovery", 0) - this_role["Advance Recovery"]

	for line in lines:
		line.base_amount = 0
		if line.line_type == "Subtotal":
			line.amount = money(running)
		else:
			if line.calculation == "Typed Amount":
				if flt(line.amount) < 0:
					frappe.throw(_("{0}: enter a positive amount; the line itself says whether it is added or taken off.").format(line.label))
				amount = flt(line.amount)
			elif line.calculation == "Percentage":
				base = {
					"Running Total": lambda: running,
					"Total at Line": lambda: at_line.get(cint(line.line_no), 0),
					"Retention Held": retention_held,
					"Advance Balance": advance_balance,
					"Contract Value": lambda: flt(contract_value),
				}.get(line.percentage_of, lambda: flt(bases.get(line.percentage_of)))()
				line.base_amount = money(base)
				amount = flt(line.rate) / 100 * base
			else:
				amount = flt(bases.get(line.calculation))

			if line.deduct_previous:
				amount -= previous_by_label.get(line.label, 0)

			if line.limit and amount > 0:
				if line.limit == "% of Contract Value":
					used = (previous_by_role.get(line.role, 0) + this_role[line.role]) if line.role else previous_by_label.get(line.label, 0)
					room = flt(line.limit_rate) / 100 * flt(contract_value) - used
				elif line.limit == "Advance Payment":
					room = advance_balance()
				else:
					room = retention_held()
				amount = min(amount, max(room, 0))

			line.amount = money(amount)
			sign = -1 if line.line_type == "Less" else 1
			running += sign * line.amount
			if not line.calculation_only:
				final += sign * line.amount
			if line.role:
				this_role[line.role] += line.amount

		line.running_total = money(running)
		line.previous_amount = money(previous_by_label.get(line.label, 0))
		line.to_date_amount = money(line.previous_amount + line.amount)
		at_line[cint(line.template_line_no) or line.idx] = running

	return money(final), this_role


def validate_template(template):
	work_bases = {"Work This Certificate", "Work This Certificate (excl. VAT-Exempt)", "Work to Date", "Retention Held", "Advance Balance"}
	allowed_calculations, blocked_bases = {
		"Payment Certificate": ({"Work This Certificate", "Percentage", "Typed Amount"}, {"Total of Bills", "Direct Cost", "BOQ Value"}),
		"BOQ Summary": ({"Total of Bills", "Provisional Sums", "Percentage", "Typed Amount"}, work_bases | {"Direct Cost", "BOQ Value"}),
		"Budget Overheads": ({"Direct Cost", "Percentage", "Typed Amount"}, work_bases | {"Total of Bills"}),
	}[template.used_for]
	for row in template.lines:
		if row.line_type == "Subtotal":
			continue
		if row.calculation not in allowed_calculations:
			frappe.throw(_("Line {0}: '{1}' cannot be used on a {2} template.").format(row.idx, row.calculation, _(template.used_for)))
		if row.calculation == "Percentage":
			if not row.percentage_of:
				frappe.throw(_("Line {0}: choose what the percentage is of.").format(row.idx))
			if row.percentage_of in blocked_bases:
				frappe.throw(_("Line {0}: '{1}' cannot be used on a {2} template.").format(row.idx, row.percentage_of, _(template.used_for)))
			if row.percentage_of == "Total at Line" and not 0 < cint(row.line_no) < row.idx:
				frappe.throw(_("Line {0}: Line No. must be one of the lines above.").format(row.idx))
		if row.limit == "% of Contract Value" and not flt(row.limit_rate):
			frappe.throw(_("Line {0}: enter the Limit (%).").format(row.idx))


# ---------------------------------------------------------------- payment certificates

def get_contract_terms(contract):
	return frappe.db.get_value(
		"BF Contract",
		contract,
		["total_contract_amount", "contract_amount", "advance_payment_amount", "certificate_template",
			"ld_rate_per_day", "original_completion_date", "revised_completion_date"],
		as_dict=True,
	) or frappe._dict()


def contract_value(terms):
	return flt(terms.total_contract_amount) or flt(terms.contract_amount)


def default_certificate_template(contract=None):
	return (
		(frappe.db.get_value("BF Contract", contract, "certificate_template") if contract else None)
		or frappe.db.get_single_value("BF Construction Settings", "default_certificate_template")
	)


def get_previous_totals(claim):
	"""Totals of the submitted certificates of the same contract before this one."""
	totals = frappe.db.sql(
		"""
		select
			coalesce(sum(retention_deduction), 0) as retention,
			coalesce(sum(retention_release), 0) as released,
			coalesce(sum(advance_payment_recovery), 0) as advance,
			coalesce(sum(liquidated_damages), 0) as liquidated_damages,
			coalesce(sum(materials_on_site), 0) as materials,
			coalesce(sum(vat_amount), 0) as vat,
			coalesce(sum(net_amount_due), 0) as net
		from `tabBF Progress Claim`
		where contract = %s and claim_type = %s and docstatus = 1 and name != %s
		""",
		(claim.contract, claim.claim_type or "Client Claim", claim.name or ""),
		as_dict=True,
	)[0]
	return frappe._dict({k: flt(v) for k, v in totals.items()})


def get_previous_by_label(claim):
	rows = frappe.db.sql(
		"""
		select line.label, sum(line.amount) as amount
		from `tabBF Certificate Line` line
		join `tabBF Progress Claim` claim on claim.name = line.parent
		where line.parenttype = 'BF Progress Claim' and claim.contract = %s and claim.claim_type = %s
			and claim.docstatus = 1 and claim.name != %s
		group by line.label
		""",
		(claim.contract, claim.claim_type or "Client Claim", claim.name or ""),
		as_dict=True,
	)
	return {r.label: flt(r.amount) for r in rows}


def calculate(claim):
	terms = get_contract_terms(claim.contract) if claim.contract else frappe._dict()
	value = contract_value(terms)

	work_to_date = this_work = taxable_work = 0.0
	for item in claim.claim_items:
		item.previous_value = money(flt(item.previous_qty) * flt(item.unit_rate))
		item.this_period_value = money(flt(item.this_period_qty) * flt(item.unit_rate))
		item.cumulative_qty = flt(item.previous_qty) + flt(item.this_period_qty)
		item.cumulative_value = money(flt(item.cumulative_qty) * flt(item.unit_rate))
		work_to_date += item.cumulative_value
		this_work += item.this_period_value
		if not item.vat_exempt:
			taxable_work += item.this_period_value

	variations_to_date = this_variations = 0.0
	for row in claim.get("variations") or []:
		row.cumulative_amount = flt(row.previously_certified) + flt(row.this_period_amount)
		variations_to_date += flt(row.cumulative_amount)
		this_variations += flt(row.this_period_amount)

	claim.total_work_executed = money(work_to_date)
	claim.approved_variations = money(variations_to_date)
	claim.gross_valuation = money(work_to_date + variations_to_date)
	claim.this_period_work = money(this_work + this_variations)

	if not claim.certificate_template:
		claim.certificate_template = default_certificate_template(claim.contract)
	rebuild = not claim.get("certificate_lines") or (
		not claim.is_new() and (claim.has_value_changed("certificate_template") or claim.has_value_changed("certificate_type"))
	)
	if rebuild:
		build_lines(claim, "certificate_lines", claim.certificate_template, claim.certificate_type or "Interim")

	previous = get_previous_totals(claim)
	advance = flt(terms.advance_payment_amount)
	bases = {
		"Work This Certificate": claim.this_period_work,
		"Work This Certificate (excl. VAT-Exempt)": money(taxable_work + this_variations),
		"Work to Date": claim.gross_valuation,
	}
	previous_by_role = {
		"Retention": previous.retention,
		"Retention Release": previous.released,
		"Advance Recovery": previous.advance,
		"Liquidated Damages": previous.liquidated_damages,
		"Materials on Site": previous.materials,
		"VAT": previous.vat,
	}

	if claim.certificate_lines:
		total, roles = run_lines(claim.certificate_lines, bases, get_previous_by_label(claim), previous_by_role, value, advance)
	else:
		total, roles = claim.this_period_work, defaultdict(float)

	claim.materials_on_site = money(roles["Materials on Site"])
	claim.retention_deduction = money(roles["Retention"])
	claim.retention_release = money(roles["Retention Release"])
	claim.advance_payment_recovery = money(roles["Advance Recovery"])
	claim.liquidated_damages = money(roles["Liquidated Damages"])
	claim.vat_amount = money(roles["VAT"])
	claim.vat_base = money(sum(flt(line.base_amount) for line in claim.certificate_lines if line.role == "VAT"))
	claim.amount_due = total
	claim.net_amount_due = money(total - claim.vat_amount)
	claim.previous_certified_amount = money(previous.net)

	claim.retention_held_to_date = money(previous.retention - previous.released + claim.retention_deduction - claim.retention_release)
	claim.advance_recovered_to_date = money(previous.advance + claim.advance_payment_recovery)
	claim.advance_balance = money(advance - claim.advance_recovered_to_date) if advance else 0


def suggest_liquidated_damages(claim):
	"""Days of this period after the revised completion date x the contract's rate per day."""
	terms = get_contract_terms(claim.contract)
	completion = terms.revised_completion_date or terms.original_completion_date
	if not (flt(terms.ld_rate_per_day) and completion and claim.period_to):
		return 0

	late_from = add_days(completion, 1)
	if claim.period_from and getdate(claim.period_from) > getdate(late_from):
		late_from = claim.period_from
	days = date_diff(claim.period_to, late_from) + 1
	return money(days * flt(terms.ld_rate_per_day)) if days > 0 else 0


def set_liquidated_damages(claim):
	"""Put the suggested amount on the template's typed Liquidated Damages line, if it has one."""
	suggestion = suggest_liquidated_damages(claim)
	for line in claim.certificate_lines:
		if line.role == "Liquidated Damages" and line.calculation == "Typed Amount":
			line.amount = suggestion
			return


def update_contract_balances(contract):
	terms = get_contract_terms(contract)
	totals = frappe.db.sql(
		"""
		select
			coalesce(sum(retention_deduction), 0) as retention,
			coalesce(sum(retention_release), 0) as released,
			coalesce(sum(advance_payment_recovery), 0) as advance,
			coalesce(sum(liquidated_damages), 0) as liquidated_damages
		from `tabBF Progress Claim`
		where contract = %s and docstatus = 1
		""",
		contract,
		as_dict=True,
	)[0]
	advance = flt(terms.advance_payment_amount)
	frappe.db.set_value(
		"BF Contract",
		contract,
		{
			"advance_recovered": money(totals.advance),
			"advance_balance": money(advance - flt(totals.advance)) if advance else 0,
			"retention_held": money(flt(totals.retention) - flt(totals.released)),
			"retention_released": money(totals.released),
			"liquidated_damages_to_date": money(totals.liquidated_damages),
		},
		update_modified=False,
	)


# ---------------------------------------------------------------- BOQ tender summary

def calculate_boq_summary(boq):
	"""Bid price from the BOQ Summary template: total of bills, provisional sums, contingency, VAT..."""
	if not boq.summary_template:
		boq.set("summary_lines", [])
		boq.bid_price = boq.total_amount
		return
	if not boq.summary_lines or (not boq.is_new() and boq.has_value_changed("summary_template")):
		build_lines(boq, "summary_lines", boq.summary_template)
	bases = {
		"Total of Bills": flt(boq.total_amount),
		"Provisional Sums": sum(flt(row.amount) for row in boq.items if row.is_provisional_sum),
	}
	boq.bid_price, _roles = run_lines(boq.summary_lines, bases, contract_value=flt(boq.total_amount))


# ---------------------------------------------------------------- printing

def get_ipc_print_data(claim):
	"""Everything the IPC print formats need: certificate lines, valuation per bill, summary per bill."""
	contract = frappe.get_doc("BF Contract", claim.contract) if claim.contract else None
	rows_by_item = {row.boq_item: row for row in claim.claim_items}

	boq_items = []
	if claim.boq:
		boq_items = frappe.get_all(
			"BF BOQ Item",
			filters={"parent": claim.boq},
			fields=["name", "item_no", "description", "bill", "uom", "quantity", "unit_rate", "amount", "vat_exempt"],
			order_by="idx",
		)

	bills, by_bill = [], {}
	for item in boq_items:
		bill = item.bill or _("General Items")
		if bill not in by_bill:
			by_bill[bill] = frappe._dict(
				name=bill, rows=[], original=0.0, previous=0.0, this=0.0, cumulative=0.0, vat_exempt=True
			)
			bills.append(by_bill[bill])
		row = rows_by_item.get(item.name)
		line = frappe._dict(
			name=item.name,
			item_no=item.item_no,
			description=item.description,
			uom=item.uom,
			quantity=flt(item.quantity),
			rate=flt(item.unit_rate),
			amount=flt(item.amount),
			previous_qty=flt(row.previous_qty) if row else 0,
			previous_value=flt(row.previous_value) if row else 0,
			this_qty=flt(row.this_period_qty) if row else 0,
			this_value=flt(row.this_period_value) if row else 0,
			cumulative_qty=flt(row.cumulative_qty) if row else 0,
			cumulative_value=flt(row.cumulative_value) if row else 0,
		)
		group = by_bill[bill]
		group.rows.append(line)
		group.original += line.amount
		group.previous += line.previous_value
		group.this += line.this_value
		group.cumulative += line.cumulative_value
		group.vat_exempt = group.vat_exempt and bool(item.vat_exempt)

	for group in bills:
		group.percent = group.cumulative / group.original * 100 if group.original else 0

	def total(key, exempt=None):
		return sum(g[key] for g in bills if exempt is None or g.vat_exempt == exempt)

	# VAT rows on the summary only when the template charges VAT on the work excluding exempt bills
	vat_line = next(
		(l for l in claim.certificate_lines if l.role == "VAT" and l.percentage_of == "Work This Certificate (excl. VAT-Exempt)"), None
	)
	vat_rate = flt(vat_line.rate) / 100 if vat_line else 0
	summary = frappe._dict(
		original=total("original"),
		previous=total("previous"),
		this=total("this"),
		cumulative=total("cumulative"),
		taxable={k: total(k, False) for k in ("original", "previous", "this", "cumulative")},
		exempt={k: total(k, True) for k in ("original", "previous", "this", "cumulative")},
	)
	summary.vat = {k: summary.taxable[k] * vat_rate for k in summary.taxable}
	summary.grand = {k: summary.taxable[k] + summary.vat[k] + summary.exempt[k] for k in summary.taxable}
	summary.percent = summary.cumulative / summary.original * 100 if summary.original else 0

	variations = flt(
		frappe.db.sql(
			"select sum(requested_amount) from `tabBF Variation Order` where contract = %s and docstatus = 1",
			claim.contract,
		)[0][0]
	) if claim.contract else 0
	company = frappe.db.get_value("Project", claim.project, "company") if claim.project else None
	currency = frappe.get_cached_value("Company", company, "default_currency") if company else None

	# payment split over currencies (e.g. 15% TZS, 85% USD at the contract's rate)
	currencies = []
	for row in (contract.payment_currencies if contract else []):
		share = flt(claim.amount_due) * flt(row.share_percentage) / 100
		currencies.append(frappe._dict(currency=row.currency, share=flt(row.share_percentage), rate=flt(row.exchange_rate) or 1,
			amount=money(share / (flt(row.exchange_rate) or 1))))

	return frappe._dict(
		currencies=currencies,
		boq_summary=get_boq_summary_columns(claim, bills, summary, by_bill),
		title=_(CERTIFICATE_TITLES.get(claim.certificate_type or "Interim")),
		contract=contract,
		project_name=frappe.db.get_value("Project", claim.project, "project_name") if claim.project else "",
		company=company,
		client=claim.customer or claim.supplier,
		original_value=contract_value(contract) if contract else 0,
		revised_value=(contract_value(contract) + variations) if contract and variations else None,
		bills=bills,
		summary=summary,
		vat_line=vat_line,
		has_exempt=bool(vat_line) and any(g.vat_exempt for g in bills),
		amount_in_words=money_in_words(claim.amount_due, currency),
	)


class LineHolder:
	"""Just enough of a document for build_lines / run_lines, for working out lines without saving them."""

	def __init__(self):
		self.lines = []

	def get(self, _table):
		return self.lines

	def set(self, _table, rows):
		self.lines = list(rows)

	def append(self, _table, values):
		row = frappe._dict(values, idx=len(self.lines) + 1)
		self.lines.append(row)
		return row


def get_boq_summary_columns(claim, bills, summary, by_bill):
	"""The BOQ's tender summary (A-I lines) worked out for each column of the certificate summary, plus the balance."""
	template = frappe.db.get_value("BF Bill of Quantities", claim.boq, "summary_template") if claim.boq else None
	if not template:
		return None
	typed = {l.label: flt(l.amount) for l in frappe.get_all("BF Certificate Line",
		filters={"parent": claim.boq, "parenttype": "BF Bill of Quantities"}, fields=["label", "amount"])}
	provisional = set(frappe.get_all("BF BOQ Item", filters={"parent": claim.boq, "is_provisional_sum": 1}, pluck="name"))

	def provisional_total(key):
		return sum(row[key] for group in bills for row in group.rows if row.name in provisional)

	columns = {"original": ("amount", summary.original), "previous": ("previous_value", summary.previous),
		"this": ("this_value", summary.this), "cumulative": ("cumulative_value", summary.cumulative)}
	results = {}
	for column, (row_key, total) in columns.items():
		holder = LineHolder()
		build_lines(holder, "lines", template)
		for line in holder.lines:
			if line.calculation == "Typed Amount":
				line.amount = typed.get(line.label, 0) if column == "original" else 0
		final, _roles = run_lines(holder.lines, {"Total of Bills": total, "Provisional Sums": provisional_total(row_key)},
			contract_value=summary.original)
		results[column] = ([money(l.amount) for l in holder.lines], final)
	labels = [(l.label, l.line_type) for l in frappe.get_doc("BF Certificate Template", template).lines]
	rows = []
	for i, (label, line_type) in enumerate(labels):
		values = {c: results[c][0][i] for c in results}
		values["balance"] = values["original"] - values["cumulative"]
		rows.append(frappe._dict(label=label, line_type=line_type, **values))
	totals = frappe._dict({c: results[c][1] for c in results})
	totals["balance"] = totals["original"] - totals["cumulative"]
	return frappe._dict(rows=rows, totals=totals)
