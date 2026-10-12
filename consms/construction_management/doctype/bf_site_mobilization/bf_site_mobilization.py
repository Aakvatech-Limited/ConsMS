# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from consms.construction_management.tasks import (
	create_task_from_template,
	get_mobilization_status,
	set_task_status,
)


class BFSiteMobilization(Document):
	def validate(self):
		self.create_tasks_from_template()
		self.validate_task_projects()
		self.sync_task_statuses()
		self.mobilization_status = get_mobilization_status([row.status for row in self.mobilization_checklist])

	def before_submit(self):
		if self.mobilization_status != "Completed":
			frappe.throw(_("Mobilization can only be submitted when all tasks are 'Completed'."))

	def create_tasks_from_template(self):
		"""First save with a template and an empty checklist: create the project's Tasks."""
		if not self.mobilization_template or self.mobilization_checklist:
			return

		template = frappe.get_doc("Project Template", self.mobilization_template)
		for row in template.tasks:
			task = create_task_from_template(row.task, self.project)
			self.append("mobilization_checklist", {
				"task": task,
				"subject": frappe.db.get_value("Task", task, "subject"),
				"status": "Pending",
			})

	def validate_task_projects(self):
		for row in self.mobilization_checklist:
			task_project = frappe.db.get_value("Task", row.task, "project")
			if task_project != self.project:
				frappe.throw(
					_("Row {0}: Task {1} belongs to project {2}, not {3}.").format(
						row.idx, row.task, task_project or _("(none)"), self.project
					)
				)

	def sync_task_statuses(self):
		for row in self.mobilization_checklist:
			if row.task:
				set_task_status(row.task, row.status)
