"""Give existing submitted contracts their own site store."""

import frappe

from consms.construction_management.doctype.bf_contract.bf_contract import get_or_create_site_store


def execute():
	for c in frappe.get_all("BF Contract", filters={"docstatus": 1, "site_warehouse": ["is", "not set"]}, fields=["name", "project"]):
		company = c.project and frappe.db.get_value("Project", c.project, "company")
		if company:
			frappe.db.set_value("BF Contract", c.name, "site_warehouse", get_or_create_site_store(c.project, company), update_modified=False)
