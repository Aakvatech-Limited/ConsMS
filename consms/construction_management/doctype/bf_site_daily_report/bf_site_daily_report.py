# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""What happened on site in a day: the diary, and the materials used on each task.

It holds no money. Materials leave the Site Store through a Stock Issue on submit, which puts
their cost in the books with the project, task and BOQ line. Labour gangs and hired machines are
Suppliers paid by Purchase Invoice with the project and task (Task is an accounting dimension).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class BFSiteDailyReport(Document):
	def validate(self):
		if self.materials and not self.source_warehouse:
			frappe.throw(_("Select the Site Store the materials are taken from."))
		self.validate_tasks()

	def validate_tasks(self):
		"""Every material row belongs to a task, once the project has tasks to choose from."""
		if not frappe.db.exists("Task", {"project": self.project, "is_template": 0}):
			return
		for row in self.materials:
			if not row.task:
				frappe.throw(_("Materials Used row {0}: select the Task this belongs to.").format(row.idx), title=_("Task missing"))

	def on_submit(self):
		self.issue_materials()

	def on_cancel(self):
		if self.stock_entry and frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") == 1:
			frappe.get_doc("Stock Entry", self.stock_entry).cancel()

	def issue_materials(self):
		"""Materials used today leave the site store, charged to the project, task and BOQ line."""
		if not self.materials:
			return
		company = frappe.db.get_value("Project", self.project, "company")
		entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"company": company,
				"posting_date": self.date,
				"set_posting_time": 1,
				"project": self.project,
				# the header Task (shown under Connections on the Task) when all materials are for one task
				"task": tasks.pop() if len(tasks := {row.task for row in self.materials}) == 1 else None,
				"from_warehouse": self.source_warehouse,
				"remarks": _("Materials used on site - {0}").format(self.name),
				"items": [
					{
						"item_code": row.item_code,
						"qty": row.qty,
						"s_warehouse": self.source_warehouse,
						"project": self.project,
						"task": row.task,
						"bf_boq_item": row.boq_item,
					}
					for row in self.materials
				],
			}
		)
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.db_set("stock_entry", entry.name)
