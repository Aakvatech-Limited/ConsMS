"""Works Execution task rows are ERPNext Tasks; keep both statuses in step."""

import frappe
from frappe.utils import today

MOBILIZATION_TASK_TYPE = "Mobilization"

# task row status -> Task status
TO_TASK_STATUS = {"Pending": "Open", "In Progress": "Working", "Completed": "Completed"}

# Task status -> task row status
FROM_TASK_STATUS = {
	"Open": "Pending",
	"Overdue": "Pending",
	"Template": "Pending",
	"Working": "In Progress",
	"Pending Review": "In Progress",
	"Completed": "Completed",
	"Cancelled": "Completed",
}


def get_execution_status(row_statuses):
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


def ensure_task_type(task_type):
	if task_type and not frappe.db.exists("Task Type", task_type):
		frappe.get_doc({"doctype": "Task Type", "name": task_type}).insert(ignore_permissions=True)


def create_task_from_template(template_task, project, activity_type=None):
	"""Copy a template Task into the project, like ERPNext does for Project Templates.

	Tasks take the activity type (Mobilization, Construction...), so they can be filtered per stage.
	"""
	template = frappe.get_doc("Task", template_task)
	task_type = activity_type or template.type or MOBILIZATION_TASK_TYPE
	ensure_task_type(task_type)
	task = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": template.subject,
			"project": project,
			"status": "Open",
			"description": template.description,
			"type": task_type,
			"priority": template.priority,
			"task_weight": template.task_weight,
			"template_task": template.name,
		}
	)
	task.insert(ignore_permissions=True)
	return task.name


def set_task_status(task_name, row_status):
	task = frappe.get_doc("Task", task_name)
	task_status = TO_TASK_STATUS.get(row_status, "Open")
	if FROM_TASK_STATUS.get(task.status) == row_status:
		return

	task.status = task_status
	if task_status == "Completed" and not task.completed_on:
		task.completed_on = today()
	task.flags.from_works_execution = True
	task.save(ignore_permissions=True)


def update_works_execution_from_task(doc, method=None):
	"""Task on_update: mirror the Task status on the Works Execution task rows."""
	if doc.flags.from_works_execution or doc.flags.from_mobilization or doc.is_template:
		return

	row_status = FROM_TASK_STATUS.get(doc.status, "Pending")
	rows = frappe.get_all(
		"BF Works Execution Task",
		filters={"task": doc.name, "parenttype": "BF Works Execution"},
		fields=["name", "parent", "status"],
	)
	for row in rows:
		if row.status == row_status:
			continue

		frappe.db.set_value("BF Works Execution Task", row.name, "status", row_status)
		statuses = frappe.get_all(
			"BF Works Execution Task", filters={"parent": row.parent}, pluck="status", order_by="idx"
		)
		frappe.db.set_value("BF Works Execution", row.parent, "status", get_execution_status(statuses))
