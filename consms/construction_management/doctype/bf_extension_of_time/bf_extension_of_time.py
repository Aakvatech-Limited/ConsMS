# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, today


class BFExtensionofTime(Document):
	def before_insert(self):
		self.status = "Draft"
		self.days_approved = 0

	def validate(self):
		if cint(self.days_requested) <= 0:
			frappe.throw(_("Days Requested must be more than zero."))
		if frappe.db.get_value("BF Contract", self.contract, "docstatus") != 1:
			frappe.throw(_("Extensions of Time can only be requested on a submitted contract."))

	def on_submit(self):
		self.db_set("status", "Requested")

	def on_cancel(self):
		update_contract_extensions(self.contract)


@frappe.whitelist()
def set_decision(name, decision, days_approved=None, decision_date=None, reference=None, remarks=None):
	"""Approve (fully or partly) or reject a submitted extension request."""
	eot = frappe.get_doc("BF Extension of Time", name)
	eot.check_permission("submit")
	if eot.docstatus != 1 or eot.status != "Requested":
		frappe.throw(_("Only a submitted request with status Requested can be decided."))
	if decision not in ("Approved", "Rejected"):
		frappe.throw(_("Decision must be Approved or Rejected."))

	days = cint(days_approved) if decision == "Approved" else 0
	if decision == "Approved" and not 0 < days <= cint(eot.days_requested):
		frappe.throw(_("Days Approved must be between 1 and the {0} days requested.").format(eot.days_requested))

	eot.db_set({
		"status": decision,
		"days_approved": days,
		"decision_date": decision_date or today(),
		"decision_reference": reference,
		"decision_remarks": remarks,
	})
	eot.add_comment("Info", _("{0}: {1} of {2} days").format(decision, days, eot.days_requested))
	update_contract_extensions(eot.contract)
	return decision


def update_contract_extensions(contract_name):
	"""Contract revised completion = original completion + days approved on approved extensions."""
	contract = frappe.get_doc("BF Contract", contract_name)
	contract.calculate_period()
	contract.db_set({
		"approved_extension_days": contract.approved_extension_days,
		"revised_completion_date": contract.revised_completion_date,
	})
	contract.sync_project_dates()
