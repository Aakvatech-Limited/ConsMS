"""What happened on each task across days: from submitted Site Daily Reports, and for materials from the books.

Labour and machines are facts (man-days, hours) from the daily reports; materials are the Stock Issues
that carry the task, at the value the books hold. Progress is the task's % done from measurements.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

HOUR_UNITS = {"hour", "hours", "hr", "hrs"}
DAY_UNITS = {"day", "days"}


def get_activity(tasks, from_date=None, to_date=None):
	"""{task: activity} for the given tasks, optionally between two dates."""
	tasks = list(tasks)
	activity = {t: frappe._dict(dates=set(), reports={}, man_days=0.0, trades=defaultdict(float),
		machine_hours=0.0, machine_days=0.0, machines=defaultdict(float), materials={}, materials_cost=0.0) for t in tasks}
	if not tasks:
		return activity

	period = {"tasks": tasks, "from_date": from_date or "1900-01-01", "to_date": to_date or "2999-12-31"}
	report_rows = """
		join `tabBF Site Daily Report` report on report.name = row.parent
		where row.task in %(tasks)s and report.docstatus = 1 and report.date between %(from_date)s and %(to_date)s
	"""

	for table in ("BF Daily Labour", "BF Daily Plant", "BF Daily Material"):
		for r in frappe.db.sql(f"select distinct row.task, report.name, report.date from `tab{table}` row {report_rows}", period, as_dict=True):
			activity[r.task].dates.add(r.date)
			activity[r.task].reports[r.name] = r.date

	for r in frappe.db.sql(f"""
			select row.task, row.item_code, sum(row.headcount * row.days) as man_days
			from `tabBF Daily Labour` row {report_rows} group by row.task, row.item_code""", period, as_dict=True):
		activity[r.task].trades[r.item_code] += flt(r.man_days)
		activity[r.task].man_days += flt(r.man_days)

	for r in frappe.db.sql(f"""
			select row.task, row.item_code, row.uom, sum(row.hours) as used
			from `tabBF Daily Plant` row {report_rows} group by row.task, row.item_code, row.uom""", period, as_dict=True):
		unit = (r.uom or "").lower()
		activity[r.task].machines[f"{r.item_code} ({r.uom or _('units')})"] += flt(r.used)
		if unit in HOUR_UNITS:
			activity[r.task].machine_hours += flt(r.used)
		elif unit in DAY_UNITS:
			activity[r.task].machine_days += flt(r.used)

	for r in frappe.db.sql("""
			select sed.bf_task as task, sed.item_code, sed.uom, sum(sed.qty) as qty, sum(sed.amount) as amount
			from `tabStock Entry Detail` sed
			join `tabStock Entry` se on se.name = sed.parent
			where sed.bf_task in %(tasks)s and se.docstatus = 1 and se.purpose = 'Material Issue'
				and se.posting_date between %(from_date)s and %(to_date)s
			group by sed.bf_task, sed.item_code, sed.uom""", period, as_dict=True):
		activity[r.task].materials[r.item_code] = frappe._dict(qty=flt(r.qty), uom=r.uom, amount=flt(r.amount))
		activity[r.task].materials_cost += flt(r.amount)

	for a in activity.values():
		a.days_worked = len(a.dates)
		a.first_day = min(a.dates) if a.dates else None
		a.last_day = max(a.dates) if a.dates else None
	return activity


@frappe.whitelist()
def get_task_site_activity(task):
	"""The Site Activity section on a Task."""
	frappe.get_doc("Task", task).check_permission("read")
	a = get_activity([task])[task]
	return {
		"progress": flt(frappe.db.get_value("Task", task, "progress")),
		"days_worked": a.days_worked,
		"first_day": a.first_day,
		"last_day": a.last_day,
		"man_days": a.man_days,
		"machine_hours": a.machine_hours,
		"machine_days": a.machine_days,
		"materials_cost": a.materials_cost,
		"trades": [{"trade": k, "man_days": v} for k, v in sorted(a.trades.items())],
		"machines": [{"machine": k, "used": v} for k, v in sorted(a.machines.items())],
		"materials": [dict(item_code=k, **v) for k, v in sorted(a.materials.items())],
		"reports": [{"name": k, "date": v} for k, v in sorted(a.reports.items(), key=lambda x: x[1], reverse=True)],
	}
