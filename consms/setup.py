import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from consms.construction_management.certificate_templates import ensure_certificate_templates
from consms.construction_management.tasks import ensure_mobilization_task_type
from consms.construction_management.uom import ensure_standard_uom_mappings


def after_migrate():

    # Links that trace a purchase back to its BOQ line and budget line. "Get Items From > Budget" on the
    # Material Request fills them; they are carried MR -> RFQ -> Supplier Quotation -> PO -> Receipt -> Invoice.
    # Read only, and hidden on purchases that do not come from a budget. On item rows only the BOQ Line shows;
    # the other row links are for the code (the header already shows the BOQ and the budget).
    def budget_link(fieldname, label, options, insert_after, hidden=0):
        return {"fieldname": fieldname, "label": label, "fieldtype": "Link", "options": options,
                "insert_after": insert_after, "read_only": 1, "depends_on": f"eval:doc.{fieldname}", "hidden": hidden}

    header_links = [
        budget_link("bf_boq", "Bill of Quantities", "BF Bill of Quantities", "project"),
        budget_link("bf_budget", "Budget", "BF Budget", "bf_boq"),
    ]
    row_links = [
        budget_link("bf_boq", "Bill of Quantities", "BF Bill of Quantities", "item_code", hidden=1),
        budget_link("bf_boq_item", "BOQ Line", "BF BOQ Item", "bf_boq"),
        budget_link("bf_budget", "Budget", "BF Budget", "bf_boq_item", hidden=1),
        budget_link("bf_budget_item", "Budget Line", "BF Budget Item", "bf_budget", hidden=1),
    ]
    buying = ["Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]
    create_custom_fields({
        **{dt: header_links for dt in buying},
        **{f"{dt} Item": row_links for dt in buying},
        # Materials issued to site with a BOQ line (older stock issues): their cost in the books per BOQ line
        "Stock Entry Detail": [budget_link("bf_boq_item", "BOQ Line", "BF BOQ Item", "project")],
    })
    ensure_task_dimension()

    ensure_mobilization_task_type()
    ensure_standard_uom_mappings()
    ensure_tender_document_types()
    ensure_bid_security_types()
    ensure_activity_types()
    add_customer_types()
    ensure_certificate_templates()
    if not frappe.db.get_single_value("BF Construction Settings", "vat_rate"):
        frappe.db.set_single_value("BF Construction Settings", "vat_rate", 18)

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


def add_construction_links(data, links):
    """Connections from an ERPNext document to the construction documents that point at it: {doctype: field}."""
    data.setdefault("non_standard_fieldnames", {}).update(links)
    data.setdefault("transactions", []).append({"label": "Construction", "items": list(links)})
    return data


def get_customer_dashboard(data):
    return add_construction_links(data, {"BF Contract": "customer", "BF Progress Claim": "customer"})


def get_supplier_dashboard(data):
    return add_construction_links(data, {"BF Contract": "supplier", "BF Progress Claim": "supplier"})


def ensure_task_dimension():
    """Task is an accounting dimension: every cost (stock issue, supplier invoice, journal) can carry it.

    Labour gangs, fundis and hired machines are Suppliers paid by Purchase Invoice with the project and task.
    The Task fields are added here rather than by ERPNext's background job, so they exist right after migrate
    (that job also fails on newer Frappe versions, which reject its "distinct" query).
    """
    from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_doctypes_with_dimensions
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    if not frappe.db.exists("Accounting Dimension", {"document_type": "Task"}):
        # saved without its after_insert hook, which only queues ERPNext's job (the fields are added below)
        dimension = frappe.get_doc({"doctype": "Accounting Dimension", "document_type": "Task"})
        dimension.run_method("before_insert")
        dimension.set_new_name()
        dimension.db_insert()

    for doctype in get_doctypes_with_dimensions():
        meta = frappe.get_meta(doctype, cached=False)
        if meta.has_field("task"):
            continue
        insert_after = next((f for f in ("dimension_col_break", "accounting_dimensions_section", "cost_center") if meta.has_field(f)), None)
        create_custom_field(doctype, {"fieldname": "task", "label": "Task", "fieldtype": "Link", "options": "Task",
            "insert_after": insert_after}, ignore_validate=True)
        frappe.clear_cache(doctype=doctype)


def get_task_dashboard(data):
    data = add_construction_links(data, {"BF Site Measurement Log": "task"})
    # the costs charged to the task: materials issued on site, supplier invoices, journals
    data["transactions"].append({"label": "Costs", "items": ["Stock Entry", "Purchase Invoice", "Journal Entry"]})
    return data


def get_project_dashboard(data):
    """Project Connections: the construction documents first, then ERPNext's own."""
    data["transactions"] = [
        {"label": "Construction", "items": ["BF Tender", "BF Bill of Quantities", "BF Contract"]},
        {"label": "Site & Budget", "items": ["BF Budget", "BF Works Execution", "BF Site Measurement Log"]},
        {"label": "Commercial", "items": ["BF Variation Order", "BF Extension of Time", "BF Progress Claim"]},
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


CUSTOMER_TYPES = ["Government Institution"]


def add_customer_types():
    """Clients such as RUWASA or TANROADS are government institutions, not companies."""
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    options = (frappe.get_meta("Customer").get_field("customer_type").options or "").split("\n")
    missing = [t for t in CUSTOMER_TYPES if t not in options]
    if missing:
        make_property_setter("Customer", "customer_type", "options", "\n".join(options + missing), "Text",
            validate_fields_for_doctype=False)
