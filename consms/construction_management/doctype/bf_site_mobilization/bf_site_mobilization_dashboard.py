from frappe import _


def get_data():
	return {
		"fieldname": "site_mobilization",
		"internal_links": {
			"BF Contract": "contract",
			"Project Template": "mobilization_template",
			"Task": ["mobilization_checklist", "task"],
		},
		"transactions": [
			{"label": _("Contract"), "items": ["BF Contract"]},
			{"label": _("Tasks"), "items": ["Task", "Project Template"]},
		],
	}
