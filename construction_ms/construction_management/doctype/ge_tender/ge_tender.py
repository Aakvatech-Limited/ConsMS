# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class GETender(Document):
    pass


@frappe.whitelist()
def make_ge_contract(source_name, target_doc=None):
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
