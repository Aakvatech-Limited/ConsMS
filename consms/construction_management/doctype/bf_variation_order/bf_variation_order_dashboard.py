from frappe import _


def get_data():
	return {
		"fieldname": "variation_order",
		"internal_links": {
			"BF Contract": "contract",
			"BF Bill of Quantities": "boq",
			"BF Site Measurement Log": "measurement_log",
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Contract", "BF Bill of Quantities", "BF Site Measurement Log"]},
			{"label": _("Certified In"), "items": ["BF Progress Claim"]},
		],
	}
