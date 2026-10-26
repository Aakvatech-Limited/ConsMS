# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
from frappe.utils import flt, getdate

from consms.construction_management.ipc import (
	calculate,
	earlier_claims,
	set_due_date,
	set_late_payment_interest,
	set_liquidated_damages,
	update_contract_balances,
)

class BFProgressClaim(Document):
	def validate(self):
		if self.period_from and self.period_to:
			if getdate(self.period_from) > getdate(self.period_to):
				frappe.throw(_("Period From cannot be after Period To."))

			overlapping = frappe.db.sql("""
				SELECT name FROM `tabBF Progress Claim`
				WHERE contract = %s AND docstatus < 2 AND name != %s
				AND (
					(period_from <= %s AND period_to >= %s) OR
					(period_from <= %s AND period_to >= %s) OR
					(period_from >= %s AND period_to <= %s)
				)
			""", (self.contract, self.name or "New", self.period_from, self.period_from, self.period_to, self.period_to, self.period_from, self.period_to))

			if overlapping:
				frappe.throw(_("There is already a Progress Claim ({0}) covering this time period for this Contract.").format(overlapping[0][0]))

		for var in self.get("variations", []):
			var.cumulative_amount = flt(var.previously_certified) + flt(var.this_period_amount)
			if flt(var.cumulative_amount) > flt(var.approved_amount):
				frappe.throw(_("Row {0}: Cumulative Claimed Amount ({1}) cannot exceed the Approved Amount ({2}) for Variation {3}.").format(
					var.idx, var.cumulative_amount, var.approved_amount, var.variation_order))

		set_due_date(self)
		self.calculate_totals()
		self.set_documents()

	def set_documents(self):
		"""Add the document types this certificate type needs (keeps rows already filled in)."""
		have = {row.document_type for row in self.documents}
		for doc_type in get_certificate_document_types(self.certificate_type):
			if doc_type not in have:
				self.append("documents", {"document_type": doc_type, "status": "Pending"})

	def before_submit(self):
		mandatory = set(frappe.get_all("BF Document Type", filters={"is_mandatory": 1}, pluck="name"))
		needed = set(get_certificate_document_types(self.certificate_type))
		missing = [row.document_type for row in self.documents
			if row.document_type in mandatory and row.document_type in needed and row.status != "Ready"]
		if missing:
			frappe.throw(
				_("Attach these documents and mark them Ready before submitting the certificate: {0}").format(
					", ".join(frappe.bold(d) for d in missing)),
				title=_("Supporting documents missing"),
			)
		for row in self.documents:
			if row.status == "Ready" and not row.attachment:
				frappe.throw(_("Row {0}: attach {1} before marking it Ready.").format(row.idx, frappe.bold(row.document_type)))

	def calculate_totals(self):
		calculate(self)

	def before_update_after_submit(self):
		# certificate lines share a child doctype with BOQ summaries (editable after submit there), not here
		before = self.get_doc_before_save()
		old = [(l.label, flt(l.amount)) for l in before.certificate_lines] if before else []
		if old != [(l.label, flt(l.amount)) for l in self.certificate_lines]:
			frappe.throw(_("The lines of a submitted certificate cannot be changed. Cancel and amend it instead."))
		# the engineer often certifies after the certificate is submitted
		set_due_date(self)

	def on_submit(self):
		update_contract_balances(self.contract)

	def on_cancel(self):
		update_contract_balances(self.contract)


def get_certificate_document_types(certificate_type):
	scopes = {"Interim": ["All Certificates"],
		"Substantial Completion": ["All Certificates", "Substantial Completion and Final"],
		"Final": ["All Certificates", "Substantial Completion and Final", "Final"]}[certificate_type or "Interim"]
	return frappe.get_all("BF Document Type",
		filters={"applies_to": "Payment Certificate", "certificate_types": ["in", scopes]},
		pluck="name", order_by="is_mandatory desc, name")


@frappe.whitelist()
def fetch_measurements(claim_name, contract, period_from=None, period_to=None):
	doc = frappe.get_doc("BF Progress Claim", claim_name)
	doc.check_permission("write")
	boq_name = frappe.db.get_value("BF Contract", contract, "boq")

	if not boq_name:
		frappe.throw(_("The selected Contract does not have an attached BOQ."))

	boq_items = frappe.get_all(
		"BF BOQ Item",
		filters={"parent": boq_name},
		fields=["name", "item_no", "description", "bill", "uom", "unit_rate", "vat_exempt"],
		order_by="idx",
	)

	# Measurements of this period
	filters = {"contract": contract, "docstatus": 1}
	if period_from and period_to:
		filters["date"] = ["between", [period_from, period_to]]
	elif period_from:
		filters["date"] = [">=", period_from]
	elif period_to:
		filters["date"] = ["<=", period_to]

	period_qtys = {}
	logs = frappe.get_all("BF Site Measurement Log", filters=filters, pluck="name")
	if logs:
		for mi in frappe.get_all("BF Measurement Item", filters={"parent": ["in", logs]}, fields=["boq_item", "total_quantity"]):
			period_qtys[mi.boq_item] = period_qtys.get(mi.boq_item, 0.0) + flt(mi.total_quantity)

	# Earlier certificates
	condition, values = earlier_claims(frappe._dict(doc.as_dict(), contract=contract, period_to=period_to or doc.period_to))
	past_claims = frappe.db.sql_list(f"select name from `tabBF Progress Claim` claim where {condition}", values)
	prev_qtys, prev_var_claims = {}, {}
	if past_claims:
		for pi in frappe.get_all("BF Progress Claim Item", filters={"parent": ["in", past_claims]}, fields=["boq_item", "this_period_qty"]):
			prev_qtys[pi.boq_item] = prev_qtys.get(pi.boq_item, 0.0) + flt(pi.this_period_qty)
		for pvi in frappe.get_all("BF Progress Claim Variation", filters={"parent": ["in", past_claims]}, fields=["variation_order", "this_period_amount"]):
			prev_var_claims[pvi.variation_order] = prev_var_claims.get(pvi.variation_order, 0.0) + flt(pvi.this_period_amount)

	doc.set("variations", [])
	# BOQ-line changes and new items are paid through measurement; only lump sums are claimed by amount
	for v in frappe.get_all("BF Variation Order", filters={"contract": contract, "docstatus": 1, "lump_sum_amount": [">", 0]},
			fields=["name", "reason", "lump_sum_amount"]):
		prev_claimed = prev_var_claims.get(v.name, 0.0)
		remaining = max(flt(v.lump_sum_amount) - prev_claimed, 0.0)
		doc.append("variations", {
			"variation_order": v.name,
			"variation_reason": v.reason,
			"approved_amount": flt(v.lump_sum_amount),
			"previously_certified": prev_claimed,
			"this_period_amount": remaining,
		})

	doc.set("claim_items", [])
	for item in boq_items:
		prev_qty = prev_qtys.get(item.name, 0.0)
		this_qty = period_qtys.get(item.name, 0.0)
		# negative quantities are corrections of earlier measurements
		if prev_qty or this_qty:
			doc.append("claim_items", {
				"boq_item": item.name,
				"item_no": item.item_no,
				"bill": item.bill,
				"vat_exempt": item.vat_exempt,
				"item_description": item.description,
				"uom": item.uom,
				"unit_rate": item.unit_rate,
				"previous_qty": prev_qty,
				"this_period_qty": this_qty,
			})

	doc.period_from, doc.period_to = period_from or doc.period_from, period_to or doc.period_to
	if not doc.certificate_lines:
		calculate(doc)
	set_liquidated_damages(doc)
	set_late_payment_interest(doc)
	doc.save()

	return {"status": "success", "count": len(doc.claim_items)}


def set_claim_vat(invoice, claim, template_doctype):
	"""The certificate's own VAT (on the work, excluding VAT-exempt lines), not a % of the net amount."""
	invoice.set("taxes", [])
	invoice.taxes_and_charges = None
	if not flt(claim.vat_amount):
		return

	template = get_default_taxes_and_charges(template_doctype, company=invoice.company) or {}
	accounts = [row.get("account_head") for row in template.get("taxes") or [] if row.get("account_head")]
	if not accounts:
		# no default template: use the company's only active one
		templates = frappe.get_all(template_doctype, filters={"company": invoice.company, "disabled": 0}, pluck="name")
		if len(templates) == 1:
			accounts = [row.account_head for row in frappe.get_doc(template_doctype, templates[0]).taxes if row.account_head]
	if not accounts:
		frappe.throw(
			_("Set a default {0} with the VAT account for company {1}, so the certificate's VAT can be charged.").format(
				_(template_doctype), invoice.company
			)
		)

	row = {
		"charge_type": "Actual",
		"account_head": accounts[0],
		"description": "{0} - {1}".format(
			", ".join(line.label for line in claim.certificate_lines if line.role == "VAT") or _("VAT"), claim.name
		),
		"tax_amount": claim.vat_amount,
	}
	if template_doctype == "Purchase Taxes and Charges Template":
		row.update({"category": "Total", "add_deduct_tax": "Add"})
	invoice.append("taxes", row)


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
	doclist.disable_rounded_total = 1  # the invoice must equal the certificate to the cent
	claim = frappe.get_doc("BF Progress Claim", source_name)
	if claim.due_date and getdate(claim.due_date) >= getdate(doclist.posting_date):
		# the client pays by the certificate's due date, not by the customer's usual terms
		doclist.payment_terms_template = None
		doclist.set("payment_schedule", [])
		doclist.due_date = claim.due_date
	set_claim_vat(doclist, claim, "Sales Taxes and Charges Template")
	doclist.calculate_taxes_and_totals()
	
	return doclist

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
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
			"description": f"Subcontractor Claim for Contract {source.contract}: {source.claim_title}",
			"qty": 1,
			"rate": source.net_amount_due,
			"amount": source.net_amount_due
		})

	doclist = get_mapped_doc(
		"BF Progress Claim", source_name,
		{"BF Progress Claim": {"doctype": "Purchase Invoice"}},
		target_doc, set_missing_values
	)
	
	doclist.set_missing_values()
	doclist.disable_rounded_total = 1
	set_claim_vat(doclist, frappe.get_doc("BF Progress Claim", source_name), "Purchase Taxes and Charges Template")
	doclist.calculate_taxes_and_totals()
	
	return doclist
