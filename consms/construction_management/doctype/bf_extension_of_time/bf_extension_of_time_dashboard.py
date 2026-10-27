from frappe import _


def get_data():
	return {
		"fieldname": "extension_of_time",
		"internal_links": {"BF Contract": "contract", "Project": "project"},
		"transactions": [
			{"label": _("Related"), "items": ["BF Contract", "Project"]},
		],
	}
