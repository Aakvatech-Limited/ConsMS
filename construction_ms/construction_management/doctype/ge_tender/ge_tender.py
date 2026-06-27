# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class GETender(Document):
    pass


@frappe.whitelist()
def check_existing_contract(tender_name):
	# Safe backend check that doesn't trigger frontend permission errors
	return frappe.db.get_value("GE Contract", {"tender": tender_name, "docstatus": ["!=", 2]}, "name")

@frappe.whitelist()
def make_ge_contract(source_name, target_doc=None):
    # Security Rule: 1 Tender = 1 Contract
    existing_contract = frappe.db.exists("GE Contract", {"tender": source_name, "docstatus": ["!=", 2]})
    if existing_contract:
        frappe.throw(f"A Contract ({existing_contract}) already exists for this Tender. You cannot create multiple active contracts for a single tender.")

    doc = get_mapped_doc(
        "GE Tender",
        source_name,
        {
            "GE Tender": {
                "doctype": "GE Contract",
                "field_map": {"project": "project", "name": "tender"},
            }
        },
        target_doc,
    )

    if not doc.get("submittals"):
        document_types = frappe.get_all("GE Document Type", fields=["name"])
        for doc_type in document_types:
            doc.append("submittals", {"submittal_type": doc_type.name, "status": "Pending"})

    return doc
