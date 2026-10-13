# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BFRateAnalysis(Document):
	def validate(self):
		if self.amended_from and not (self.revision_reason or "").strip():
			frappe.throw(_("Enter the Revision Reason: why this new version of the recipe is needed."))
		self.validate_one_active_version()
		self.cost_per_unit = 0
		for row in self.items:
			row.amount = flt(row.qty) * (1 + flt(row.wastage_percent) / 100) * flt(row.rate)
			self.cost_per_unit += row.amount

	def before_cancel(self):
		# Budgets keep their own copy of the quantities and rates, so an old version can be retired
		self.ignore_linked_doctypes = ("BF Budget",)

	def validate_one_active_version(self):
		other = frappe.db.get_value(
			"BF Rate Analysis",
			{
				"rate_analysis_name": self.rate_analysis_name,
				"docstatus": ["!=", 2],
				"name": ["not in", [self.name or "", self.amended_from or ""]],
			},
		)
		if other:
			frappe.throw(
				_("Rate Analysis {0} already exists ({1}). Cancel and Amend it to make a new version.").format(
					frappe.bold(self.rate_analysis_name), other
				)
			)
