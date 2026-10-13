# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class BFRateAnalysis(Document):
	def validate(self):
		self.cost_per_unit = 0
		for row in self.items:
			row.amount = flt(row.qty) * (1 + flt(row.wastage_percent) / 100) * flt(row.rate)
			self.cost_per_unit += row.amount
