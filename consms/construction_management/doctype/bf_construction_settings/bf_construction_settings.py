# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BFConstructionSettings(Document):
	def on_update(self):
		if self.track_costs_per_task:
			ensure_task_accounting_dimension()


def ensure_task_accounting_dimension():
	"""Task as an accounting dimension: costs can be booked per project task."""
	if frappe.db.exists("Accounting Dimension", {"document_type": "Task"}):
		return

	frappe.get_doc({"doctype": "Accounting Dimension", "document_type": "Task", "label": "Task"}).insert(
		ignore_permissions=True
	)
