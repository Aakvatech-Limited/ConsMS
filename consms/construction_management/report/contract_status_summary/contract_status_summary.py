# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_report_summary(data)


def get_columns():
	return [
		{"label": _("Contract"), "fieldname": "contract", "fieldtype": "Link", "options": "BF Contract", "width": 160},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
		{"label": _("Client / Subcontractor"), "fieldname": "party", "fieldtype": "Data", "width": 170},
		{"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 140},
		{"label": _("Approved Variations"), "fieldname": "variations", "fieldtype": "Currency", "width": 140},
		{"label": _("Revised Value"), "fieldname": "revised_value", "fieldtype": "Currency", "width": 140},
		{"label": _("Measured to Date"), "fieldname": "measured", "fieldtype": "Currency", "width": 140},
		{"label": _("Work Certified"), "fieldname": "work_certified", "fieldtype": "Currency", "width": 140},
		{"label": _("% Complete"), "fieldname": "percent_complete", "fieldtype": "Percent", "width": 100},
		{"label": _("Retention Held"), "fieldname": "retention", "fieldtype": "Currency", "width": 130},
		{"label": _("Paid / Payable"), "fieldname": "net_certified", "fieldtype": "Currency", "width": 140},
		{"label": _("Invoiced"), "fieldname": "invoiced", "fieldtype": "Currency", "width": 130},
		{"label": _("Balance to Complete"), "fieldname": "balance", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	contract_filters = {"docstatus": 1}
	for field in ("project", "customer", "contract_type"):
		if filters.get(field):
			contract_filters[field] = filters.get(field)

	contracts = frappe.get_all(
		"BF Contract",
		filters=contract_filters,
		fields=["name", "project", "customer", "supplier", "total_contract_amount", "boq"],
		order_by="creation desc",
	)
	if not contracts:
		return []

	names = [c.name for c in contracts]
	variations = get_sum_by_contract("BF Variation Order", "requested_amount", names)
	net_certified = get_sum_by_contract("BF Progress Claim", "net_amount_due", names)
	invoiced = get_invoiced(names)
	measured = get_measured(names)
	latest_claims = get_latest_claims(names)

	data = []
	for c in contracts:
		claim = latest_claims.get(c.name, {})
		revised_value = flt(c.total_contract_amount) + flt(variations.get(c.name))
		work_certified = flt(claim.get("gross_valuation"))
		data.append(
			{
				"contract": c.name,
				"project": c.project,
				"party": c.customer or c.supplier,
				"contract_value": c.total_contract_amount,
				"variations": variations.get(c.name, 0),
				"revised_value": revised_value,
				"measured": measured.get(c.name, 0),
				"work_certified": work_certified,
				"percent_complete": work_certified / revised_value * 100 if revised_value else 0,
				"retention": claim.get("retention_deduction", 0),
				"net_certified": net_certified.get(c.name, 0),
				"invoiced": invoiced.get(c.name, 0),
				"balance": revised_value - work_certified,
			}
		)
	return data


def get_sum_by_contract(doctype, field, contracts):
	rows = frappe.get_all(
		doctype,
		filters={"contract": ["in", contracts], "docstatus": 1},
		fields=["contract", f"sum({field}) as total"],
		group_by="contract",
	)
	return {r.contract: flt(r.total) for r in rows}


def get_invoiced(contracts):
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"bf_contract": ["in", contracts], "docstatus": 1},
		fields=["bf_contract", "sum(net_total) as total"],
		group_by="bf_contract",
	)
	return {r.bf_contract: flt(r.total) for r in rows}


def get_measured(contracts):
	"""Value of submitted site measurements: quantity x BOQ unit rate."""
	rows = frappe.db.sql(
		"""
		select log.contract, sum(mi.total_quantity * boq_item.unit_rate) as total
		from `tabBF Site Measurement Log` log
		join `tabBF Measurement Item` mi on mi.parent = log.name
		join `tabBF BOQ Item` boq_item on boq_item.name = mi.boq_item
		where log.docstatus = 1 and log.contract in %(contracts)s
		group by log.contract
		""",
		{"contracts": contracts},
		as_dict=True,
	)
	return {r.contract: flt(r.total) for r in rows}


def get_latest_claims(contracts):
	"""Progress claims hold cumulative values, so only the latest one per contract counts."""
	claims = frappe.get_all(
		"BF Progress Claim",
		filters={"contract": ["in", contracts], "docstatus": 1},
		fields=["contract", "gross_valuation", "retention_deduction"],
		order_by="posting_date desc, creation desc",
	)
	latest = {}
	for claim in claims:
		latest.setdefault(claim.contract, claim)
	return latest


def get_chart(data):
	if not data:
		return None

	return {
		"data": {
			"labels": [d["contract"] for d in data],
			"datasets": [
				{"name": _("Revised Value"), "values": [d["revised_value"] for d in data]},
				{"name": _("Work Certified"), "values": [d["work_certified"] for d in data]},
			],
		},
		"type": "bar",
		"fieldtype": "Currency",
		"colors": ["#93c5fd", "#16a34a"],
	}


def get_report_summary(data):
	revised = sum(flt(d["revised_value"]) for d in data)
	certified = sum(flt(d["work_certified"]) for d in data)
	return [
		{"value": len(data), "indicator": "Blue", "label": _("Contracts"), "datatype": "Int"},
		{"value": revised, "indicator": "Blue", "label": _("Revised Contract Value"), "datatype": "Currency"},
		{"value": certified, "indicator": "Green", "label": _("Work Certified"), "datatype": "Currency"},
		{
			"value": sum(flt(d["retention"]) for d in data),
			"indicator": "Orange",
			"label": _("Retention Held"),
			"datatype": "Currency",
		},
		{
			"value": certified / revised * 100 if revised else 0,
			"indicator": "Green",
			"label": _("Overall % Complete"),
			"datatype": "Percent",
		},
	]
