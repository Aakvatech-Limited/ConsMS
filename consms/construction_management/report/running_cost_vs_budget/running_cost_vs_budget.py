# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from consms.construction_management.progress import get_actual_cost, get_budget_cost, get_measured_qty


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data, budget = get_data(filters.contract)
	message = None if budget else _("This contract has no submitted Budget yet, so budget figures are empty.")
	return get_columns(), data, message, get_chart(data), get_summary(data)


def get_columns():
	return [
		{"label": _("BOQ Work Item"), "fieldname": "description", "fieldtype": "Data", "width": 280},
		{"label": _("Budget Cost"), "fieldname": "budget", "fieldtype": "Currency", "width": 130},
		{"label": _("% Work Done"), "fieldname": "percent_done", "fieldtype": "Percent", "width": 100},
		{"label": _("Budget for Work Done"), "fieldname": "earned", "fieldtype": "Currency", "width": 150,
		 "description": "What the work done so far should have cost."},
		{"label": _("Actual Cost"), "fieldname": "actual", "fieldtype": "Currency", "width": 130},
		{"label": _("% Budget Spent"), "fieldname": "percent_spent", "fieldtype": "Percent", "width": 110},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
	]


def get_data(contract):
	boq = frappe.db.get_value("BF Contract", contract, "boq")
	if not boq:
		return [], None
	done = get_measured_qty(contract)
	budget_name, budget = get_budget_cost(contract)
	actual = get_actual_cost(contract)
	data = []
	for line in frappe.get_all("BF BOQ Item", filters={"parent": boq}, fields=["name", "description", "quantity"], order_by="idx"):
		pct = done.get(line.name, 0) / flt(line.quantity) * 100 if flt(line.quantity) else 0
		data.append(make_row(line.description, budget.get(line.name, 0), min(pct, 100), actual.get(line.name, 0)))
	unallocated = actual.get(None, 0) + actual.get("", 0)
	if unallocated:
		row = make_row(_("Costs not linked to a BOQ line"), 0, 0, unallocated)
		row["status"] = _("Not linked to BOQ")
		data.append(row)
	return data, budget_name


def make_row(description, budget, percent_done, actual):
	earned = budget * percent_done / 100
	variance = earned - actual
	if not actual and not percent_done:
		status = _("Not started")
	elif variance >= 0:
		status = _("On budget")
	else:
		status = _("Over budget")
	return {
		"description": description,
		"budget": budget,
		"percent_done": percent_done,
		"earned": earned,
		"actual": actual,
		"percent_spent": actual / budget * 100 if budget else 0,
		"variance": variance,
		"status": status,
	}


def get_chart(data):
	rows = [d for d in data if d["actual"] or d["earned"]]
	if not rows:
		return None
	return {
		"data": {
			"labels": [d["description"][:30] for d in rows],
			"datasets": [
				{"name": _("Budget for Work Done"), "values": [d["earned"] for d in rows]},
				{"name": _("Actual Cost"), "values": [d["actual"] for d in rows]},
			],
		},
		"type": "bar",
		"fieldtype": "Currency",
		"colors": ["#93c5fd", "#dc2626"],
	}


def get_summary(data):
	budget = sum(d["budget"] for d in data)
	earned = sum(d["earned"] for d in data)
	actual = sum(d["actual"] for d in data)
	return [
		{"value": budget, "indicator": "Blue", "label": _("Total Budget"), "datatype": "Currency"},
		{"value": earned / budget * 100 if budget else 0, "indicator": "Green", "label": _("% Work Done (by budget)"), "datatype": "Percent"},
		{"value": actual / budget * 100 if budget else 0, "indicator": "Orange", "label": _("% Budget Spent"), "datatype": "Percent"},
		{"value": actual, "indicator": "Red", "label": _("Actual Cost"), "datatype": "Currency"},
		{"value": earned - actual, "indicator": "Green" if earned >= actual else "Red", "label": _("Cost Variance"), "datatype": "Currency"},
	]
