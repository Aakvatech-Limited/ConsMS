import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


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

def get_material_request_dashboard(data):
    if "internal_links" not in data:
        data["internal_links"] = {}
        
    data["internal_links"]["BF Bill of Quantities"] = ["items", "bf_boq"]
    
    data["transactions"].append({
        "label": "Construction",
        "items": ["BF Bill of Quantities"]
    })
    return data
