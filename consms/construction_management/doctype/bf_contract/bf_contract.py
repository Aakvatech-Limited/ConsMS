# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, date_diff, flt, getdate
from frappe.model.mapper import get_mapped_doc

class BFContract(Document):
	def validate(self):
		if flt(self.contingency_percentage) > 15:
			frappe.msgprint("Warning: A contingency exceeding 15% is unusually high for standard construction contracts and may require special budget approval. Please verify.", title="High Contingency Threshold", indicator="orange")
		
		self.contingency_amount = flt(self.contract_amount) * (flt(self.contingency_percentage) / 100.0)
		self.total_contract_amount = flt(self.contract_amount) + flt(self.contingency_amount)
		self.validate_submittals()
		self.calculate_period()

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
		for row in self.extensions:
			if row.status == "Approved" and not row.approved_on:
				row.approved_on = frappe.utils.today()
		self.approved_extension_days = sum(cint(r.days) for r in self.extensions if r.status == "Approved")
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
def make_site_measurement_log(source_name, target_doc=None):
	if not frappe.db.exists("BF Site Mobilization", {"contract": source_name, "docstatus": 1}):
		frappe.throw(_("Submit the Site Mobilization for this contract before recording measurements."))

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
	if not frappe.db.exists("BF Site Mobilization", {"contract": source_name, "docstatus": 1}):
		frappe.throw(_("Submit the Site Mobilization for this contract before recording daily reports."))

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
