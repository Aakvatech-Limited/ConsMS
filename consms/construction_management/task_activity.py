"""The cost of each task, from the books.

Materials are the Stock Issues that carry the task, at the
value the books hold. Other costs are everything else booked to the task (Task is an accounting
dimension): labour gangs and hired machines on supplier invoices, journals, services.
Progress is the task's % done from measurements.
"""

import frappe
from frappe import _
from frappe.utils import flt


def get_activity(tasks, from_date=None, to_date=None):
	"""{task: activity} for the given tasks, optionally between two dates."""
	tasks = list(tasks)
	activity = {t: frappe._dict(materials={}, materials_cost=0.0, other_costs={}, other_cost=0.0)
		for t in tasks}
	if not tasks:
		return activity

	period = {"tasks": tasks, "from_date": from_date or "1900-01-01", "to_date": to_date or "2999-12-31"}

	for r in frappe.db.sql("""
			select sed.task, sed.item_code, sed.uom, sum(sed.qty) as qty, sum(sed.amount) as amount
			from `tabStock Entry Detail` sed
			join `tabStock Entry` se on se.name = sed.parent
			where sed.task in %(tasks)s and se.docstatus = 1 and se.purpose = 'Material Issue'
				and se.posting_date between %(from_date)s and %(to_date)s
			group by sed.task, sed.item_code, sed.uom""", period, as_dict=True):
		activity[r.task].materials[r.item_code] = frappe._dict(qty=flt(r.qty), uom=r.uom, amount=flt(r.amount))
		activity[r.task].materials_cost += flt(r.amount)

	for r in frappe.db.sql("""
			select gle.task, gle.account, sum(gle.debit - gle.credit) as amount
			from `tabGL Entry` gle
			join `tabAccount` account on account.name = gle.account
			where gle.task in %(tasks)s and gle.is_cancelled = 0 and account.root_type = 'Expense'
				and gle.voucher_type != 'Stock Entry' and gle.posting_date between %(from_date)s and %(to_date)s
			group by gle.task, gle.account""", period, as_dict=True):
		activity[r.task].other_costs[r.account] = flt(r.amount)
		activity[r.task].other_cost += flt(r.amount)

	for a in activity.values():
		a.total_cost = a.materials_cost + a.other_cost
	return activity


@frappe.whitelist()
def get_task_site_activity(task):
	"""The Costs section on a Task."""
	frappe.get_doc("Task", task).check_permission("read")
	a = get_activity([task])[task]
	return {
		"progress": flt(frappe.db.get_value("Task", task, "progress")),
		"materials_cost": a.materials_cost,
		"other_cost": a.other_cost,
		"total_cost": a.total_cost,
		"materials": [dict(item_code=k, **v) for k, v in sorted(a.materials.items())],
		"other_costs": [{"account": k, "amount": v} for k, v in sorted(a.other_costs.items())],
	}
