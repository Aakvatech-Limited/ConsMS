"""Contract budget helpers: default buying rates and expense accounts.

The BF Budget holds the quantity breakdown (items, qty, rate per BOQ line); budget
control is done on it directly (Material Request warnings, Running Cost vs Budget).
"""

import frappe
from frappe.utils import flt, nowdate


@frappe.whitelist()
def get_item_buying_rate(item_code, uom=None):
	price_list = frappe.db.get_single_value("Buying Settings", "buying_price_list") or "Standard Buying"
	# the latest price already valid today (Item Price "Valid From")
	filters = {"item_code": item_code, "price_list": price_list, "valid_from": ["<=", nowdate()]}
	order = "valid_from desc, modified desc"
	rate = None
	if uom:
		rate = frappe.db.get_value("Item Price", {**filters, "uom": uom}, "price_list_rate", order_by=order)
	rate = rate or frappe.db.get_value("Item Price", filters, "price_list_rate", order_by=order)
	if not rate:
		rate = frappe.db.get_value("Item", item_code, "valuation_rate") or frappe.db.get_value(
			"Item", item_code, "last_purchase_rate"
		)
	return flt(rate)


def get_expense_account(item_code, company):
	return frappe.db.get_value(
		"Item Default", {"parent": item_code, "company": company}, "expense_account"
	) or frappe.get_cached_value("Company", company, "default_expense_account")
