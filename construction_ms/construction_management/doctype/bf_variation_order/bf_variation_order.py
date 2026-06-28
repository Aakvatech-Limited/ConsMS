# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class BFVariationOrder(Document):
	def validate(self):
		total = 0.0
		for item in self.get("items"):
			item.amount = flt(item.quantity) * flt(item.unit_rate)
			total += item.amount
			
		self.requested_amount = total
