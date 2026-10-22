from frappe import _


def get_data():
	"""Where the recipe is used: check this before amending it."""
	return {
		"fieldname": "rate_analysis",
		"transactions": [
			{"label": _("Used In"), "items": ["BF Budget", "BF Variation Order"]},
		],
	}
