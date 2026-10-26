"""BF Contract Profitability is replaced by Contract Profitability (profit from all project costs, without VAT)."""

import frappe


def execute():
	frappe.delete_doc_if_exists("Report", "BF Contract Profitability", force=True)
	frappe.db.delete("Workspace Link", {"link_to": "BF Contract Profitability"})
	frappe.db.delete("Workspace Shortcut", {"link_to": "BF Contract Profitability"})
