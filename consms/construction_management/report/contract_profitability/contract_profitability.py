# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""Per main contract: the profit the budget expects, and the profit so far from the books.

Billed is the certificates' invoices without VAT (the advance payment invoice is not income). Cost to
date is every expense booked to the project: materials issued, subcontractors, labour gangs, machine
hire and anything else, so it matches Running Cost vs Budget.
"""

import frappe
from frappe import _
from frappe.utils import flt

from consms.construction_management.progress import get_actual_cost


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{"label": _("Contract"), "fieldname": "contract", "fieldtype": "Link", "options": "BF Contract", "width": 160},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
		{"label": _("Client"), "fieldtype": "Link", "fieldname": "customer", "options": "Customer", "width": 140},
		{"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 140,
		 "description": "The BOQ value, without VAT."},
		{"label": _("Variations"), "fieldname": "variations", "fieldtype": "Currency", "width": 120},
		{"label": _("Revised Value"), "fieldname": "revised_value", "fieldtype": "Currency", "width": 140},
		{"label": _("Budget Cost"), "fieldname": "budget_cost", "fieldtype": "Currency", "width": 140,
		 "description": "From the submitted budget, with overheads and unplanned site costs."},
		{"label": _("Estimated Profit"), "fieldname": "estimated_profit", "fieldtype": "Currency", "width": 140},
		{"label": _("Billed (excl. VAT)"), "fieldname": "billed", "fieldtype": "Currency", "width": 140},
		{"label": _("Cost to Date"), "fieldname": "cost_to_date", "fieldtype": "Currency", "width": 140,
		 "description": "All expenses booked to the project."},
		{"label": _("Profit to Date"), "fieldname": "profit_to_date", "fieldtype": "Currency", "width": 140},
		{"label": _("Margin to Date"), "fieldname": "margin_to_date", "fieldtype": "Percent", "width": 110},
	]


def get_data(filters):
	conditions = {"docstatus": 1, "contract_type": "Main Contract"}
	if filters.project:
		conditions["project"] = filters.project
	if filters.customer:
		conditions["customer"] = filters.customer

	data = []
	for c in frappe.get_all("BF Contract", filters=conditions, fields=["name", "project", "customer", "contract_amount"], order_by="name"):
		variations = flt(frappe.db.sql(
			"select sum(requested_amount) from `tabBF Variation Order` where contract = %s and docstatus = 1", c.name)[0][0])
		revised_value = flt(c.contract_amount) + variations
		budget = frappe.db.get_value("BF Budget", {"contract": c.name, "docstatus": 1},
			["total_budget_cost", "total_with_overheads", "unplanned_amount"], as_dict=True)
		budget_cost = (flt(budget.total_with_overheads) or flt(budget.total_budget_cost)) + flt(budget.unplanned_amount) if budget else None
		billed = flt(frappe.db.sql(
			"""select sum(net_total) from `tabSales Invoice`
			where bf_contract = %s and docstatus = 1 and ifnull(bf_advance_payment, 0) = 0""", c.name)[0][0])
		cost = sum(get_actual_cost(c.name).values())
		profit = billed - cost
		data.append({
			"contract": c.name,
			"project": c.project,
			"customer": c.customer,
			"contract_value": flt(c.contract_amount),
			"variations": variations,
			"revised_value": revised_value,
			"budget_cost": budget_cost,
			"estimated_profit": revised_value - budget_cost if budget else None,
			"billed": billed,
			"cost_to_date": cost,
			"profit_to_date": profit,
			"margin_to_date": profit / billed * 100 if billed else None,
		})
	return data


def get_summary(data):
	billed = sum(flt(d["billed"]) for d in data)
	profit = sum(flt(d["profit_to_date"]) for d in data)
	return [
		{"value": sum(flt(d["revised_value"]) for d in data), "indicator": "Blue", "label": _("Revised Value"), "datatype": "Currency"},
		{"value": sum(flt(d["estimated_profit"]) for d in data), "indicator": "Blue", "label": _("Estimated Profit"), "datatype": "Currency"},
		{"value": billed, "indicator": "Green", "label": _("Billed (excl. VAT)"), "datatype": "Currency"},
		{"value": sum(flt(d["cost_to_date"]) for d in data), "indicator": "Orange", "label": _("Cost to Date"), "datatype": "Currency"},
		{"value": profit, "indicator": "Green" if profit >= 0 else "Red", "label": _("Profit to Date"), "datatype": "Currency"},
	]
