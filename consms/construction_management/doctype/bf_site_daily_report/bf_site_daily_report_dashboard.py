from frappe import _


def get_data():
	return {
		"fieldname": "site_daily_report",
		"internal_links": {"BF Contract": "contract", "Stock Entry": "stock_entry"},
		"transactions": [
			{"label": _("Contract"), "items": ["BF Contract"]},
			{"label": _("Stock"), "items": ["Stock Entry"]},
		],
	}
