"""Interim Payment Certificates (IPC) the way Tanzanian clients certify them.

Each certificate pays the work of its own period:

	work this certificate (+ variations this period)
	+ materials on site
	- retention        (retention % of the work, until the contract's retention limit is held)
	- advance recovery (recovery % of the work, until the advance is recovered)
	+ retention released
	- liquidated damages
	= amount due (excl. VAT)
	+ VAT              (VAT % of the work, excluding VAT-exempt BOQ lines such as P&G)
	= amount due to contractor

Previous and cumulative values are kept on the claim lines for the valuation sheet.
"""

from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, money_in_words


def money(value):
	"""Round to cents half-up, like the clients' Excel certificates (116,334,289.925 -> .93)."""
	return float(Decimal(repr(round(flt(value), 6))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_contract_terms(contract):
	return frappe.db.get_value(
		"BF Contract",
		contract,
		[
			"total_contract_amount",
			"contract_amount",
			"retention_percentage",
			"retention_limit_percentage",
			"advance_payment_amount",
			"advance_recovery_percentage",
			"vat_percentage",
			"ld_rate_per_day",
			"ld_limit_percentage",
			"original_completion_date",
			"revised_completion_date",
		],
		as_dict=True,
	) or frappe._dict()


def contract_value(terms):
	return flt(terms.total_contract_amount) or flt(terms.contract_amount)


def get_previous_totals(claim):
	"""Totals of the submitted certificates of the same contract before this one."""
	totals = frappe.db.sql(
		"""
		select
			coalesce(sum(retention_deduction), 0) as retention,
			coalesce(sum(retention_release), 0) as released,
			coalesce(sum(advance_payment_recovery), 0) as advance,
			coalesce(sum(liquidated_damages), 0) as liquidated_damages,
			coalesce(sum(net_amount_due), 0) as net
		from `tabBF Progress Claim`
		where contract = %s and claim_type = %s and docstatus = 1 and name != %s
		""",
		(claim.contract, claim.claim_type or "Client Claim", claim.name or ""),
		as_dict=True,
	)[0]
	return frappe._dict({k: flt(v) for k, v in totals.items()})


def calculate(claim):
	terms = get_contract_terms(claim.contract) if claim.contract else frappe._dict()
	value = contract_value(terms)

	work_to_date = this_work = vat_base = 0.0
	for item in claim.claim_items:
		item.previous_value = money(flt(item.previous_qty) * flt(item.unit_rate))
		item.this_period_value = money(flt(item.this_period_qty) * flt(item.unit_rate))
		item.cumulative_qty = flt(item.previous_qty) + flt(item.this_period_qty)
		item.cumulative_value = money(flt(item.cumulative_qty) * flt(item.unit_rate))
		work_to_date += item.cumulative_value
		this_work += item.this_period_value
		if not item.vat_exempt:
			vat_base += item.this_period_value

	variations_to_date = this_variations = 0.0
	for row in claim.get("variations") or []:
		row.cumulative_amount = flt(row.previously_certified) + flt(row.this_period_amount)
		variations_to_date += flt(row.cumulative_amount)
		this_variations += flt(row.this_period_amount)

	claim.total_work_executed = money(work_to_date)
	claim.approved_variations = money(variations_to_date)
	claim.gross_valuation = money(work_to_date + variations_to_date)
	claim.this_period_work = money(this_work + this_variations)

	previous = get_previous_totals(claim)
	base = claim.this_period_work

	# Retention: % of this certificate's work, never more than the limit in total
	retention = flt(claim.retention_percentage) / 100 * base
	if flt(terms.retention_limit_percentage) and value:
		room = flt(terms.retention_limit_percentage) / 100 * value - previous.retention
		retention = min(retention, max(room, 0))
	claim.retention_deduction = money(retention)

	# Advance: % of this certificate's work, until the advance is recovered
	advance = flt(terms.advance_payment_amount)
	recovery = 0.0
	if advance:
		claim.advance_recovery_percentage = flt(terms.advance_recovery_percentage)
		recovery = flt(terms.advance_recovery_percentage) / 100 * base
		recovery = max(min(recovery, advance - previous.advance), -previous.advance)
	claim.advance_payment_recovery = money(recovery)

	held_before = previous.retention - previous.released
	if flt(claim.retention_release) < 0:
		frappe.throw(_("Retention Released cannot be negative."))
	if money(claim.retention_release) > money(held_before + claim.retention_deduction):
		frappe.throw(
			_("Retention Released ({0}) is more than the retention held ({1}).").format(
				frappe.format_value(claim.retention_release, "Currency"),
				frappe.format_value(held_before + claim.retention_deduction, "Currency"),
			)
		)

	if flt(claim.liquidated_damages) < 0:
		frappe.throw(_("Liquidated Damages cannot be negative."))
	if flt(terms.ld_limit_percentage) and value:
		ld_room = flt(terms.ld_limit_percentage) / 100 * value - previous.liquidated_damages
		if money(claim.liquidated_damages) > money(max(ld_room, 0)):
			frappe.throw(
				_("Liquidated Damages are limited to {0}% of the contract value; at most {1} can still be deducted.").format(
					flt(terms.ld_limit_percentage), frappe.format_value(max(ld_room, 0), "Currency")
				)
			)

	claim.vat_base = money(vat_base + this_variations)
	claim.vat_amount = money(flt(claim.vat_percentage) / 100 * claim.vat_base)

	claim.net_amount_due = money(
		claim.this_period_work
		+ money(claim.materials_on_site)
		- claim.retention_deduction
		- claim.advance_payment_recovery
		+ money(claim.retention_release)
		- money(claim.liquidated_damages)
	)
	claim.amount_due = money(claim.net_amount_due + claim.vat_amount)
	claim.previous_certified_amount = money(previous.net)

	claim.retention_held_to_date = money(held_before + claim.retention_deduction - flt(claim.retention_release))
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


def get_ipc_print_data(claim):
	"""Everything the IPC print formats need: valuation per bill, summary per bill, contract details."""
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

	vat_rate = flt(claim.vat_percentage) / 100
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

	return frappe._dict(
		contract=contract,
		project_name=frappe.db.get_value("Project", claim.project, "project_name") if claim.project else "",
		company=company,
		client=claim.customer or claim.supplier,
		original_value=contract_value(contract) if contract else 0,
		revised_value=(contract_value(contract) + variations) if contract and variations else None,
		bills=bills,
		summary=summary,
		has_exempt=any(g.vat_exempt for g in bills),
		amount_in_words=money_in_words(claim.amount_due, currency),
	)
