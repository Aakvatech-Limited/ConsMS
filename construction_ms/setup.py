import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_migrate():
    # We strictly only modify Material Request and its child table as requested!
    create_custom_fields({

        "Material Request Item": [
            {
                "fieldname": "ge_boq_item",
                "label": "GE BOQ Item Reference",
                "fieldtype": "Data",
                "insert_after": "item_code",
                "read_only": 1,
                "hidden": 1
            }
        ]
    })
