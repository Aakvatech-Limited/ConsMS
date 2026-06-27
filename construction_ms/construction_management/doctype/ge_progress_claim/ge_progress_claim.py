# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class GEProgressClaim(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		total_work_executed = 0.0
		for item in self.claim_items:
			item.this_period_value = flt(item.this_period_qty) * flt(item.unit_rate)
			item.cumulative_qty = flt(item.previous_qty) + flt(item.this_period_qty)
			item.cumulative_value = flt(item.cumulative_qty) * flt(item.unit_rate)
			
			total_work_executed += item.cumulative_value

		self.total_work_executed = total_work_executed
		self.gross_valuation = flt(self.total_work_executed) + flt(self.materials_on_site)
		
		self.retention_deduction = (flt(self.retention_percentage) / 100.0) * self.gross_valuation
		
		# Deductions
		total_deductions = flt(self.retention_deduction) + flt(self.advance_payment_recovery) + flt(self.previous_certified_amount)
		self.net_amount_due = self.gross_valuation - total_deductions
		
		self.vat_amount = (flt(self.vat_percentage) / 100.0) * self.net_amount_due
		self.total_amount_certified = self.net_amount_due + self.vat_amount


@frappe.whitelist()
def fetch_measurements(claim_name, contract, period_from=None, period_to=None):
	doc = frappe.get_doc("GE Progress Claim", claim_name)
	contract_doc = frappe.get_doc("GE Contract", contract)
	boq_name = contract_doc.boq

	if not boq_name:
		frappe.throw("The selected Contract does not have an attached BOQ.")

	# 1. Fetch BOQ Items
	boq_items = frappe.get_all("GE BOQ Item", filters={"parent": boq_name}, fields=["name", "description", "uom", "unit_rate"])

	# 2. Fetch Measurements for this period
	filters = {"contract": contract, "docstatus": 1}
	if period_from: filters["date"] = [">=", period_from]
	if period_to: 
		if "date" in filters:
			filters["date"] = ["between", [period_from, period_to]]
		else:
			filters["date"] = ["<=", period_to]

	logs = frappe.get_all("GE Site Measurement Log", filters=filters, pluck="name")
	
	period_qtys = {}
	if logs:
		measurement_items = frappe.get_all("GE Measurement Item", 
			filters={"parent": ["in", logs]}, 
			fields=["boq_item", "total_quantity"]
		)
		for mi in measurement_items:
			period_qtys[mi.boq_item] = period_qtys.get(mi.boq_item, 0.0) + flt(mi.total_quantity)

	# 3. Fetch Previous IPCs for cumulative qtys
	past_claims = frappe.get_all("GE Progress Claim", 
		filters={"contract": contract, "docstatus": 1, "name": ["!=", claim_name]}, 
		pluck="name"
	)
	
	prev_qtys = {}
	prev_certified = 0.0
	if past_claims:
		past_items = frappe.get_all("GE Progress Claim Item", 
			filters={"parent": ["in", past_claims]}, 
			fields=["boq_item", "this_period_qty"]
		)
		for pi in past_items:
			prev_qtys[pi.boq_item] = prev_qtys.get(pi.boq_item, 0.0) + flt(pi.this_period_qty)
			
		# Get the total Gross Valuation of all past claims to subtract as Previous Certified Amount
		past_claim_docs = frappe.get_all("GE Progress Claim", filters={"name": ["in", past_claims]}, fields=["gross_valuation"])
		# Note: Standard practice is to subtract the Gross Valuation of previous IPCs from current Gross Valuation.
		# Wait, actually usually the most recent IPC's Gross Valuation is subtracted. But summing them is wrong if Gross is cumulative.
		# Since Gross Valuation is cumulative (based on cumulative_qty), we only need the MAX(Gross Valuation) of previous IPCs.
		if past_claim_docs:
			prev_certified = max([flt(p.gross_valuation) for p in past_claim_docs])

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
