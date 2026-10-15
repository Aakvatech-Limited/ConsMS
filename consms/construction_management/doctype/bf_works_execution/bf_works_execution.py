# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from consms.construction_management.tasks import (
	create_task_from_template,
	get_execution_status,
	set_task_status,
)


class BFWorksExecution(Document):
	def validate(self):
		if self.planned_start_date and self.planned_end_date and self.planned_end_date < self.planned_start_date:
			frappe.throw(_("Planned Finish cannot be before Planned Start."))
		self.create_tasks_from_template()
		self.validate_task_projects()
		self.sync_task_statuses()
		self.validate_resources()
		self.status = get_execution_status([row.status for row in self.tasks])

	def validate_resources(self):
		for row in self.resources:
			if row.resource_type != "Labour":
				row.employee = None
			if row.resource_type != "Plant":
				row.asset = None
			if row.employee:
				row.quantity = 1

	def before_submit(self):
		if self.status != "Completed":
			frappe.throw(_("{0} can only be submitted when all tasks are 'Completed'.").format(self.activity_type))

	def create_tasks_from_template(self):
		"""First save with a template and no tasks: create the project's Tasks."""
		if not self.project_template or self.tasks:
			return

		template = frappe.get_doc("Project Template", self.project_template)
		for row in template.tasks:
			task = create_task_from_template(row.task, self.project, self.activity_type)
			self.append("tasks", {
				"task": task,
				"subject": frappe.db.get_value("Task", task, "subject"),
				"status": "Pending",
			})

	def validate_task_projects(self):
		for row in self.tasks:
			task_project = frappe.db.get_value("Task", row.task, "project")
			if task_project != self.project:
				frappe.throw(
					_("Row {0}: Task {1} belongs to project {2}, not {3}.").format(
						row.idx, row.task, task_project or _("(none)"), self.project
					)
				)

	def sync_task_statuses(self):
		for row in self.tasks:
			if row.task:
				set_task_status(row.task, row.status)


@frappe.whitelist()
def is_mobilized(contract):
	"""True once a Mobilization-type Works Execution is submitted for the contract."""
	return bool(
		frappe.db.sql(
			"""
			select 1 from `tabBF Works Execution` wx
			join `tabBF Activity Type` act on act.name = wx.activity_type
			where wx.contract = %s and wx.docstatus = 1 and act.is_mobilization = 1
			limit 1
			""",
			contract,
		)
	)
