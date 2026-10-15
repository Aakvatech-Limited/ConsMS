"""Variations in BOQ terms.

Each BOQ line keeps its Original Qty (as tendered). Approved Variation Orders add or take
quantity (Variation Qty) or add new lines, which gives the Revised Qty: the most that may
be measured on the line (plus the contract's tolerance). Every approved Variation Order is
recorded as a new revision of the BOQ, so the history of the quantities is kept.
"""

import frappe
from frappe import _
from frappe.utils import flt, today

from consms.construction_management.ipc import money


# ---------------------------------------------------------------- BOQ quantities

def set_revised_quantities(boq):
	"""Original Qty = Quantity while the BOQ is a draft; Revised = Original + approved variations."""
	for row in boq.items:
		if boq.docstatus == 0 and not row.variation_order:
			row.original_qty = flt(row.quantity)
		row.revised_qty = flt(row.original_qty) + flt(row.variation_qty)
		row.revised_amount = money(row.revised_qty * flt(row.unit_rate))
	boq.revised_total = money(sum(flt(row.revised_amount) for row in boq.items))
	boq.variations_total = money(boq.revised_total - flt(boq.total_amount))


def refresh_boq(boq_name):
	"""Recalculate revised quantities and totals of a submitted BOQ without touching anything else."""
	boq = frappe.get_doc("BF Bill of Quantities", boq_name)
	set_revised_quantities(boq)
	for row in boq.items:
		row.db_update()
	boq.db_set({"revised_total": boq.revised_total, "variations_total": boq.variations_total}, update_modified=False)
	return boq


def measured_to_date(contract, boq_items, exclude_log=None):
	"""Quantity measured per BOQ line on submitted measurement logs of the contract."""
	if not boq_items:
		return {}
	rows = frappe.db.sql(
		"""
		select mi.boq_item, sum(mi.total_quantity) as qty
		from `tabBF Measurement Item` mi
		join `tabBF Site Measurement Log` log on log.name = mi.parent
		where log.contract = %(contract)s and log.docstatus = 1 and mi.boq_item in %(items)s and log.name != %(exclude)s
		group by mi.boq_item
		""",
		{"contract": contract, "items": list(boq_items), "exclude": exclude_log or ""},
		as_dict=True,
	)
	return {r.boq_item: flt(r.qty) for r in rows}


def get_over_limit(log):
	"""Lines of a measurement log that go beyond the revised BOQ quantity (+ tolerance)."""
	quantities = {}
	for row in log.measurements:
		quantities[row.boq_item] = quantities.get(row.boq_item, 0) + flt(row.total_quantity)
	if not quantities:
		return []
	tolerance = flt(frappe.db.get_value("BF Contract", log.contract, "measurement_tolerance"))
	before = measured_to_date(log.contract, quantities, exclude_log=log.name)
	lines = frappe.get_all(
		"BF BOQ Item",
		filters={"name": ["in", list(quantities)]},
		fields=["name", "item_no", "description", "uom", "unit_rate", "revised_qty"],
	)
	over = []
	for line in lines:
		total = before.get(line.name, 0) + quantities[line.name]
		allowed = flt(line.revised_qty) * (1 + tolerance / 100)
		if quantities[line.name] > 0 and total > allowed + 1e-9:
			excess = total - flt(line.revised_qty)
			over.append(frappe._dict(
				boq_item=line.name, item_no=line.item_no, description=line.description, uom=line.uom,
				unit_rate=flt(line.unit_rate), revised_qty=flt(line.revised_qty), measured=total,
				excess=excess, excess_amount=money(excess * flt(line.unit_rate)),
			))
	return over


def over_limit_message(over):
	return "<br>".join(
		_("{0}: measured to date {1} {2} is more than the revised BOQ quantity {3} (over by {4} = {5}).").format(
			frappe.bold(f"{o.item_no or ''} {(o.description or '')[:60]}".strip()), flt(o.measured, 3), o.uom or "",
			flt(o.revised_qty, 3), flt(o.excess, 3), frappe.format_value(o.excess_amount, "Currency"))
		for o in over
	)


@frappe.whitelist()
def make_variation_order_from_measurement(measurement_log):
	"""A Variation Order prefilled with the quantities measured beyond the revised BOQ."""
	log = frappe.get_doc("BF Site Measurement Log", measurement_log)
	log.check_permission("read")
	over = get_over_limit(log)
	if not over:
		frappe.throw(_("No line of this measurement goes beyond the revised BOQ quantity."))
	vo = frappe.new_doc("BF Variation Order")
	vo.contract, vo.project, vo.measurement_log = log.contract, log.project, log.name
	vo.reason = _("Quantities measured on site ({0}) exceed the BOQ.").format(log.name)
	for o in over:
		vo.append("items", {"change_type": "Change to BOQ Line", "boq_item": o.boq_item, "quantity": o.excess})
	# saved straight away as a draft, so the prefilled lines are never lost on the way to the form
	vo.insert()
	return vo.name


# ---------------------------------------------------------------- applying a Variation Order

def apply_variation(vo, sign):
	"""sign = 1 on approval (submit), -1 on cancel."""
	boq = frappe.get_doc("BF Bill of Quantities", vo.boq)
	if boq.docstatus != 1:
		frappe.throw(_("Submit the BOQ {0} before approving variations on it.").format(vo.boq))
	rows = {row.name: row for row in boq.items}
	measured = measured_to_date(vo.contract, [l.boq_item for l in vo.items if l.boq_item])

	for line in vo.items:
		if line.change_type == "Change to BOQ Line":
			row = rows[line.boq_item]
			new_variation = flt(row.variation_qty) + sign * flt(line.quantity)
			if flt(row.original_qty) + new_variation < measured.get(row.name, 0) - 1e-9:
				frappe.throw(_("{0}: {1} is already measured; the revised quantity cannot go below it.").format(
					row.item_no or row.description, measured.get(row.name, 0)))
			frappe.db.set_value("BF BOQ Item", row.name, "variation_qty", new_variation, update_modified=False)

		elif line.change_type == "New Item":
			if sign > 0:
				new = frappe.get_doc({
					"doctype": "BF BOQ Item", "parent": boq.name, "parenttype": "BF Bill of Quantities", "parentfield": "items",
					"idx": len(boq.items) + 1, "item_no": line.item_no, "description": line.description, "bill": line.bill or _("Additional Works"),
					"uom": line.uom, "quantity": 0, "unit_rate": line.unit_rate, "amount": 0, "original_qty": 0,
					"variation_qty": line.quantity, "variation_order": vo.name,
				})
				from consms.construction_management.uom import resolve_uom
				new.erp_uom = resolve_uom(line.uom)
				new.db_insert()
				boq.items.append(new)
				line.db_set("boq_item", new.name)
			elif line.boq_item:
				if measured.get(line.boq_item):
					frappe.throw(_("{0} is already measured, so this Variation Order cannot be cancelled.").format(line.description))
				frappe.db.delete("BF BOQ Item", line.boq_item)
				line.db_set("boq_item", None)

	boq = refresh_boq(boq.name)
	if sign > 0:
		frappe.get_doc({
			"doctype": "BF BOQ Revision", "parent": boq.name, "parenttype": "BF Bill of Quantities", "parentfield": "revisions",
			"idx": len(boq.revisions) + 1, "revision_no": len(boq.revisions) + 1, "variation_order": vo.name,
			"approval_date": vo.approval_date, "client_instruction_no": vo.client_instruction_no,
			"change_amount": money(flt(vo.requested_amount) - flt(vo.lump_sum_amount)), "revised_total": boq.revised_total,
		}).db_insert()
	else:
		frappe.db.set_value("BF BOQ Revision", {"parent": boq.name, "variation_order": vo.name}, "status", "Cancelled")
	update_contract_variations(vo.contract)


def update_contract_variations(contract):
	approved = flt(frappe.db.sql(
		"select sum(requested_amount) from `tabBF Variation Order` where contract = %s and docstatus = 1", contract)[0][0])
	value = flt(frappe.db.get_value("BF Contract", contract, "total_contract_amount"))
	frappe.db.set_value("BF Contract", contract, {"approved_variations": approved, "revised_contract_value": value + approved},
		update_modified=False)


# ---------------------------------------------------------------- budget

def get_current_budget(contract):
	return frappe.db.get_value("BF Budget", {"contract": contract, "docstatus": 1}, "name")


def get_budget_rate_analysis(contract, boq_item):
	budget = get_current_budget(contract)
	if not budget:
		return None
	return frappe.db.get_value("BF Budget BOQ Line", {"parent": budget, "boq_item": boq_item}, "applied_rate_analysis")


@frappe.whitelist()
def make_budget_revision(variation_order):
	"""New version of the contract's budget with the approved variation's quantities and new items."""
	vo = frappe.get_doc("BF Variation Order", variation_order)
	vo.check_permission("read")
	if vo.docstatus != 1:
		frappe.throw(_("Approve (submit) the Variation Order first."))
	current = get_current_budget(vo.contract)
	if not current:
		frappe.throw(_("This contract has no submitted budget yet. Create the budget from the contract."))
	old = frappe.get_doc("BF Budget", current)
	old.check_permission("cancel")
	old.cancel()

	new = frappe.copy_doc(old)
	new.amended_from = old.name
	new.revision_reason = _("Variation Order {0} ({1}) approved {2}").format(
		vo.name, vo.client_instruction_no or "", frappe.utils.formatdate(vo.approval_date or today()))
	# the budget follows all approved variations of the contract, not only this one
	recipes = {}
	for approved in frappe.get_all("BF Variation Order", filters={"contract": vo.contract, "docstatus": 1}, pluck="name", order_by="creation"):
		for l in frappe.get_doc("BF Variation Order", approved).items:
			if l.boq_item and l.rate_analysis:
				recipes[l.boq_item] = l.rate_analysis
	new.build_boq_lines()
	for line in new.boq_lines:
		if line.boq_item in recipes and not line.rate_analysis:
			line.rate_analysis = recipes[line.boq_item]
	new.insert()
	return new.name
