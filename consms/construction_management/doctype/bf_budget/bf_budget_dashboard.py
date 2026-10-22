from frappe import _


def get_data():
	return {
		"fieldname": "bf_budget",
		"internal_links": {
			"BF Contract": "contract",
			"BF Bill of Quantities": "boq",
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Contract", "BF Bill of Quantities"]},
			{"label": _("Procurement"), "items": ["Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
		],
	}
