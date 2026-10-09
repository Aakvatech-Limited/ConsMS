from frappe import _


def get_data():
	return {
		"fieldname": "mobilization_template",
		"transactions": [
			{"label": _("Used In"), "items": ["BF Site Mobilization"]},
		],
	}
