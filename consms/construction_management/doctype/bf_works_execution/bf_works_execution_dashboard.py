from frappe import _


def get_data():
	return {
		"fieldname": "works_execution",
		"internal_links": {
			"BF Contract": "contract",
			"Project Template": "project_template",
			"Task": ["tasks", "task"],
		},
		"transactions": [
			{"label": _("Contract"), "items": ["BF Contract"]},
			{"label": _("Tasks"), "items": ["Task", "Project Template"]},
		],
	}
