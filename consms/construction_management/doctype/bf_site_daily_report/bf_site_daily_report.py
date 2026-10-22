# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""What happened on site in a day, task by task: who worked, which machines, what was used.

It holds no money. Materials leave the Site Store through a Stock Issue on submit, which puts
their cost in the books with the project, task and BOQ line; labour and machine hire are paid
through payroll and accounts.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

TABLES = ("labour", "plant", "materials")


class BFSiteDailyReport(Document):
	def validate(self):
		if self.materials and not self.source_warehouse:
			frappe.throw(_("Select the Site Store the materials are taken from."))
		self.validate_tasks()
		for row in self.labour:
			if row.employee:
				row.headcount = 1
		self.set_summary()

	def validate_tasks(self):
		"""Every row belongs to a task, once the project has tasks to choose from."""
		if not frappe.db.exists("Task", {"project": self.project, "is_template": 0}):
			return
		for table in TABLES:
			for row in self.get(table):
				if not row.task:
					frappe.throw(
						_("{0} row {1}: select the Task this belongs to.").format(_(self.meta.get_label(table)), row.idx),
						title=_("Task missing"),
					)

	def set_summary(self):
		self.total_headcount = sum(cint(row.headcount) for row in self.labour)
		self.man_days = sum(cint(row.headcount) * flt(row.days) for row in self.labour)
		self.machines_on_site = len(self.plant)

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
				"from_warehouse": self.source_warehouse,
				"remarks": _("Materials used on site - {0}").format(self.name),
				"items": [
					{
						"item_code": row.item_code,
						"qty": row.qty,
						"s_warehouse": self.source_warehouse,
						"project": self.project,
						"bf_task": row.task,
						"bf_boq_item": row.boq_item,
					}
					for row in self.materials
				],
			}
		)
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.db_set("stock_entry", entry.name)
