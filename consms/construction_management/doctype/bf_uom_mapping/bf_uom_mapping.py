# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BFUOMMapping(Document):
	def validate(self):
		self.boq_unit = self.boq_unit.strip()
