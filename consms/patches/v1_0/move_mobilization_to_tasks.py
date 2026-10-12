"""Move mobilization checklists from BF Mobilization Task/Template to ERPNext Task/Project Template.

- each BF Mobilization Task      -> template Task (is_template, type Mobilization)
- each BF Mobilization Template  -> Project Template with the same name
- each checklist row             -> a Task in the mobilization's project, with the row's status
"""

import frappe
from frappe.utils import today

from consms.construction_management.tasks import (
	MOBILIZATION_TASK_TYPE,
	TO_TASK_STATUS,
	ensure_mobilization_task_type,
)


def execute():
	if not frappe.db.table_exists("BF Mobilization Task"):
		return

	ensure_mobilization_task_type()
	template_tasks = create_template_tasks()
	create_project_templates(template_tasks)
	convert_checklist_rows(template_tasks)


def create_template_tasks():
	"""Return {old BF Mobilization Task name: template Task name}."""
	template_tasks = {}
	for old in frappe.db.sql("select name, task_name, description from `tabBF Mobilization Task`", as_dict=True):
		subject = old.task_name or old.name
		task = frappe.db.get_value(
			"Task", {"is_template": 1, "subject": subject, "type": MOBILIZATION_TASK_TYPE}
		)
		if not task:
			task = (
				frappe.get_doc(
					{
						"doctype": "Task",
						"subject": subject,
						"description": old.description,
						"type": MOBILIZATION_TASK_TYPE,
						"is_template": 1,
						"status": "Template",
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		template_tasks[old.name] = task
	return template_tasks


def create_project_templates(template_tasks):
	if not frappe.db.table_exists("BF Mobilization Template Task"):
		return

	rows = frappe.db.sql(
		"select parent, task from `tabBF Mobilization Template Task` order by parent, idx", as_dict=True
	)
	templates = {}
	for row in rows:
		templates.setdefault(row.parent, []).append(row.task)

	for name, tasks in templates.items():
		if frappe.db.exists("Project Template", name):
			continue

		template = frappe.get_doc({"doctype": "Project Template", "__newname": name})
		for old_task in tasks:
			if template_tasks.get(old_task):
				template.append("tasks", {"task": template_tasks[old_task]})
		template.insert(ignore_permissions=True)


def convert_checklist_rows(template_tasks):
	"""Rows still pointing at a BF Mobilization Task get a real Task in their project."""
	rows = frappe.db.sql(
		"""
		select item.name, item.task, item.status, mob.project
		from `tabBF Site Mobilization Item` item
		join `tabBF Site Mobilization` mob on mob.name = item.parent
		where item.parenttype = 'BF Site Mobilization'
		""",
		as_dict=True,
	)
	for row in rows:
		if row.task not in template_tasks:
			continue

		template = frappe.get_doc("Task", template_tasks[row.task])
		task = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": template.subject,
				"description": template.description,
				"project": row.project,
				"type": MOBILIZATION_TASK_TYPE,
				"status": TO_TASK_STATUS.get(row.status, "Open"),
				"completed_on": today() if row.status == "Completed" else None,
				"template_task": template.name,
			}
		)
		task.flags.from_mobilization = True
		task.insert(ignore_permissions=True)
		frappe.db.set_value("BF Site Mobilization Item", row.name, "task", task.name, update_modified=False)
