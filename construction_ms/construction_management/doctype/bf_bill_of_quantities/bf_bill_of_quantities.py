# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from frappe.utils import flt

class BFBillofQuantities(Document):
	def validate(self):
		total = 0
		for item in self.get("items"):
			item.amount = flt(item.quantity) * flt(item.unit_rate)
			total += item.amount
		self.total_amount = total

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.material_request_type = "Purchase"
		
	def update_item(source, target, source_parent):
		target.bf_boq = source_parent.name
		target.bf_boq_item = source.name
		# Only request the remaining amount
		rem_qty = float(source.quantity or 0) - float(source.requested_qty or 0)
		target.qty = rem_qty

	doc = get_mapped_doc("BF Bill of Quantities", source_name, {
		"BF Bill of Quantities": {
			"doctype": "Material Request",
			"field_map": {
				"project": "project"
			}
		},
		"BF BOQ Item": {
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

@frappe.whitelist()
def make_bf_tender(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.tender_name = f"Tender for {source.project}"

	doc = get_mapped_doc("BF Bill of Quantities", source_name, {
		"BF Bill of Quantities": {
			"doctype": "BF Tender",
			"field_map": {
				"project": "project",
				"name": "boq"
			}
		}
	}, target_doc, set_missing_values)
	
	return doc

@frappe.whitelist()
def check_existing_tender(boq_name):
	existing_tender = frappe.db.get_value("BF Tender", {"boq": boq_name}, "name")
	if existing_tender:
		return existing_tender
	return None
