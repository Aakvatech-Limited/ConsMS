import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
    # Fix pre-existing custom fields where fieldtype was Data
    existing_custom_fields = frappe.db.get_all(
        "Custom Field",
        filters={"fieldname": "bf_boq_item", "fieldtype": "Data"},
        pluck="name"
    )
    for cf_name in existing_custom_fields:
        frappe.db.set_value("Custom Field", cf_name, {
            "fieldtype": "Link",
            "options": "BF BOQ Item",
            "label": "BOQ Line Item",
            "read_only": 0,
            "hidden": 0
        })

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
    ]

    create_custom_fields({
        "Material Request Item": boq_item_link_fields,
        "Purchase Order Item": boq_item_link_fields,
        "Purchase Receipt Item": boq_item_link_fields,
        "Purchase Invoice Item": boq_item_link_fields,
    })

def get_material_request_dashboard(data):
    if "internal_links" not in data:
        data["internal_links"] = {}
        
    data["internal_links"]["BF Bill of Quantities"] = ["items", "bf_boq"]
    
    data["transactions"].append({
        "label": "Construction",
        "items": ["BF Bill of Quantities"]
    })
    return data
