import frappe
from frappe import _
from frappe.utils import flt


def warn_if_over_budget(doc, method=None):
	"""Warn when a Material Request asks for more than is left on a budget line."""
	requested_now = {}
	for row in doc.items:
		if row.get("bf_budget_item"):
			requested_now[row.bf_budget_item] = requested_now.get(row.bf_budget_item, 0) + flt(row.stock_qty)

	for budget_item, qty in requested_now.items():
		line = frappe.db.get_value(
			"BF Budget Item", budget_item, ["item_code", "boq_description", "qty", "requested_qty", "uom"], as_dict=True
		)
		if not line:
			continue

		remaining = flt(line.qty) - flt(line.requested_qty)
		if qty > remaining:
			frappe.msgprint(
				_("{0} for {1}: requesting {2} {3}, but only {4} is left in the budget (budget {5}, already requested {6}).").format(
					frappe.bold(line.item_code), line.boq_description, qty, line.uom or "", remaining, line.qty, line.requested_qty
				),
				title=_("More than the budget quantity"),
				indicator="orange",
			)


def update_budget_requested_qty(doc, method=None):
	"""Recalculate Requested Qty on the budget lines used in this Material Request."""
	for budget_item in {row.bf_budget_item for row in doc.items if row.get("bf_budget_item")}:
		requested = frappe.db.sql(
			"""
			select coalesce(sum(mri.stock_qty), 0)
			from `tabMaterial Request Item` mri
			join `tabMaterial Request` mr on mr.name = mri.parent
			where mri.bf_budget_item = %s and mr.docstatus = 1
			""",
			budget_item,
		)[0][0]
		frappe.db.set_value("BF Budget Item", budget_item, "requested_qty", flt(requested), update_modified=False)
