# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""One row per task of a project: % done, days on site, man-days, machine time and materials cost."""

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
			"days_worked": a.days_worked,
			"first_day": a.first_day,
			"last_day": a.last_day,
			"man_days": a.man_days,
			"machine_hours": a.machine_hours,
			"machine_days": a.machine_days,
			"materials_cost": a.materials_cost,
			"exp_end_date": t.exp_end_date,
		})
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{"label": _("Task"), "fieldname": "task", "fieldtype": "Link", "options": "Task", "width": 120},
		{"label": _("Subject"), "fieldname": "subject", "fieldtype": "Data", "width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("% Done"), "fieldname": "progress", "fieldtype": "Percent", "width": 90},
		{"label": _("Days on Site"), "fieldname": "days_worked", "fieldtype": "Int", "width": 100},
		{"label": _("First Day"), "fieldname": "first_day", "fieldtype": "Date", "width": 100},
		{"label": _("Last Day"), "fieldname": "last_day", "fieldtype": "Date", "width": 100},
		{"label": _("Man-days"), "fieldname": "man_days", "fieldtype": "Float", "precision": 1, "width": 100},
		{"label": _("Machine Hours"), "fieldname": "machine_hours", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("Machine Days"), "fieldname": "machine_days", "fieldtype": "Float", "precision": 1, "width": 100},
		{"label": _("Materials Cost"), "fieldname": "materials_cost", "fieldtype": "Currency", "width": 130,
		 "description": "Materials issued from the site store to the task, at the value the books hold."},
		{"label": _("Expected End"), "fieldname": "exp_end_date", "fieldtype": "Date", "width": 110},
	]


def get_summary(data):
	return [
		{"value": sum(1 for d in data if d["days_worked"]), "indicator": "Blue", "label": _("Tasks with Site Work"), "datatype": "Int"},
		{"value": sum(d["man_days"] for d in data), "indicator": "Green", "label": _("Man-days"), "datatype": "Float"},
		{"value": sum(d["machine_hours"] for d in data), "indicator": "Orange", "label": _("Machine Hours"), "datatype": "Float"},
		{"value": sum(d["materials_cost"] for d in data), "indicator": "Red", "label": _("Materials Cost"), "datatype": "Currency"},
	]
