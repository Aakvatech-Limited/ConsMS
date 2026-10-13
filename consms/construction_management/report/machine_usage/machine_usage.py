# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{"label": _("Machine"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 170},
		{"label": _("Asset"), "fieldname": "asset", "fieldtype": "Link", "options": "Asset", "width": 140},
		{"label": _("Asset Status"), "fieldname": "asset_status", "fieldtype": "Data", "width": 120},
		{"label": _("Last Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},
		{"label": _("Last Contract"), "fieldname": "contract", "fieldtype": "Link", "options": "BF Contract", "width": 150},
		{"label": _("Last Used"), "fieldname": "last_used", "fieldtype": "Date", "width": 100},
		{"label": _("Mobilization Status"), "fieldname": "mobilization_status", "fieldtype": "Data", "width": 130},
		{"label": _("Days Used"), "fieldname": "days_used", "fieldtype": "Int", "width": 90},
		{"label": _("Quantity Used"), "fieldname": "qty_used", "fieldtype": "Float", "width": 110},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 70},
		{"label": _("Fuel (L)"), "fieldname": "fuel", "fieldtype": "Float", "width": 90},
		{"label": _("Cost"), "fieldname": "cost", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	conditions = ["r.docstatus = 1"]
	values = {}
	for field, column in (("from_date", "r.date >= %(from_date)s"), ("to_date", "r.date <= %(to_date)s"),
			("project", "r.project = %(project)s"), ("asset", "p.asset = %(asset)s")):
		if filters.get(field):
			conditions.append(column)
			values[field] = filters.get(field)

	rows = frappe.db.sql(
		f"""
		select p.item_code, p.asset, p.uom, p.hours, p.fuel_litres, p.amount, r.date, r.project, r.contract
		from `tabBF Daily Plant` p
		join `tabBF Site Daily Report` r on r.name = p.parent
		where {" and ".join(conditions)}
		order by r.date
		""",
		values,
		as_dict=True,
	)

	machines = {}
	for row in rows:
		key = (row.item_code, row.asset or "")
		m = machines.setdefault(key, frappe._dict(item_code=row.item_code, asset=row.asset, uom=row.uom, dates=set(),
			qty_used=0, fuel=0, cost=0))
		m.dates.add(row.date)
		m.qty_used += flt(row.hours)
		m.fuel += flt(row.fuel_litres)
		m.cost += flt(row.amount)
		m.update(last_used=row.date, project=row.project, contract=row.contract)

	data = []
	for m in machines.values():
		m.days_used = len(m.pop("dates"))
		if m.asset:
			m.asset_status = frappe.db.get_value("Asset", m.asset, "status")
		m.mobilization_status = get_mobilization_status(m)
		data.append(m)
	return sorted(data, key=lambda d: d.last_used, reverse=True)


def get_mobilization_status(machine):
	"""Latest status of this machine in a Site Mobilization's Labour & Equipment plan."""
	filters = {"parenttype": "BF Site Mobilization", "resource_type": "Plant"}
	filters.update({"asset": machine.asset} if machine.asset else {"item_code": machine.item_code})
	row = frappe.get_all("BF Mobilization Resource", filters=filters, fields=["status"], order_by="modified desc", limit=1)
	return row[0].status if row else None


def get_summary(data):
	return [
		{"value": len(data), "indicator": "Blue", "label": _("Machines Used"), "datatype": "Int"},
		{"value": sum(flt(d.qty_used) for d in data), "indicator": "Blue", "label": _("Total Quantity Used"), "datatype": "Float"},
		{"value": sum(flt(d.fuel) for d in data), "indicator": "Orange", "label": _("Fuel (Litres)"), "datatype": "Float"},
		{"value": sum(flt(d.cost) for d in data), "indicator": "Red", "label": _("Machine Cost"), "datatype": "Currency"},
	]
