from frappe import _


def get_data():
	return {
		"fieldname": "tender",
		"internal_links": {"BF Bill of Quantities": "boq"},
		"transactions": [
			{"label": _("Source"), "items": ["BF Bill of Quantities"]},
			{"label": _("Contract"), "items": ["BF Contract"]},
		],
	}
