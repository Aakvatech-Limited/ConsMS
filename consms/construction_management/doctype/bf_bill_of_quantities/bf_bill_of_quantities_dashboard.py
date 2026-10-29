from frappe import _


def get_data():
	return {
		"fieldname": "boq",
		"non_standard_fieldnames": {
			"Material Request": "bf_boq",
			"Purchase Order": "bf_boq",
			"Purchase Receipt": "bf_boq",
			"Purchase Invoice": "bf_boq",
			"Request for Quotation": "bf_boq",
			"Supplier Quotation": "bf_boq",
		},
		"transactions": [
			{"label": _("Tender & Contract"), "items": ["BF Tender", "BF Contract"]},
			{"label": _("Budget & Changes"), "items": ["BF Budget", "BF Variation Order"]},
			{"label": _("Execution"), "items": ["BF Site Measurement Log", "BF Progress Claim"]},
			{"label": _("Procurement"), "items": ["Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
		],
	}
