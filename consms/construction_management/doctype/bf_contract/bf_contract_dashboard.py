from frappe import _


def get_data():
	return {
		"fieldname": "contract",
		"non_standard_fieldnames": {
			"BF Contract": "main_contract",
			"Sales Invoice": "bf_contract",
		},
		"internal_links": {
			"BF Tender": "tender",
			"BF Bill of Quantities": "boq",
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Tender", "BF Bill of Quantities"]},
			{"label": _("Execution"), "items": ["BF Site Mobilization", "BF Site Measurement Log"]},
			{"label": _("Contract Changes"), "items": ["BF Variation Order"]},
			{"label": _("Subcontracts"), "items": ["BF Contract"]},
			{"label": _("Billing"), "items": ["BF Progress Claim", "Sales Invoice"]},
		],
	}
