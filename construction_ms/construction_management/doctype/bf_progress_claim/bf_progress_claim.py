# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class BFProgressClaim(Document):
	def validate(self):
		for var in self.get("variations", []):
			var.cumulative_amount = flt(var.previously_certified) + flt(var.this_period_amount)
			if flt(var.cumulative_amount) > flt(var.approved_amount):
				frappe.throw(f"Row {var.idx}: Cumulative Claimed Amount ({var.cumulative_amount}) cannot exceed the Approved Amount ({var.approved_amount}) for Variation {var.variation_order}.")
		
		self.calculate_totals()

	def calculate_totals(self):
		total_work_executed = 0.0
		for item in self.claim_items:
			item.this_period_value = flt(item.this_period_qty) * flt(item.unit_rate)
			item.cumulative_qty = flt(item.previous_qty) + flt(item.this_period_qty)
			item.cumulative_value = flt(item.cumulative_qty) * flt(item.unit_rate)
			
			total_work_executed += item.cumulative_value

		total_variations = 0.0
		for var in self.get("variations", []):
			var.cumulative_amount = flt(var.previously_certified) + flt(var.this_period_amount)
			total_variations += flt(var.cumulative_amount)

		self.approved_variations = total_variations
		self.total_work_executed = total_work_executed
		self.gross_valuation = flt(self.total_work_executed) + flt(self.approved_variations) + flt(self.materials_on_site)
		
		self.retention_deduction = (flt(self.retention_percentage) / 100.0) * self.gross_valuation
		
		# Deductions
		total_deductions = flt(self.retention_deduction) + flt(self.advance_payment_recovery) + flt(self.previous_certified_amount)
		self.net_amount_due = self.gross_valuation - total_deductions
		
		self.vat_amount = (flt(self.vat_percentage) / 100.0) * self.net_amount_due
		self.total_amount_certified = self.net_amount_due + self.vat_amount


@frappe.whitelist()
def fetch_measurements(claim_name, contract, period_from=None, period_to=None):
	doc = frappe.get_doc("BF Progress Claim", claim_name)
	contract_doc = frappe.get_doc("BF Contract", contract)
	boq_name = contract_doc.boq

	if not boq_name:
		frappe.throw("The selected Contract does not have an attached BOQ.")

	# 1. Fetch BOQ Items
	boq_items = frappe.get_all("BF BOQ Item", filters={"parent": boq_name}, fields=["name", "description", "uom", "unit_rate"])

	# 2. Fetch Measurements for this period
	filters = {"contract": contract, "docstatus": 1}
	if period_from: filters["date"] = [">=", period_from]
	if period_to: 
		if "date" in filters:
			filters["date"] = ["between", [period_from, period_to]]
		else:
			filters["date"] = ["<=", period_to]

	logs = frappe.get_all("BF Site Measurement Log", filters=filters, pluck="name")
	
	period_qtys = {}
	if logs:
		measurement_items = frappe.get_all("BF Measurement Item", 
			filters={"parent": ["in", logs]}, 
			fields=["boq_item", "total_quantity"]
		)
		for mi in measurement_items:
			period_qtys[mi.boq_item] = period_qtys.get(mi.boq_item, 0.0) + flt(mi.total_quantity)

	# 3. Fetch Previous IPCs for cumulative qtys
	past_claims = frappe.get_all("BF Progress Claim", 
		filters={"contract": contract, "docstatus": 1, "name": ["!=", claim_name]}, 
		pluck="name"
	)
	
	prev_qtys = {}
	prev_certified = 0.0
	if past_claims:
		past_items = frappe.get_all("BF Progress Claim Item", 
			filters={"parent": ["in", past_claims]}, 
			fields=["boq_item", "this_period_qty"]
		)
		for pi in past_items:
			prev_qtys[pi.boq_item] = prev_qtys.get(pi.boq_item, 0.0) + flt(pi.this_period_qty)
			
		# Get the total Gross Valuation of all past claims to subtract as Previous Certified Amount
		past_claim_docs = frappe.get_all("BF Progress Claim", filters={"name": ["in", past_claims]}, fields=["gross_valuation"])
		# Note: Standard practice is to subtract the Gross Valuation of previous IPCs from current Gross Valuation.
		# Wait, actually usually the most recent IPC's Gross Valuation is subtracted. But summing them is wrong if Gross is cumulative.
		# Since Gross Valuation is cumulative (based on cumulative_qty), we only need the MAX(Gross Valuation) of previous IPCs.
		if past_claim_docs:
			prev_certified = max([flt(p.gross_valuation) for p in past_claim_docs])

	# Fetch Past Variation Claims
	prev_var_claims = {}
	if past_claims:
		past_var_items = frappe.get_all("BF Progress Claim Variation", 
			filters={"parent": ["in", past_claims]}, 
			fields=["variation_order", "this_period_amount"]
		)
		for pvi in past_var_items:
			prev_var_claims[pvi.variation_order] = prev_var_claims.get(pvi.variation_order, 0.0) + flt(pvi.this_period_amount)

	# Fetch Approved Variations
	variations = frappe.get_all("BF Variation Order", 
		filters={"contract": contract, "docstatus": 1}, 
		fields=["name", "reason", "requested_amount"]
	)
	
	doc.set("variations", [])
	total_variations = 0.0
	for v in variations:
		prev_claimed = prev_var_claims.get(v.name, 0.0)
		remaining = flt(v.requested_amount) - prev_claimed
		if remaining < 0: remaining = 0.0
		
		doc.append("variations", {
			"variation_order": v.name,
			"variation_reason": v.reason,
			"approved_amount": flt(v.requested_amount),
			"previously_certified": prev_claimed,
			"this_period_amount": remaining,
			"cumulative_amount": prev_claimed + remaining
		})
		total_variations += prev_claimed + remaining
		
	doc.approved_variations = total_variations

	# Clear existing items
	doc.set("claim_items", [])
	
	for item in boq_items:
		prev_qty = prev_qtys.get(item.name, 0.0)
		this_qty = period_qtys.get(item.name, 0.0)
		
		# If there is no quantity measured in this period AND no previous quantity, we can skip it to keep IPC clean,
		# or add it with 0. Let's add it only if there is some quantity involved.
		if prev_qty > 0 or this_qty > 0:
			doc.append("claim_items", {
				"boq_item": item.name,
				"item_description": item.description,
				"uom": item.uom,
				"unit_rate": item.unit_rate,
				"previous_qty": prev_qty,
				"this_period_qty": this_qty
			})

	doc.previous_certified_amount = prev_certified
	doc.calculate_totals()
	doc.save()
	
	return {"status": "success", "count": len(doc.claim_items)}

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	
	def set_missing_values(source, target):
		target.project = source.project
		target.bf_contract = source.contract
		target.bf_progress_claim = source.name
		target.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
			
		default_item = frappe.db.get_single_value("BF Construction Settings", "default_progress_claim_item")
			
		target.append("items", {
			"item_code": default_item,
			"item_name": source.claim_title,
			"description": f"Progress Claim for Contract {source.contract}: {source.claim_title}",
			"qty": 1,
			"rate": source.net_amount_due,
			"amount": source.net_amount_due
		})

	doclist = get_mapped_doc(
		"BF Progress Claim", source_name,
		{"BF Progress Claim": {"doctype": "Sales Invoice"}},
		target_doc, set_missing_values
	)
	
	doclist.set_missing_values()
	
	return doclist
