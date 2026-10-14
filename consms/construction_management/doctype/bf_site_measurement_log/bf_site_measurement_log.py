# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from consms.construction_management.measurement import update_task_progress


class BFSiteMeasurementLog(Document):
	def before_submit(self):
		if not self.measurements:
			frappe.throw(_("Add at least one measured BOQ item."))
		for row in self.measurements:
			item = self.get_item_label(row)
			if flt(row.total_quantity) <= 0:
				frappe.throw(_("Row {0}: enter the Quantity measured for {1}.").format(row.idx, item))
			if not row.drawing:
				frappe.throw(_("Row {0}: attach the drawing or measurement sheet as proof for {1}.").format(row.idx, item))

	def get_item_label(self, row):
		item_no = frappe.db.get_value("BF BOQ Item", row.boq_item, "item_no")
		description = (row.item_description or "")[:60]
		return frappe.bold(f"{item_no} {description}".strip() if item_no else description or row.boq_item)

	def on_submit(self):
		update_task_progress(row.task for row in self.measurements)

	def on_cancel(self):
		update_task_progress(row.task for row in self.measurements)

@frappe.whitelist()
def fetch_boq_items(boq_name):
	# Using ignore_permissions=True to safely pull the items regardless of user role
	items = frappe.get_all(
		"BF BOQ Item",
		filters={"parent": boq_name},
		fields=["name", "description", "uom", "task"],
		ignore_permissions=True
	)
	return items

@frappe.whitelist()
def get_boq_item_details(item_name):
	# Safely fetch details for a single item when manually selected
	return frappe.db.get_value(
		"BF BOQ Item", 
		item_name, 
		["description", "uom", "task"], 
		as_dict=True,
		ignore=True
	)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_items_query(doctype, txt, searchfield, start, page_len, filters):
	boq_name = filters.get("parent")
	if not boq_name:
		return []
		
	search_txt = f"%{txt}%"
	
	query = """
		SELECT 
			name, description, quantity, uom
		FROM `tabBF BOQ Item`
		WHERE parent = %s
		AND (name LIKE %s OR IFNULL(description, '') LIKE %s)
		ORDER BY idx
		LIMIT %s, %s
	"""

	return frappe.db.sql(query, (boq_name, search_txt, search_txt, start, page_len))

