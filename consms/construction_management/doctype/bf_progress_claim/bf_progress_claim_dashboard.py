from frappe import _


def get_data():
	return {
		"fieldname": "bf_progress_claim",
		"internal_links": {
			"BF Contract": "contract",
			"BF Bill of Quantities": "boq",
			"BF Variation Order": ["variations", "variation_order"],
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Contract", "BF Bill of Quantities"]},
			{"label": _("Variations"), "items": ["BF Variation Order"]},
			{"label": _("Accounting"), "items": ["Sales Invoice", "Purchase Invoice"]},
		],
	}
