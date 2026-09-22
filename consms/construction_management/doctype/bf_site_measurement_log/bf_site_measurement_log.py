# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BFSiteMeasurementLog(Document):
	pass

@frappe.whitelist()
def fetch_boq_items(boq_name):
	# Using ignore_permissions=True to safely pull the items regardless of user role
	items = frappe.get_all(
		"BF BOQ Item",
		filters={"parent": boq_name},
		fields=["name", "description", "uom"],
		ignore_permissions=True
	)
	return items

@frappe.whitelist()
def get_boq_item_details(item_name):
	# Safely fetch details for a single item when manually selected
	return frappe.db.get_value(
		"BF BOQ Item", 
		item_name, 
		["description", "uom"], 
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
			name, item_code, description, quantity, uom
		FROM `tabBF BOQ Item`
		WHERE parent = %s
		AND (name LIKE %s OR IFNULL(item_code, '') LIKE %s OR IFNULL(description, '') LIKE %s)
		LIMIT %s, %s
	"""
	
	return frappe.db.sql(query, (boq_name, search_txt, search_txt, search_txt, start, page_len))

