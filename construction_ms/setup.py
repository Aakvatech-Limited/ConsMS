import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():

    child_fields = [
        {
            "fieldname": "ge_boq",
            "label": "GE Bill of Quantities",
            "fieldtype": "Link",
            "options": "GE Bill of Quantities",
            "insert_after": "item_code",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "ge_boq_item",
            "label": "GE BOQ Item Reference",
            "fieldtype": "Data",
            "insert_after": "item_code",
            "read_only": 1,
            "hidden": 1,
        },
    ]

    create_custom_fields({"Material Request Item": child_fields})
