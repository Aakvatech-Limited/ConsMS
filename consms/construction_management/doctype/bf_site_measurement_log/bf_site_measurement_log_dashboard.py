from frappe import _


def get_data():
	return {
		"fieldname": "site_measurement_log",
		"internal_links": {
			"BF Contract": "contract",
			"BF Bill of Quantities": "boq",
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Contract", "BF Bill of Quantities"]},
		],
	}
