"""Budget control stays on BF Budget only: remove the ERPNext Budgets that BF Budget used to create."""

import frappe


def execute():
	if not frappe.db.has_column("BF Budget", "erp_budget"):
		return

	for name in frappe.db.sql_list("select distinct erp_budget from `tabBF Budget` where ifnull(erp_budget, '') != ''"):
		if not frappe.db.exists("Budget", name):
			continue
		budget = frappe.get_doc("Budget", name)
		if budget.docstatus == 1:
			budget.flags.ignore_links = True
			budget.cancel()
		frappe.delete_doc("Budget", name, force=True, ignore_permissions=True)

	frappe.db.sql("update `tabBF Budget` set erp_budget = null")
