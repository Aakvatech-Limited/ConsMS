from frappe import _


def get_data():
	return {
		"fieldname": "site_mobilization",
		"internal_links": {
			"BF Contract": "contract",
			"BF Mobilization Template": "mobilization_template",
		},
		"transactions": [
			{"label": _("Contract"), "items": ["BF Contract"]},
			{"label": _("Template"), "items": ["BF Mobilization Template"]},
		],
	}
