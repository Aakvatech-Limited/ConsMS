"""Contract budget helpers: default buying rates, expense accounts, and the ERPNext Budget sync.

The BF Budget holds the quantity breakdown (items, qty, rate per BOQ line).
On submit it creates a standard ERPNext Budget for the project with the totals
per expense account, so ERPNext warns on Material Requests, Purchase Orders
and expenses that go over budget, and the Budget Variance report works.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate


@frappe.whitelist()
def get_item_buying_rate(item_code, uom=None):
	price_list = frappe.db.get_single_value("Buying Settings", "buying_price_list") or "Standard Buying"
	filters = {"item_code": item_code, "price_list": price_list}
	rate = None
	if uom:
		rate = frappe.db.get_value("Item Price", {**filters, "uom": uom}, "price_list_rate")
	rate = rate or frappe.db.get_value("Item Price", filters, "price_list_rate")
	if not rate:
		rate = frappe.db.get_value("Item", item_code, "valuation_rate") or frappe.db.get_value(
			"Item", item_code, "last_purchase_rate"
		)
	return flt(rate)


def get_expense_account(item_code, company):
	return frappe.db.get_value(
		"Item Default", {"parent": item_code, "company": company}, "expense_account"
	) or frappe.get_cached_value("Company", company, "default_expense_account")


def sync_erp_budget(bf_budget):
	"""Create the ERPNext Budget for this BF Budget (replacing the previous revision's)."""
	project = frappe.get_doc("Project", bf_budget.project)
	company = project.company
	totals = {}
	for row in bf_budget.items:
		account = row.expense_account or get_expense_account(row.item_code, company)
		totals[account] = totals.get(account, 0) + flt(row.amount)

	previous = bf_budget.amended_from and frappe.db.get_value("BF Budget", bf_budget.amended_from, "erp_budget")
	if previous and frappe.db.get_value("Budget", previous, "docstatus") == 1:
		frappe.get_doc("Budget", previous).cancel()

	from erpnext.accounts.utils import get_fiscal_year

	erp_budget = frappe.get_doc(
		{
			"doctype": "Budget",
			"budget_against": "Project",
			"project": project.name,
			"company": company,
			"fiscal_year": get_fiscal_year(nowdate(), company=company)[0],
			"applicable_on_material_request": 1,
			"action_if_annual_budget_exceeded_on_mr": "Warn",
			"action_if_accumulated_monthly_budget_exceeded_on_mr": "Ignore",
			"applicable_on_purchase_order": 1,
			"action_if_annual_budget_exceeded_on_po": "Warn",
			"action_if_accumulated_monthly_budget_exceeded_on_po": "Ignore",
			"applicable_on_booking_actual_expenses": 1,
			"action_if_annual_budget_exceeded": "Warn",
			"action_if_accumulated_monthly_budget_exceeded": "Ignore",
			"accounts": [{"account": a, "budget_amount": amt} for a, amt in totals.items() if amt],
		}
	)
	erp_budget.insert(ignore_permissions=True)
	erp_budget.submit()
	bf_budget.db_set("erp_budget", erp_budget.name)
	frappe.msgprint(_("ERPNext Budget {0} created for project {1}.").format(erp_budget.name, project.name), alert=True)


def cancel_erp_budget(bf_budget):
	if bf_budget.erp_budget and frappe.db.get_value("Budget", bf_budget.erp_budget, "docstatus") == 1:
		frappe.get_doc("Budget", bf_budget.erp_budget).cancel()
