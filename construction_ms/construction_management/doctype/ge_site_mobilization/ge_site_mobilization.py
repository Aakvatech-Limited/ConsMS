# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GESiteMobilization(Document):
	def validate(self):
		self.update_mobilization_status()

	def before_submit(self):
		if self.mobilization_status != "Completed":
			frappe.throw("Mobilization can only be submitted when all tasks are 'Completed'.")
		
	def update_mobilization_status(self):
		if not self.mobilization_checklist:
			self.mobilization_status = "Not Started"
			return
			
		all_completed = True
		any_started = False
		
		for item in self.mobilization_checklist:
			if item.status == "Completed":
				any_started = True
			elif item.status == "In Progress":
				any_started = True
				all_completed = False
			else: # Pending
				all_completed = False
				
		if all_completed:
			self.mobilization_status = "Completed"
		elif any_started:
			self.mobilization_status = "In Progress"
		else:
			self.mobilization_status = "Not Started"
