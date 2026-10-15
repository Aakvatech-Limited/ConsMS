"""Fill the new ERP UOM on existing BOQ lines from their BOQ unit text."""

import frappe

from consms.construction_management.uom import ensure_standard_uom_mappings, get_uom_map, resolve_uom


def execute():
	ensure_standard_uom_mappings()
	uom_map = get_uom_map()
	for row in frappe.get_all("BF BOQ Item", filters={"erp_uom": ["is", "not set"]}, fields=["name", "uom"]):
		uom = resolve_uom(row.uom, uom_map)
		if uom:
			frappe.db.set_value("BF BOQ Item", row.name, "erp_uom", uom, update_modified=False)
