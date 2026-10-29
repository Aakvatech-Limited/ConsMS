# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""One row per task of a project: % done and its cost from the books."""

import frappe
from frappe import _

from consms.construction_management.task_activity import get_activity


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.project:
		return get_columns(), [], _("Select a Project to see its tasks.")
	tasks = frappe.get_all(
		"Task",
		filters={"project": filters.project, "is_template": 0},
		fields=["name", "subject", "status", "progress", "exp_start_date", "exp_end_date"],
		order_by="lft, creation",
	)
	activity = get_activity([t.name for t in tasks], filters.from_date, filters.to_date)
	data = []
	for t in tasks:
		a = activity[t.name]
		data.append({
			"task": t.name,
			"subject": t.subject,
			"status": t.status,
			"progress": t.progress,
			"materials_cost": a.materials_cost,
			"other_cost": a.other_cost,
			"total_cost": a.total_cost,
			"exp_end_date": t.exp_end_date,
		})
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{"label": _("Task"), "fieldname": "task", "fieldtype": "Link", "options": "Task", "width": 120},
		{"label": _("Subject"), "fieldname": "subject", "fieldtype": "Data", "width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("% Done"), "fieldname": "progress", "fieldtype": "Percent", "width": 90},
		{"label": _("Materials Cost"), "fieldname": "materials_cost", "fieldtype": "Currency", "width": 130,
		 "description": "Materials issued from the site store to the task, at the value the books hold."},
		{"label": _("Other Costs"), "fieldname": "other_cost", "fieldtype": "Currency", "width": 130,
		 "description": "Labour, machine hire and services booked to the task (supplier invoices, journals)."},
		{"label": _("Total Cost"), "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": _("Expected End"), "fieldname": "exp_end_date", "fieldtype": "Date", "width": 110},
	]


def get_summary(data):
	return [
		{"value": sum(1 for d in data if d["total_cost"]), "indicator": "Blue", "label": _("Tasks with Costs"), "datatype": "Int"},
		{"value": sum(d["materials_cost"] for d in data), "indicator": "Green", "label": _("Materials Cost"), "datatype": "Currency"},
		{"value": sum(d["other_cost"] for d in data), "indicator": "Orange", "label": _("Other Costs"), "datatype": "Currency"},
		{"value": sum(d["total_cost"] for d in data), "indicator": "Red", "label": _("Total Cost"), "datatype": "Currency"},
	]
