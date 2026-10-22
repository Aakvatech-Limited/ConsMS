"""BOQ Budget vs Expenditure is now part of Running Cost vs Budget (committed and actual cost per BOQ line)."""

import frappe

REPORT = "BOQ Budget vs Expenditure"


def execute():
	frappe.delete_doc_if_exists("Report", REPORT, force=True)
	frappe.db.delete("Workspace Link", {"link_to": REPORT})
	frappe.db.delete("Workspace Shortcut", {"link_to": REPORT})
