from frappe import _

def get_data():
	return {
		"fieldname": "bf_progress_claim",
		"transactions": [
			{
				"label": _("Accounting"),
				"items": ["Sales Invoice"]
			}
		]
	}
