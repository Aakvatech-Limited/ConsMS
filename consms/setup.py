import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from consms.construction_management.measurement import ensure_standard_construction_types
from consms.construction_management.tasks import ensure_mobilization_task_type
from consms.construction_management.uom import ensure_standard_uom_mappings


def after_migrate():

    parent_boq_field = [
        {
            "fieldname": "bf_boq",
            "label": "BF Bill of Quantities",
            "fieldtype": "Link",
            "options": "BF Bill of Quantities",
            "insert_after": "project",
        }
    ]

    boq_item_link_fields = [
        {
            "fieldname": "bf_boq",
            "label": "BF Bill of Quantities",
            "fieldtype": "Link",
            "options": "BF Bill of Quantities",
            "insert_after": "item_code",
        },
        {
            "fieldname": "bf_boq_item",
            "label": "BOQ Line Item",
            "fieldtype": "Link",
            "options": "BF BOQ Item",
            "insert_after": "bf_boq",
        },
        {
            "fieldname": "bf_boq_item_id",
            "label": "BOQ Item ID",
            "fieldtype": "Data",
            "insert_after": "bf_boq_item",
            "read_only": 1,
        },
    ]

    create_custom_fields({
        "Material Request": parent_boq_field,
        "Purchase Order": parent_boq_field,
        "Purchase Receipt": parent_boq_field,
        "Purchase Invoice": parent_boq_field,
        "Material Request Item": boq_item_link_fields,
        "Purchase Order Item": boq_item_link_fields,
        "Purchase Receipt Item": boq_item_link_fields,
        "Purchase Invoice Item": boq_item_link_fields,
    })

    # Budget link on buying documents, carried MR -> RFQ -> Supplier Quotation -> PO -> Receipt -> Invoice
    parent_budget_field = [
        {"fieldname": "bf_budget", "label": "BF Budget", "fieldtype": "Link", "options": "BF Budget",
         "insert_after": "bf_boq", "read_only": 1},
    ]
    item_budget_fields = [
        {"fieldname": "bf_budget", "label": "BF Budget", "fieldtype": "Link", "options": "BF Budget",
         "insert_after": "bf_boq_item_id", "read_only": 1},
        {"fieldname": "bf_budget_item", "label": "Budget Line", "fieldtype": "Link", "options": "BF Budget Item",
         "insert_after": "bf_budget", "read_only": 1},
    ]
    create_custom_fields({
        "Request for Quotation": parent_boq_field,
        "Supplier Quotation": parent_boq_field,
        "Request for Quotation Item": boq_item_link_fields,
        "Supplier Quotation Item": boq_item_link_fields,
    })
    buying = ["Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]
    create_custom_fields({
        **{dt: parent_budget_field for dt in buying},
        **{f"{dt} Item": item_budget_fields for dt in buying},
    })

    ensure_mobilization_task_type()
    ensure_standard_construction_types()
    ensure_standard_uom_mappings()
    ensure_tender_document_types()
    ensure_bid_security_types()
    ensure_activity_types()

def get_material_request_dashboard(data):
    if "internal_links" not in data:
        data["internal_links"] = {}
        
    data["internal_links"]["BF Bill of Quantities"] = ["items", "bf_boq"]
    data["internal_links"]["BF Budget"] = ["items", "bf_budget"]

    data["transactions"].append({
        "label": "Construction",
        "items": ["BF Budget", "BF Bill of Quantities"]
    })
    return data


TENDER_DOCUMENT_TYPES = [
    ("Bid Security / Bid Bond", 1, "Bank guarantee or insurance bond securing the bid; note its expiry date."),
    ("Business Registration Certificate (BRELA)", 1, "Company registration certificate."),
    ("Tax Clearance Certificate (TRA)", 1, "Valid tax clearance; note its expiry date."),
    ("Contractor Registration Certificate (CRB)", 1, "Contractors Registration Board certificate in the required class."),
    ("Signed Form of Tender", 1, "Form of tender signed by an authorised person."),
    ("Power of Attorney", 0, "Authority for the person signing the bid."),
    ("Company Profile", 0, "Experience, past projects, key staff and equipment."),
]


def ensure_tender_document_types():
    for name, mandatory, description in TENDER_DOCUMENT_TYPES:
        if not frappe.db.exists("BF Document Type", name):
            frappe.get_doc({"doctype": "BF Document Type", "document_name": name, "applies_to": "Tender",
                "is_mandatory": mandatory, "description": description}).insert(ignore_permissions=True)


def get_project_dashboard(data):
    """Project Connections: the construction documents first, then ERPNext's own."""
    data["transactions"] = [
        {"label": "Construction", "items": ["BF Tender", "BF Bill of Quantities", "BF Contract"]},
        {"label": "Site & Budget", "items": ["BF Budget", "BF Works Execution", "BF Site Daily Report", "BF Site Measurement Log"]},
        {"label": "Commercial", "items": ["BF Variation Order", "BF Extension of Time", "BF Progress Claim", "BF Correspondence"]},
    ] + data["transactions"]
    return data


BID_SECURITY_TYPES = [
    ("Bank Guarantee", "Unconditional guarantee issued by a bank."),
    ("Insurance Bond", "Bid bond issued by an insurance company."),
    ("Cash Deposit", "Cash or banker's cheque deposited with the client."),
    ("Bid Securing Declaration", "Signed declaration accepted instead of a guarantee (PPRA)."),
]


def ensure_bid_security_types():
    for name, description in BID_SECURITY_TYPES:
        if not frappe.db.exists("BF Bid Security Type", name):
            frappe.get_doc({"doctype": "BF Bid Security Type", "security_type": name, "description": description}).insert(ignore_permissions=True)


ACTIVITY_TYPES = [
    ("Mobilization", 1, "Standard Mobilization", "Site setup: camp, offices, crews and machines to site."),
    ("Construction", 0, None, "The main works, e.g. per bill or section of the BOQ."),
    ("Testing & Commissioning", 0, None, "Tests, trial runs and commissioning before handover."),
    ("Demobilization", 0, None, "Crews and machines leave; site cleared and reinstated."),
    ("Handover", 0, None, "Inspections, snag list and handover to the client."),
]


def ensure_activity_types():
    for name, is_mobilization, template, description in ACTIVITY_TYPES:
        if not frappe.db.exists("BF Activity Type", name):
            frappe.get_doc({"doctype": "BF Activity Type", "activity_type": name, "is_mobilization": is_mobilization,
                "default_project_template": template if template and frappe.db.exists("Project Template", template) else None,
                "description": description}).insert(ignore_permissions=True)
