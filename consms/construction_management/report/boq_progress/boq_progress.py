# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from consms.construction_management.progress import get_measured_qty


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters.contract)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
	return [
		{"label": _("BOQ Work Item"), "fieldname": "description", "fieldtype": "Data", "width": 300},
		{"label": _("Unit"), "fieldname": "unit", "fieldtype": "Data", "width": 70},
		{"label": _("Original Qty"), "fieldname": "original_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Variation Qty"), "fieldname": "variation_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Revised Qty"), "fieldname": "boq_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Done to Date"), "fieldname": "done_qty", "fieldtype": "Float", "width": 110},
		{"label": _("% Done"), "fieldname": "percent_done", "fieldtype": "Percent", "width": 90},
		{"label": _("Remaining Qty"), "fieldname": "remaining_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 120},
		{"label": _("Value Done"), "fieldname": "value_done", "fieldtype": "Currency", "width": 140},
		{"label": _("Value Remaining"), "fieldname": "value_remaining", "fieldtype": "Currency", "width": 140},
	]


def get_data(contract):
	boq = frappe.db.get_value("BF Contract", contract, "boq")
	if not boq:
		return []
	done = get_measured_qty(contract)
	data = []
	for line in frappe.get_all("BF BOQ Item", filters={"parent": boq}, fields=["name", "description", "uom", "quantity", "unit_rate", "original_qty", "variation_qty", "revised_qty"], order_by="idx"):
		qty, done_qty, rate = flt(line.revised_qty or line.quantity), done.get(line.name, 0), flt(line.unit_rate)
		data.append({
			"description": line.description,
			"unit": line.uom,
			"original_qty": flt(line.original_qty),
			"variation_qty": flt(line.variation_qty),
			"boq_qty": qty,
			"done_qty": done_qty,
			"percent_done": done_qty / qty * 100 if qty else 0,
			"remaining_qty": max(qty - done_qty, 0),
			"rate": rate,
			"value_done": done_qty * rate,
			"value_remaining": max(qty - done_qty, 0) * rate,
		})
	return data


def get_chart(data):
	started = [d for d in data if d["done_qty"]]
	if not started:
		return None
	return {
		"data": {"labels": [d["description"][:30] for d in started], "datasets": [{"name": _("% Done"), "values": [round(d["percent_done"], 1) for d in started]}]},
		"type": "bar",
		"colors": ["#16a34a"],
	}


def get_summary(data):
	total = sum(d["boq_qty"] * d["rate"] for d in data)
	done = sum(d["value_done"] for d in data)
	return [
		{"value": total, "indicator": "Blue", "label": _("Revised BOQ Value"), "datatype": "Currency"},
		{"value": done, "indicator": "Green", "label": _("Value of Work Done"), "datatype": "Currency"},
		{"value": total - done, "indicator": "Orange", "label": _("Value Remaining"), "datatype": "Currency"},
		{"value": done / total * 100 if total else 0, "indicator": "Green", "label": _("Overall % Done"), "datatype": "Percent"},
		{"value": sum(1 for d in data if d["done_qty"]), "indicator": "Blue", "label": _("Lines Started"), "datatype": "Int"},
	]
