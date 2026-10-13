from frappe import _


def get_data():
	return {
		"fieldname": "bf_budget",
		"internal_links": {
			"BF Contract": "contract",
			"BF Bill of Quantities": "boq",
			"Budget": "erp_budget",
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Contract", "BF Bill of Quantities"]},
			{"label": _("Procurement"), "items": ["Material Request", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
			{"label": _("Accounts Budget"), "items": ["Budget"]},
		],
	}
