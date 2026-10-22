from frappe import _


def get_data():
	return {
		"fieldname": "tender",
		"transactions": [
			{"label": _("Source"), "items": ["BF Bill of Quantities"]},
			{"label": _("Contract"), "items": ["BF Contract"]},
			{"label": _("Correspondence"), "items": ["BF Correspondence"]},
		],
	}
