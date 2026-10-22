# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, date_diff, flt, getdate
from frappe.model.mapper import get_mapped_doc

from consms.construction_management.doctype.bf_works_execution.bf_works_execution import is_mobilized

class BFContract(Document):
	def validate(self):
		if flt(self.contingency_percentage) > 15:
			frappe.msgprint("Warning: A contingency exceeding 15% is unusually high for standard construction contracts and may require special budget approval. Please verify.", title="High Contingency Threshold", indicator="orange")
		
		self.set_value_from_boq()
		self.contingency_amount = flt(self.contract_amount) * (flt(self.contingency_percentage) / 100.0)
		self.total_contract_amount = flt(self.contract_amount) + flt(self.contingency_amount)
		self.validate_submittals()
		self.calculate_period()
		self.set_payment_terms()

	def set_value_from_boq(self):
		"""Contract amount = BOQ bid price without VAT (tender summary), or the total of bills."""
		if self.docstatus:
			return
		if not self.boq and self.tender:
			from consms.construction_management.doctype.bf_tender.bf_tender import get_tender_boq

			self.boq = get_tender_boq(self.tender)
		if not self.boq:
			return
		boq = frappe.get_doc("BF Bill of Quantities", self.boq)
		if boq.summary_lines:
			vat = sum(flt(l.amount) for l in boq.summary_lines if l.role == "VAT" and not l.calculation_only)
			self.contract_amount = flt(boq.bid_price) - vat
			self.contract_sum_incl_vat = boq.bid_price
			# the tender summary already holds the contingency
			if self.is_new():
				self.contingency_percentage = 0
		else:
			self.contract_amount = boq.total_amount
			self.contract_sum_incl_vat = 0

	def on_submit(self):
		self.create_site_store()
		self.sync_project_dates()

	def create_site_store(self):
		"""Each contract gets its own store on site, under the company's warehouses."""
		if self.site_warehouse or not self.project:
			return
		company = frappe.db.get_value("Project", self.project, "company")
		self.db_set("site_warehouse", get_or_create_site_store(self.project, company))

	def before_update_after_submit(self):
		self.validate_submittals()
		self.lock_original_dates()
		self.calculate_period()
		self.set_payment_terms()

	def set_payment_terms(self):
		if not self.certificate_template:
			self.certificate_template = frappe.db.get_single_value("BF Construction Settings", "default_certificate_template")
		if not 0 <= flt(self.advance_payment_percentage) <= 100:
			frappe.throw(_("Advance Payment (%) must be between 0 and 100."))
		if flt(self.advance_payment_percentage):
			self.advance_payment_amount = flt(
				flt(self.total_contract_amount) * flt(self.advance_payment_percentage) / 100, 2
			)
		self.advance_balance = flt(self.advance_payment_amount) - flt(self.advance_recovered)

	def lock_original_dates(self):
		"""Original dates may be filled in once after submit, never changed: time changes go through extensions."""
		before = self.get_doc_before_save()
		for field in ("start_date", "original_completion_date"):
			old = before.get(field) if before else None
			if old and getdate(old) != getdate(self.get(field)):
				frappe.throw(
					_("{0} is already set to {1}. Record an Extension of Time instead of changing it.").format(
						_(self.meta.get_label(field)), frappe.utils.formatdate(old)
					)
				)

	def on_update_after_submit(self):
		self.sync_project_dates()

	def calculate_period(self):
		if self.start_date and self.original_completion_date:
			if getdate(self.original_completion_date) < getdate(self.start_date):
				frappe.throw(_("Original Completion Date cannot be before the Start Date."))
			self.contract_duration = date_diff(self.original_completion_date, self.start_date)
		self.approved_extension_days = cint(
			frappe.db.sql(
				"""select sum(days_approved) from `tabBF Extension of Time`
				where contract = %s and docstatus = 1 and status = 'Approved'""",
				self.name,
			)[0][0]
		) if not self.is_new() else 0
		self.revised_completion_date = (
			add_days(self.original_completion_date, self.approved_extension_days) if self.original_completion_date else None
		)

	def sync_project_dates(self):
		"""Keep the ERPNext Project's dates in line with the contract period (main contracts only)."""
		if self.contract_type != "Main Contract" or not self.project:
			return
		values = {}
		if self.start_date:
			values["expected_start_date"] = self.start_date
		if self.revised_completion_date:
			values["expected_end_date"] = self.revised_completion_date
		if self.actual_completion_date:
			values["actual_end_date"] = self.actual_completion_date
		if values:
			frappe.db.set_value("Project", self.project, values)

	def validate_submittals(self):
		for row in self.get("submittals"):
			if row.status in ("Approved", "Rejected") and not row.attachment:
				frappe.throw(
					_("Row {0}: attach the {1} document before marking it {2}.").format(
						row.idx, row.submittal_type, row.status
					)
				)

def get_or_create_site_store(project, company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"{project} Site Store - {abbr}"
	if not frappe.db.exists("Warehouse", name):
		parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]})
		frappe.get_doc(
			{"doctype": "Warehouse", "warehouse_name": f"{project} Site Store", "company": company, "parent_warehouse": parent}
		).insert(ignore_permissions=True)
	return name

@frappe.whitelist()
def make_works_execution(source_name, target_doc=None):
	def set_missing_values(source, target):
		# Start with Mobilization until the site is mobilized
		if not is_mobilized(source.name):
			target.activity_type = frappe.db.get_value("BF Activity Type", {"is_mobilization": 1}, "name")
		if target.activity_type:
			target.project_template = frappe.db.get_value(
				"BF Activity Type", target.activity_type, "default_project_template"
			)

	return get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Works Execution",
			"field_map": {
				"project": "project",
				"name": "contract"
			}
		}
	}, target_doc, set_missing_values)


def validate_mobilized(contract, what):
	if not is_mobilized(contract):
		frappe.throw(
			_("Submit a Works Execution of type Mobilization for this contract before recording {0}.").format(what)
		)

@frappe.whitelist()
def make_site_measurement_log(source_name, target_doc=None):
	validate_mobilized(source_name, _("measurements"))

	def set_missing_values(source, target):
		target.date = frappe.utils.today()

	doc = get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Site Measurement Log",
			"field_map": {
				"project": "project",
				"boq": "boq",
				"name": "contract"
			}
		}
	}, target_doc, set_missing_values)
	return doc

@frappe.whitelist()
def make_site_daily_report(source_name, target_doc=None):
	validate_mobilized(source_name, _("daily reports"))

	def set_missing_values(source, target):
		target.date = frappe.utils.today()
		target.source_warehouse = source.site_warehouse or frappe.db.get_single_value("Stock Settings", "default_warehouse")

	return get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Site Daily Report",
			"field_map": {"project": "project", "boq": "boq", "name": "contract"},
			"field_no_map": ["amended_from"],
		}
	}, target_doc, set_missing_values)

@frappe.whitelist()
def make_extension_of_time(source_name, target_doc=None):
	return get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Extension of Time",
			"field_map": {"project": "project", "name": "contract"},
			"field_no_map": ["amended_from", "status"],
		}
	}, target_doc)

@frappe.whitelist()
def make_variation_order(source_name, target_doc=None):
	doc = get_mapped_doc("BF Contract", source_name, {
		"BF Contract": {
			"doctype": "BF Variation Order",
			"field_map": {
				"project": "project",
				"name": "contract",
				"boq": "boq"
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


@frappe.whitelist()
def make_advance_payment_invoice(source_name):
	"""Sales Invoice for the contract's advance payment; it is recovered from the IPCs."""
	contract = frappe.get_doc("BF Contract", source_name)
	contract.check_permission("read")
	if not flt(contract.advance_payment_amount):
		frappe.throw(_("Set the Advance Payment on the contract first."))
	existing = frappe.db.get_value(
		"Sales Invoice", {"bf_contract": contract.name, "bf_advance_payment": 1, "docstatus": ["!=", 2]}, "name"
	)
	if existing:
		frappe.throw(_("Advance Payment Invoice {0} already exists for this contract.").format(existing))

	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = contract.customer
	invoice.project = contract.project
	invoice.company = frappe.db.get_value("Project", contract.project, "company") if contract.project else None
	invoice.bf_contract = contract.name
	invoice.bf_advance_payment = 1
	invoice.disable_rounded_total = 1
	invoice.append("items", {
		"item_code": frappe.db.get_single_value("BF Construction Settings", "default_progress_claim_item"),
		"item_name": _("Advance Payment"),
		"description": _("Advance Payment ({0}% of contract value) for Contract {1}, against Advance Payment Guarantee {2}").format(
			flt(contract.advance_payment_percentage) or "", contract.name, contract.advance_guarantee_no or ""),
		"qty": 1,
		"rate": contract.advance_payment_amount,
	})
	invoice.set_missing_values()
	# VAT is charged on the work in each certificate, so the advance itself carries none
	invoice.set("taxes", [])
	invoice.taxes_and_charges = None
	invoice.calculate_taxes_and_totals()
	return invoice
