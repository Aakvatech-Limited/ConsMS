# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


STATUS_TRANSITIONS = {
	"Submitted": ("Under Evaluation", "Rejected"),
	"Under Evaluation": ("Awarded", "Rejected"),
}


class BFTender(Document):
	def before_insert(self):
		self.status = "Draft"

	def on_submit(self):
		self.db_set("status", "Submitted")


@frappe.whitelist()
def set_status(tender_name, status):
	tender = frappe.get_doc("BF Tender", tender_name)
	tender.check_permission("submit")

	if tender.docstatus != 1:
		frappe.throw(_("Submit the Tender before changing its status."))

	if status not in STATUS_TRANSITIONS.get(tender.status, ()):
		frappe.throw(_("Cannot change Tender status from {0} to {1}.").format(tender.status, status))

	tender.db_set("status", status)
	tender.add_comment("Info", _("Status changed to {0}").format(status))
	return status


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
        document_types = frappe.get_all("BF Document Type", fields=["name"])
        for doc_type in document_types:
            doc.append("submittals", {"submittal_type": doc_type.name, "status": "Pending"})

    return doc
