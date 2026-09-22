from frappe import _

def get_data():
	return {
		"fieldname": "boq",
		"internal_links": {
			"Material Request": ["items", "bf_boq"]
		},
		"transactions": [
			{
				"label": _("Procurement"),
				"items": ["Material Request"]
			},
			{
				"label": _("Construction"),
				"items": ["BF Tender", "BF Contract"]
			}
		]
	}
