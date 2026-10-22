"""Two hidden fields left from an early version (the BOQ link before it was renamed). Nothing uses them."""

import frappe


def execute():
	for fieldname in ("ge_boq", "ge_boq_item"):
		for name in frappe.get_all("Custom Field", filters={"dt": "Material Request Item", "fieldname": fieldname}, pluck="name"):
			frappe.delete_doc("Custom Field", name, force=True)
