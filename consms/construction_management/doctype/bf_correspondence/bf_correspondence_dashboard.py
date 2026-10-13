from frappe import _


def get_data():
	return {
		"fieldname": "reply_to",
		"internal_links": {"BF Contract": "contract", "BF Tender": "tender", "Project": "project"},
		"transactions": [
			{"label": _("Related"), "items": ["BF Contract", "BF Tender", "Project"]},
			{"label": _("Replies"), "items": ["BF Correspondence"]},
		],
	}
