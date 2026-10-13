# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

def get_document_types(applies_to):
	"""Document types required for a Tender or a Contract (including 'Both')."""
	return frappe.get_all(
		"BF Document Type", filters={"applies_to": ["in", [applies_to, "Both"]]}, pluck="name", order_by="is_mandatory desc, name"
	)


# Status after submit -> statuses it may move to
STATUS_TRANSITIONS = {"Bid Submitted": ("Awarded", "Lost")}


class BFTender(Document):
	def before_insert(self):
		self.status = "Draft"
		if not self.documents:
			for doc_type in get_document_types("Tender"):
				self.append("documents", {"document_type": doc_type, "status": "Pending"})

	def validate(self):
		mandatory = set(frappe.get_all("BF Document Type", filters={"is_mandatory": 1}, pluck="name"))
		for row in self.documents:
			if row.status == "Not Applicable" and row.document_type in mandatory:
				frappe.throw(_("Row {0}: {1} is mandatory and cannot be Not Applicable.").format(row.idx, frappe.bold(row.document_type)))
			if row.status == "Ready" and not row.attachment:
				frappe.throw(_("Row {0}: attach {1} before marking it Ready.").format(row.idx, frappe.bold(row.document_type)))

	def before_submit(self):
		pending = [row.document_type for row in self.documents if row.status == "Pending"]
		if pending:
			frappe.throw(
				_("These tender documents are still Pending: {0}. Mark each Ready (with attachment) or Not Applicable.").format(
					", ".join(frappe.bold(d) for d in pending)
				),
				title=_("Tender documents incomplete"),
			)
		if not self.boq or frappe.db.get_value("BF Bill of Quantities", self.boq, "docstatus") != 1:
			frappe.throw(_("Submit the priced Bill of Quantities for this tender before submitting the bid."))

	def on_submit(self):
		self.db_set("status", "Bid Submitted")


@frappe.whitelist()
def set_status(tender_name, status):
	tender = frappe.get_doc("BF Tender", tender_name)
	tender.check_permission("submit")

	if status not in STATUS_TRANSITIONS.get(tender.status, ()):
		frappe.throw(_("Cannot change Tender status from {0} to {1}.").format(tender.status, status))

	tender.db_set("status", status)
	tender.add_comment("Info", _("Marked as {0}").format(status))
	return status


@frappe.whitelist()
def make_bf_boq(source_name, target_doc=None):
	"""Tender -> BOQ: the BOQ is priced for this tender (one BOQ per tender)."""
	existing = frappe.db.get_value("BF Tender", source_name, "boq")
	if existing and frappe.db.get_value("BF Bill of Quantities", existing, "docstatus") != 2:
		frappe.throw(_("This tender already has Bill of Quantities {0}.").format(existing))

	return get_mapped_doc(
		"BF Tender",
		source_name,
		{
			"BF Tender": {
				"doctype": "BF Bill of Quantities",
				"field_map": {"project": "project", "name": "tender"},
				"field_no_map": ["status", "boq", "amended_from"],
			}
		},
		target_doc,
	)


@frappe.whitelist()
def check_existing_contract(tender_name):
	# Safe backend check that doesn't trigger frontend permission errors
	return frappe.db.get_value("BF Contract", {"tender": tender_name, "docstatus": ["!=", 2]}, "name")

@frappe.whitelist()
def make_bf_contract(source_name, target_doc=None):
    # Security Rule: 1 Tender = 1 Contract
    existing_contract = frappe.db.exists("BF Contract", {"tender": source_name, "docstatus": ["!=", 2]})
    if existing_contract:
        frappe.throw(f"A Contract ({existing_contract}) already exists for this Tender. You cannot create multiple active contracts for a single tender.")

    doc = get_mapped_doc(
        "BF Tender",
        source_name,
        {
            "BF Tender": {
                "doctype": "BF Contract",
                "field_map": {"project": "project", "name": "tender"},
            }
        },
        target_doc,
    )

    if not doc.get("submittals"):
        for doc_type in get_document_types("Contract"):
            doc.append("submittals", {"submittal_type": doc_type, "status": "Pending"})

    return doc
