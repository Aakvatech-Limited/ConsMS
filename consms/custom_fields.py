import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_custom_fields


def create_custom_fields():
    # The certificate an invoice comes from: client IPC -> Sales Invoice, subcontractor IPC -> Purchase Invoice.
    # Filled by the system; hidden on invoices that do not come from a certificate.
    claim_links = [
        {
            "fieldname": "bf_contract",
            "label": "Construction Contract",
            "fieldtype": "Link",
            "options": "BF Contract",
            "insert_after": "project",
            "read_only": 1,
            "depends_on": "eval:doc.bf_contract",
        },
        {
            "fieldname": "bf_progress_claim",
            "label": "Progress Claim (IPC)",
            "fieldtype": "Link",
            "options": "BF Progress Claim",
            "insert_after": "bf_contract",
            "read_only": 1,
            "depends_on": "eval:doc.bf_progress_claim",
        },
    ]
    custom_fields = {
        "Sales Invoice": claim_links + [
            {
                "fieldname": "bf_advance_payment",
                "label": "Advance Payment (Contract)",
                "fieldtype": "Check",
                "insert_after": "bf_progress_claim",
                "read_only": 1,
                "depends_on": "eval:doc.bf_advance_payment",
            }
        ],
        "Purchase Invoice": claim_links,
        # the kind of work, for filters and reports only; shown on the contracts too
        "Project": [
            {
                "fieldname": "construction_type",
                "label": "Construction Type",
                "fieldtype": "Select",
                "options": "\nBuilding\nRoad\nBridge\nWater Supply\nIrrigation\nSewerage\nElectrical\nOther",
                "insert_after": "project_type",
                "in_standard_filter": 1,
            }
        ],
    }
    _create_custom_fields(custom_fields)
