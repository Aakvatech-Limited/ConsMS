"""Drop the tables of doctypes removed from ConsMS once their data has been moved by earlier patches."""

import frappe

REMOVED = [
	"BF Contract Extension",  # -> BF Extension of Time
	"BF Mobilization Task",  # -> ERPNext Task
	"BF Mobilization Template",  # -> Project Template
	"BF Mobilization Template Task",
	"BF Site Mobilization",  # -> BF Works Execution
	"BF Site Mobilization Item",
	"BF Mobilization Resource",
	"BF Construction Type",
]


def execute():
	for doctype in REMOVED:
		if frappe.db.exists("DocType", doctype):
			continue
		if frappe.db.table_exists(doctype):
			frappe.db.sql_ddl(f"drop table `tab{doctype}`")
		for link_doctype, field in (("Workspace Link", "link_to"), ("Workspace Shortcut", "link_to"), ("Number Card", "document_type"), ("Dashboard Chart", "document_type")):
			frappe.db.delete(link_doctype, {field: doctype})
