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
		{"fieldname": "contract", "label": _("Contract"), "fieldtype": "Link", "options": "BF Contract", "width": 150},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 150},
		{"fieldname": "customer", "label": _("Client"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "base_value", "label": _("Base Value"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "variations", "label": _("Variations"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "revised_value", "label": _("Revised Value"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "client_billed", "label": _("Billed to Client"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "subcontractor_costs", "label": _("Subcontractor Costs"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "estimated_profit", "label": _("Estimated Profit"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "actual_profit", "label": _("Actual Profit (To Date)"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "profit_margin", "label": _("Actual Margin %"), "fieldtype": "Percent", "width": 120}
	]

def get_data(filters):
	conditions = ""
	if filters.get("project"):
		conditions += f" AND project = '{filters.get('project')}'"

	contracts = frappe.db.sql(f"""
		SELECT name, project, customer, contract_amount 
		FROM `tabBF Contract` 
		WHERE docstatus = 1 AND contract_type = 'Main Contract' {conditions}
	""", as_dict=1)

	data = []
	for c in contracts:
		# Variations
		vars_total = frappe.db.sql("""
			SELECT SUM(requested_amount) FROM `tabBF Variation Order` 
			WHERE contract = %s AND docstatus = 1
		""", c.name)[0][0] or 0.0

		revised_value = flt(c.contract_amount) + flt(vars_total)

		# Client Revenue Billed (Progress Claims where claim_type is Client Claim)
		# Wait, better to sum the actual Sales Invoices linked to this contract!
		client_billed = frappe.db.sql("""
			SELECT SUM(grand_total) FROM `tabSales Invoice` 
			WHERE bf_contract = %s AND docstatus = 1
		""", c.name)[0][0] or 0.0

		# Subcontractor Costs (Purchase Invoices linked to this contract OR to its subcontracts)
		sub_costs = frappe.db.sql("""
			SELECT SUM(grand_total) FROM `tabPurchase Invoice` 
			WHERE (bf_contract = %s 
			   OR bf_contract IN (SELECT name FROM `tabBF Contract` WHERE main_contract = %s AND docstatus = 1))
			AND docstatus = 1
		""", (c.name, c.name))[0][0] or 0.0

		estimated_profit = revised_value - sub_costs
		actual_profit = flt(client_billed) - flt(sub_costs)
		margin = (actual_profit / client_billed * 100) if client_billed else 0.0

		data.append({
			"contract": c.name,
			"project": c.project,
			"customer": c.customer,
			"base_value": c.contract_amount,
			"variations": vars_total,
			"revised_value": revised_value,
			"client_billed": client_billed,
			"subcontractor_costs": sub_costs,
			"estimated_profit": estimated_profit,
			"actual_profit": actual_profit,
			"profit_margin": margin
		})
		
	return data
