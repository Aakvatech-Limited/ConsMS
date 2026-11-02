"""Site measurement: Task progress from measured quantities."""

import frappe
from frappe.utils import flt


def get_certificates_paying(log):
	"""Submitted certificates of the log's contract whose period takes in the log's date and that pay its BOQ lines."""
	boq_items = [row.boq_item for row in log.measurements if row.boq_item]
	if not boq_items:
		return []
	return frappe.db.sql_list(
		"""select distinct claim.name from `tabBF Progress Claim` claim
		join `tabBF Progress Claim Item` item on item.parent = claim.name
		where claim.contract = %(contract)s and claim.docstatus = 1
			and (claim.period_from is null or claim.period_from <= %(date)s)
			and (claim.period_to is null or claim.period_to >= %(date)s)
			and item.boq_item in %(boq_items)s and item.this_period_qty != 0
		order by claim.name""",
		{"contract": log.contract, "date": log.date, "boq_items": boq_items},
	)


def update_task_progress(tasks):
	"""Task progress % = value measured so far / value of its BOQ lines (quantity x rate)."""
	for task in {t for t in tasks if t}:
		boq_value = flt(
			frappe.db.sql(
				"""
				select sum(item.quantity * item.unit_rate)
				from `tabBF BOQ Item` item
				join `tabBF Bill of Quantities` boq on boq.name = item.parent
				where item.task = %s and boq.docstatus = 1
				""",
				task,
			)[0][0]
		)
		if not boq_value:
			continue

		measured_value = flt(
			frappe.db.sql(
				"""
				select sum(mi.total_quantity * boq_item.unit_rate)
				from `tabBF Measurement Item` mi
				join `tabBF Site Measurement Log` log on log.name = mi.parent
				join `tabBF BOQ Item` boq_item on boq_item.name = mi.boq_item
				where mi.task = %s and log.docstatus = 1
				""",
				task,
			)[0][0]
		)
		progress = min(100.0, measured_value / boq_value * 100)
		frappe.db.set_value("Task", task, "progress", progress)
