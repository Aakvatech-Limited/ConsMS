# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today

from consms.construction_management.progress import get_measured_qty


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{"label": _("Contract"), "fieldname": "contract", "fieldtype": "Link", "options": "BF Contract", "width": 150},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 110},
		{"label": _("Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
		{"label": _("Original Completion"), "fieldname": "original_completion_date", "fieldtype": "Date", "width": 130},
		{"label": _("Extension Days"), "fieldname": "extension_days", "fieldtype": "Int", "width": 110},
		{"label": _("Revised Completion"), "fieldname": "revised_completion_date", "fieldtype": "Date", "width": 130},
		{"label": _("Days Elapsed"), "fieldname": "days_elapsed", "fieldtype": "Int", "width": 100},
		{"label": _("Days Remaining"), "fieldname": "days_remaining", "fieldtype": "Int", "width": 110,
		 "description": "Negative = overdue."},
		{"label": _("% Time Used"), "fieldname": "percent_time", "fieldtype": "Percent", "width": 100},
		{"label": _("% Work Done"), "fieldname": "percent_work", "fieldtype": "Percent", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]


def get_data(filters):
	contract_filters = {"docstatus": 1, "start_date": ["is", "set"], "original_completion_date": ["is", "set"]}
	for field in ("project", "contract_type"):
		if filters.get(field):
			contract_filters[field] = filters.get(field)

	data = []
	for c in frappe.get_all(
		"BF Contract",
		filters=contract_filters,
		fields=["name", "project", "boq", "start_date", "original_completion_date", "approved_extension_days",
			"revised_completion_date", "actual_completion_date"],
		order_by="revised_completion_date",
	):
		end = c.revised_completion_date or c.original_completion_date
		as_of = c.actual_completion_date or today()
		total_days = max(date_diff(end, c.start_date), 1)
		elapsed = max(date_diff(as_of, c.start_date), 0)
		percent_time = min(elapsed / total_days * 100, 100) if getdate(as_of) <= getdate(end) else elapsed / total_days * 100
		percent_work = get_percent_work(c)

		if c.actual_completion_date:
			status = _("Completed")
		elif getdate(today()) > getdate(end):
			status = _("Overdue")
		elif percent_work + 10 < percent_time:
			status = _("Behind")
		else:
			status = _("On Track")

		data.append({
			"contract": c.name,
			"project": c.project,
			"start_date": c.start_date,
			"original_completion_date": c.original_completion_date,
			"extension_days": c.approved_extension_days,
			"revised_completion_date": end,
			"days_elapsed": elapsed,
			"days_remaining": date_diff(end, as_of),
			"percent_time": percent_time,
			"percent_work": percent_work,
			"status": status,
		})
	return data


def get_percent_work(contract):
	"""Value of measured work / BOQ value."""
	if not contract.boq:
		return 0
	done = get_measured_qty(contract.name)
	total = done_value = 0
	for line in frappe.get_all("BF BOQ Item", filters={"parent": contract.boq}, fields=["name", "quantity", "unit_rate"]):
		total += flt(line.quantity) * flt(line.unit_rate)
		done_value += min(done.get(line.name, 0), flt(line.quantity)) * flt(line.unit_rate)
	return done_value / total * 100 if total else 0


def get_summary(data):
	count = lambda s: sum(1 for d in data if d["status"] == s)
	return [
		{"value": len(data), "indicator": "Blue", "label": _("Contracts"), "datatype": "Int"},
		{"value": count(_("On Track")), "indicator": "Green", "label": _("On Track"), "datatype": "Int"},
		{"value": count(_("Behind")), "indicator": "Orange", "label": _("Behind"), "datatype": "Int"},
		{"value": count(_("Overdue")), "indicator": "Red", "label": _("Overdue"), "datatype": "Int"},
		{"value": count(_("Completed")), "indicator": "Blue", "label": _("Completed"), "datatype": "Int"},
	]
