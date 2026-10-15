"""Construction Types and measurement formulas are gone: site measurements record the quantity and a drawing as proof."""

import frappe


def execute():
	if frappe.db.table_exists("BF Construction Type"):
		frappe.db.sql_ddl("drop table `tabBF Construction Type`")
	frappe.db.delete("DocType", {"name": "BF Construction Type"})
	frappe.db.delete("Workspace Link", {"link_to": "BF Construction Type"})
	frappe.db.delete("Workspace Shortcut", {"link_to": "BF Construction Type"})
