# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from consms.construction_management.tasks import (
	create_task_from_template,
	get_execution_status,
	set_task_status,
	validate_task_projects,
)


class BFWorksExecution(Document):
	def validate(self):
		if self.planned_start_date and self.planned_end_date and self.planned_end_date < self.planned_start_date:
			frappe.throw(_("Planned Finish cannot be before Planned Start."))
		self.create_tasks_from_template()
		validate_task_projects(self, "tasks")
		self.sync_task_statuses()
		self.status = get_execution_status([row.status for row in self.tasks])

	def before_submit(self):
		if self.status != "Completed":
			frappe.throw(_("{0} can only be submitted when all tasks are 'Completed'.").format(self.activity_type))

	def before_cancel(self):
		"""Measurements need the contract to be mobilized: keep the last Mobilization while any are submitted."""
		if not frappe.db.get_value("BF Activity Type", self.activity_type, "is_mobilization"):
			return
		other = frappe.db.exists("BF Works Execution", {
			"contract": self.contract, "docstatus": 1, "name": ["!=", self.name],
			"activity_type": ["in", frappe.get_all("BF Activity Type", {"is_mobilization": 1}, pluck="name")],
		})
		measured = frappe.db.exists("BF Site Measurement Log", {"contract": self.contract, "docstatus": 1})
		if measured and not other:
			frappe.throw(
				_("Contract {0} has submitted measurements (for example {1}), which need it to be mobilized. Cancel the measurements first.").format(
					self.contract, frappe.bold(measured)),
				title=_("Contract has measurements"),
			)

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
