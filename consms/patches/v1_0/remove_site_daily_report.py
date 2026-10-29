"""The Site Daily Report is removed: site work will be recorded on Tasks (Works Execution).

The Stock Issues the reports made stay in stock and in the books, with their project, task and BOQ line.
The reports, their materials table and the workspace shortcut are removed.
"""

import frappe

DOCTYPES = ("BF Site Daily Report", "BF Daily Material")


def execute():
	frappe.db.set_value("ToDo", {"reference_type": DOCTYPES[0], "status": "Open"}, "status", "Cancelled")
	for doctype in DOCTYPES:
		frappe.delete_doc_if_exists("DocType", doctype, force=True)
		if frappe.db.table_exists(doctype):
			frappe.db.sql_ddl(f"drop table `tab{doctype}`")
	for link_doctype, field in (("Workspace Link", "link_to"), ("Workspace Shortcut", "link_to"), ("Number Card", "document_type")):
		frappe.db.delete(link_doctype, {field: DOCTYPES[0]})
