# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GESiteMeasurementLog(Document):
	pass

@frappe.whitelist()
def fetch_boq_items(boq_name):
	# Using ignore_permissions=True to safely pull the items regardless of user role
	items = frappe.get_all(
		"GE BOQ Item",
		filters={"parent": boq_name},
		fields=["name", "description", "uom"],
		ignore_permissions=True
	)
	return items

@frappe.whitelist()
def get_boq_item_details(item_name):
	# Safely fetch details for a single item when manually selected
	return frappe.db.get_value(
		"GE BOQ Item", 
		item_name, 
		["description", "uom"], 
		as_dict=True,
		ignore=True
	)

