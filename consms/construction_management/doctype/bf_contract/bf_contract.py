# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc

class BFContract(Document):
	def validate(self):
		if flt(self.contingency_percentage) > 15:
			frappe.msgprint("Warning: A contingency exceeding 15% is unusually high for standard construction contracts and may require special budget approval. Please verify.", title="High Contingency Threshold", indicator="orange")
		
		self.contingency_amount = flt(self.contract_amount) * (flt(self.contingency_percentage) / 100.0)
		self.total_contract_amount = flt(self.contract_amount) + flt(self.contingency_amount)
		self.validate_submittals()

	def before_update_after_submit(self):
		self.validate_submittals()

	def validate_submittals(self):
		for row in self.get("submittals"):
			if row.status in ("Approved", "Rejected") and not row.attachment:
				frappe.throw(
					_("Row {0}: attach the {1} document before marking it {2}.").format(
						row.idx, row.submittal_type, row.status
					)
				)

@frappe.whitelist()
def make_site_mobilization(source_name, target_doc=None):
	doc = get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Site Mobilization",
			"field_map": {
				"project": "project",
				"name": "contract"
			}
		}
	}, target_doc)

	return doc

@frappe.whitelist()
def make_variation_order(source_name, target_doc=None):
	doc = get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Variation Order",
			"field_map": {
				"project": "project",
				"name": "contract"
			}
		}
	}, target_doc)
	return doc

@frappe.whitelist()
def make_progress_claim(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.claim_title = f"IPC for Contract {source.name}"

	doc = get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Progress Claim",
			"field_map": {
				"name": "contract"
			}
		}
	}, target_doc, set_missing_values)
	return doc
