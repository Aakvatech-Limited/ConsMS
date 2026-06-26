# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class GEBillofQuantities(Document):
	pass

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.material_request_type = "Purchase"
		
	def update_item(source, target, source_parent):
		target.ge_boq_item = source.name
		# Only request the remaining amount
		rem_qty = float(source.quantity or 0) - float(source.requested_qty or 0)
		target.qty = rem_qty

	doc = get_mapped_doc("GE Bill of Quantities", source_name, {
		"GE Bill of Quantities": {
			"doctype": "Material Request",
			"field_map": {
				"project": "project"
			}
		},
		"GE BOQ Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"item_code": "item_code",
				"description": "description",
				"uom": "uom"
			},
			"condition": lambda doc: float(doc.quantity or 0) > float(doc.requested_qty or 0),
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)
	
	return doc
