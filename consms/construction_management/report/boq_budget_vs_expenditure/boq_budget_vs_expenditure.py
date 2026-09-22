# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	return [
		{"fieldname": "boq", "label": _("BOQ"), "fieldtype": "Link", "options": "BF Bill of Quantities", "width": 140},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 140},
		{"fieldname": "boq_item", "label": _("BOQ Item Ref"), "fieldtype": "Data", "width": 140},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 260},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 80},
		{"fieldname": "quantity", "label": _("Budget Qty"), "fieldtype": "Float", "width": 110},
		{"fieldname": "unit_rate", "label": _("Unit Rate"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "budget_amount", "label": _("Budget Amount"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "committed_cost", "label": _("Committed Cost (PO)"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "actual_expenditure", "label": _("Actual Spend (PI)"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "budget_balance", "label": _("Remaining Budget"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "utilization_pct", "label": _("Utilization %"), "fieldtype": "Percent", "width": 110}
	]

def get_data(filters):
	filters = filters or {}
	conditions = []
	params = {}

	if filters.get("project"):
		conditions.append("parent.project = %(project)s")
		params["project"] = filters.get("project")

	if filters.get("boq"):
		conditions.append("child.parent = %(boq)s")
		params["boq"] = filters.get("boq")

	where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

	items = frappe.db.sql(f"""
		SELECT 
			child.name as boq_item,
			child.parent as boq,
			parent.project as project,
			child.description as description,
			child.uom as uom,
			child.quantity as quantity,
			child.unit_rate as unit_rate,
			child.amount as budget_amount
		FROM `tabBF BOQ Item` child
		INNER JOIN `tabBF Bill of Quantities` parent ON child.parent = parent.name
		{where_clause}
		ORDER BY parent.name ASC, child.idx ASC
	""", params, as_dict=True)

	data = []
	for item in items:
		# 1. Committed cost from Purchase Orders
		committed = frappe.db.sql("""
			SELECT SUM(amount) FROM `tabPurchase Order Item`
			WHERE bf_boq_item = %s AND docstatus = 1
		""", item.boq_item)[0][0] or 0.0

		# 2. Actual expenditure from Purchase Invoices
		actual = frappe.db.sql("""
			SELECT SUM(amount) FROM `tabPurchase Invoice Item`
			WHERE bf_boq_item = %s AND docstatus = 1
		""", item.boq_item)[0][0] or 0.0

		budget_amount = flt(item.budget_amount)
		committed_cost = flt(committed)
		actual_expenditure = flt(actual)

		remaining = budget_amount - actual_expenditure
		utilization = (actual_expenditure / budget_amount * 100.0) if budget_amount else 0.0

		data.append({
			"boq": item.boq,
			"project": item.project,
			"boq_item": item.boq_item,
			"description": item.description,
			"uom": item.uom,
			"quantity": flt(item.quantity),
			"unit_rate": flt(item.unit_rate),
			"budget_amount": budget_amount,
			"committed_cost": committed_cost,
			"actual_expenditure": actual_expenditure,
			"budget_balance": remaining,
			"utilization_pct": utilization
		})

	return data
