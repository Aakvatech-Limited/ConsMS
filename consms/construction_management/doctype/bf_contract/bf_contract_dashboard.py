from frappe import _

def get_data():
	return {
		"fieldname": "contract",
		"non_standard_fieldnames": {
			"Sales Invoice": "bf_contract"
		},
		"transactions": [
			{
				"label": _("Execution"),
				"items": ["BF Site Mobilization", "BF Measurement Log"]
			},
			{
				"label": _("Contract Changes"),
				"items": ["BF Variation Order"]
			},
			{
				"label": _("Billing"),
				"items": ["BF Progress Claim", "Sales Invoice"]
			}
		]
	}
