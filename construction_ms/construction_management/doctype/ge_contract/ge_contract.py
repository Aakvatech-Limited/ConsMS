# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class GEContract(Document):
	def validate(self):
		if flt(self.contingency_percentage) > 15:
			frappe.msgprint("Warning: A contingency exceeding 15% is unusually high for standard construction contracts and may require special budget approval. Please verify.", title="High Contingency Threshold", indicator="orange")
		
		self.contingency_amount = flt(self.contract_amount) * (flt(self.contingency_percentage) / 100.0)
