import frappe
from frappe.utils import flt


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
