"""Remove parts of ConsMS that nothing uses (slim-down review, 22 Oct 2026).

Records only: the database columns of the removed field stay, as Frappe does for any deleted custom field.
"""

import frappe

NUMBER_CARDS = [
	"BOQ Value",
	"Total Awarded Contracts",
	"Works Execution in Progress",
	"Measurements This Month",
	"Total Variation Value",
	"Billed Percent",
	"Open Project Tasks",
	"Open Works Execution Tasks",
	"Tasks Completed This Month",
]
CHARTS = ["Contract Value by Project", "Works Execution by Activity Type", "Submittal Approval Rate"]
REPORT = "Variation vs Budget Report"
PRINT_FORMAT = "FIDIC IPC Certificate"


def execute():
	for name in frappe.get_all("Custom Field", filters={"fieldname": "bf_boq_item_id"}, pluck="name"):
		frappe.delete_doc("Custom Field", name, force=True)

	for name in NUMBER_CARDS:
		frappe.delete_doc_if_exists("Number Card", name, force=True)
	for name in CHARTS:
		frappe.delete_doc_if_exists("Dashboard Chart", name, force=True)
	frappe.delete_doc_if_exists("Report", REPORT, force=True)

	frappe.db.delete("Property Setter", {"property": "default_print_format", "value": PRINT_FORMAT})
	frappe.delete_doc_if_exists("Print Format", PRINT_FORMAT, force=True)

	# other workspaces or dashboards that showed them
	frappe.db.delete("Workspace Number Card", {"number_card_name": ["in", NUMBER_CARDS]})
	frappe.db.delete("Workspace Chart", {"chart_name": ["in", CHARTS]})
	frappe.db.delete("Dashboard Chart Link", {"chart": ["in", CHARTS]})
	frappe.db.delete("Workspace Link", {"link_to": REPORT})
	frappe.db.delete("Workspace Shortcut", {"link_to": REPORT})
