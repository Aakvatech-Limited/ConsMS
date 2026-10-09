import frappe
from frappe import _
from frappe.utils import flt


def warn_if_over_boq(doc, method=None):
	"""Warn when a Material Request asks for more than is left on a BOQ line."""
	requested_now = {}
	for row in doc.items:
		if row.get("bf_boq_item"):
			requested_now[row.bf_boq_item] = requested_now.get(row.bf_boq_item, 0) + flt(row.stock_qty)

	for boq_item, qty in requested_now.items():
		line = frappe.db.get_value("BF BOQ Item", boq_item, ["description", "quantity", "requested_qty", "uom"], as_dict=True)
		if not line:
			continue

		remaining = flt(line.quantity) - flt(line.requested_qty)
		if qty > remaining:
			frappe.msgprint(
				_("{0}: requesting {1} {2}, but only {3} is left on the BOQ (BOQ qty {4}, already requested {5}).").format(
					frappe.bold(line.description), qty, line.uom or "", remaining, line.quantity, line.requested_qty
				),
				title=_("More than the BOQ quantity"),
				indicator="orange",
			)


def update_boq_requested_qty(doc, method=None):
	"""Recalculate Requested Qty on the BOQ lines used in this Material Request."""
	boq_items = {row.bf_boq_item for row in doc.items if row.get("bf_boq_item")}
	for boq_item in boq_items:
		requested = frappe.db.sql(
			"""
			select coalesce(sum(mri.stock_qty), 0)
			from `tabMaterial Request Item` mri
			join `tabMaterial Request` mr on mr.name = mri.parent
			where mri.bf_boq_item = %s and mr.docstatus = 1
			""",
			boq_item,
		)[0][0]
		frappe.db.set_value("BF BOQ Item", boq_item, "requested_qty", flt(requested), update_modified=False)
