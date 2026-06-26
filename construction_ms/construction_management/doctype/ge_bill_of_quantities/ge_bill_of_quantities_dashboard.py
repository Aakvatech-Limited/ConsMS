from frappe import _

def get_data():
	return {
		"fieldname": "boq",
		"internal_links": {
			"Material Request": ["items", "ge_boq"]
		},
		"transactions": [
			{
				"label": _("Procurement"),
				"items": ["Material Request"]
			},
			{
				"label": _("Construction"),
				"items": ["GE Tender"]
			}
		]
	}
