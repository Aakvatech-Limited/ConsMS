"""Mobilization checklist rows are ERPNext Tasks; keep both statuses in step."""

import frappe
from frappe.utils import today

MOBILIZATION_TASK_TYPE = "Mobilization"

# checklist status -> Task status
TO_TASK_STATUS = {"Pending": "Open", "In Progress": "Working", "Completed": "Completed"}

# Task status -> checklist status
FROM_TASK_STATUS = {
	"Open": "Pending",
	"Overdue": "Pending",
	"Template": "Pending",
	"Working": "In Progress",
	"Pending Review": "In Progress",
	"Completed": "Completed",
	"Cancelled": "Completed",
}


def get_mobilization_status(row_statuses):
	if not row_statuses:
		return "Not Started"
	if all(status == "Completed" for status in row_statuses):
		return "Completed"
	if any(status in ("In Progress", "Completed") for status in row_statuses):
		return "In Progress"
	return "Not Started"


def ensure_mobilization_task_type():
	if not frappe.db.exists("Task Type", MOBILIZATION_TASK_TYPE):
		frappe.get_doc({"doctype": "Task Type", "name": MOBILIZATION_TASK_TYPE}).insert(ignore_permissions=True)


def create_task_from_template(template_task, project):
	"""Copy a template Task into the project, like ERPNext does for Project Templates."""
	ensure_mobilization_task_type()
	template = frappe.get_doc("Task", template_task)
	task = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": template.subject,
			"project": project,
			"status": "Open",
			"description": template.description,
			"type": template.type or MOBILIZATION_TASK_TYPE,
			"priority": template.priority,
			"task_weight": template.task_weight,
			"template_task": template.name,
		}
	)
	task.insert(ignore_permissions=True)
	return task.name


def set_task_status(task_name, checklist_status):
	task = frappe.get_doc("Task", task_name)
	task_status = TO_TASK_STATUS.get(checklist_status, "Open")
	if FROM_TASK_STATUS.get(task.status) == checklist_status:
		return

	task.status = task_status
	if task_status == "Completed" and not task.completed_on:
		task.completed_on = today()
	task.flags.from_mobilization = True
	task.save(ignore_permissions=True)


def update_mobilization_from_task(doc, method=None):
	"""Task on_update: mirror the Task status on the mobilization checklist."""
	if doc.flags.from_mobilization or doc.is_template:
		return

	checklist_status = FROM_TASK_STATUS.get(doc.status, "Pending")
	rows = frappe.get_all(
		"BF Site Mobilization Item",
		filters={"task": doc.name, "parenttype": "BF Site Mobilization"},
		fields=["name", "parent", "status"],
	)
	for row in rows:
		if row.status == checklist_status:
			continue

		frappe.db.set_value("BF Site Mobilization Item", row.name, "status", checklist_status)
		statuses = frappe.get_all(
			"BF Site Mobilization Item", filters={"parent": row.parent}, pluck="status", order_by="idx"
		)
		frappe.db.set_value(
			"BF Site Mobilization", row.parent, "mobilization_status", get_mobilization_status(statuses)
		)
