import frappe


def execute():
	"""The workspace now shows Works Execution cards instead."""
	for card in ("Pending Mobilization Tasks", "Mobilizations in Progress"):
		frappe.delete_doc_if_exists("Number Card", card)
