from frappe import _


def get_data():
	return {
		"fieldname": "site_measurement_log",
		"non_standard_fieldnames": {"BF Variation Order": "measurement_log"},
		"internal_links": {
			"BF Contract": "contract",
			"BF Bill of Quantities": "boq",
		},
		"transactions": [
			{"label": _("Source"), "items": ["BF Contract", "BF Bill of Quantities"]},
			{"label": _("Variations"), "items": ["BF Variation Order"]},
		],
	}
