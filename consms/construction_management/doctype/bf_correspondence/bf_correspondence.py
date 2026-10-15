# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BFCorrespondence(Document):
	def validate(self):
		if self.contract and not self.project:
			self.project = frappe.db.get_value("BF Contract", self.contract, "project")
		if self.response_required and self.status == "Open":
			self.status = "Awaiting Response"
		if self.reply_to == self.name:
			frappe.throw(_("A letter cannot reply to itself."))

	def on_update(self):
		# answering an earlier letter closes its loop
		if self.reply_to:
			frappe.db.set_value("BF Correspondence", self.reply_to, {"status": "Responded", "responded_with": self.name})
