# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BFSiteDailyReport(Document):
	def validate(self):
		if self.materials and not self.source_warehouse:
			frappe.throw(_("Select the Site Store the materials are taken from."))
		self.calculate_totals()

	def calculate_totals(self):
		for row in self.labour:
			row.amount = flt(row.headcount) * flt(row.days) * flt(row.rate)
		for row in self.plant:
			row.amount = flt(row.hours) * flt(row.rate)
		for row in self.materials:
			row.amount = flt(row.qty) * flt(row.rate)
		self.labour_cost = sum(flt(r.amount) for r in self.labour)
		self.total_headcount = sum(int(r.headcount or 0) for r in self.labour)
		self.plant_cost = sum(flt(r.amount) for r in self.plant)
		self.total_fuel = sum(flt(r.fuel_litres) for r in self.plant)
		self.material_cost = sum(flt(r.amount) for r in self.materials)
		self.total_cost = self.labour_cost + self.plant_cost + self.material_cost

	def on_submit(self):
		self.issue_materials()

	def on_cancel(self):
		if self.stock_entry and frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") == 1:
			frappe.get_doc("Stock Entry", self.stock_entry).cancel()

	def issue_materials(self):
		"""Materials used today leave the site store and are charged to the project."""
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
					{"item_code": row.item_code, "qty": row.qty, "s_warehouse": self.source_warehouse, "project": self.project}
					for row in self.materials
				],
			}
		)
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.db_set("stock_entry", entry.name)

		# record the actual stock value used
		rates = {row.item_code: flt(row.valuation_rate) for row in entry.items}
		for row in self.materials:
			row.db_set("rate", rates.get(row.item_code, 0))
			row.db_set("amount", flt(row.qty) * rates.get(row.item_code, 0))
		self.db_set("material_cost", sum(flt(r.qty) * rates.get(r.item_code, 0) for r in self.materials))
		self.db_set("total_cost", flt(self.labour_cost) + flt(self.plant_cost) + flt(self.material_cost))
