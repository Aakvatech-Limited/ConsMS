import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_custom_fields

def create_custom_fields():
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "bf_contract",
                "label": "Construction Contract",
                "fieldtype": "Link",
                "options": "BF Contract",
                "insert_after": "project",
                "read_only": 1
            },
            {
                "fieldname": "bf_progress_claim",
                "label": "Progress Claim (IPC)",
                "fieldtype": "Link",
                "options": "BF Progress Claim",
                "insert_after": "bf_contract",
                "read_only": 1
            }
        ]
    }
    _create_custom_fields(custom_fields)
