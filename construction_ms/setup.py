import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():

    child_fields = [
        {
            "fieldname": "bf_boq",
            "label": "BF Bill of Quantities",
            "fieldtype": "Link",
            "options": "BF Bill of Quantities",
            "insert_after": "item_code",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "bf_boq_item",
            "label": "BF BOQ Item Reference",
            "fieldtype": "Data",
            "insert_after": "item_code",
            "read_only": 1,
            "hidden": 1,
        },
    ]

    create_custom_fields({"Material Request Item": child_fields})

def get_material_request_dashboard(data):
    if "internal_links" not in data:
        data["internal_links"] = {}
        
    data["internal_links"]["BF Bill of Quantities"] = ["items", "bf_boq"]
    
    data["transactions"].append({
        "label": "Construction",
        "items": ["BF Bill of Quantities"]
    })
    return data
