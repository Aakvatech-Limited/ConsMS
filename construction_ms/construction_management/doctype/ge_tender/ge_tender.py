# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class GETender(Document):
	pass

@frappe.whitelist()
def make_ge_contract(source_name, target_doc=None):
	doc = get_mapped_doc("GE Tender", source_name, {
		"GE Tender": {
			"doctype": "GE Contract",
			"field_map": {
				"project": "project",
				"name": "tender"
			}
		}
	}, target_doc)
	
	return doc
