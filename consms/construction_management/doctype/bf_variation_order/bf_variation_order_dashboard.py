from frappe import _


def get_data():
	return {
		"fieldname": "variation_order",
		"internal_links": {"BF Contract": "contract"},
		"transactions": [
			{"label": _("Contract"), "items": ["BF Contract"]},
		],
	}
