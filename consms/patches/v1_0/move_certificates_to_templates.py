"""Payment certificates now follow a Certificate Template.

Contracts get the default template; submitted certificates keep their figures as
typed lines, so old certificates print exactly as they were certified.
"""

import frappe
from frappe.utils import flt

from consms.construction_management.certificate_templates import ensure_certificate_templates

SNAPSHOT = (
	("Work this certificate", "Add", "this_period_work", "Work"),
	("Add: Value of materials on site", "Add", "materials_on_site", "Materials on Site"),
	("Less: Retention", "Less", "retention_deduction", "Retention"),
	("Less: Advance recovery", "Less", "advance_payment_recovery", "Advance Recovery"),
	("Add: Retention released", "Add", "retention_release", "Retention Release"),
	("Less: Liquidated damages", "Less", "liquidated_damages", "Liquidated Damages"),
	("Add: VAT", "Add", "vat_amount", "VAT"),
)


def execute():
	ensure_certificate_templates()
	default = frappe.db.get_single_value("BF Construction Settings", "default_certificate_template")
	frappe.db.sql("update `tabBF Contract` set certificate_template = %s where ifnull(certificate_template, '') = ''", default)

	for claim in frappe.get_all("BF Progress Claim", filters={"docstatus": 1}, pluck="name"):
		if frappe.db.exists("BF Certificate Line", {"parent": claim, "parenttype": "BF Progress Claim"}):
			continue
		values = frappe.db.get_value("BF Progress Claim", claim, [f for _l, _t, f, _r in SNAPSHOT] + ["contract"], as_dict=True)
		running, idx = 0.0, 0
		for label, line_type, field, role in SNAPSHOT:
			amount = flt(values[field])
			if not amount and role != "Work":
				continue
			idx += 1
			running += amount if line_type == "Add" else -amount
			frappe.get_doc({
				"doctype": "BF Certificate Line", "parent": claim, "parenttype": "BF Progress Claim", "parentfield": "certificate_lines",
				"idx": idx, "label": label, "line_type": line_type, "calculation": "Typed Amount", "role": role,
				"amount": amount, "running_total": running, "to_date_amount": amount,
			}).db_insert()
		frappe.db.set_value("BF Progress Claim", claim, {
			"certificate_type": "Interim",
			"certificate_template": frappe.db.get_value("BF Contract", values.contract, "certificate_template"),
		}, update_modified=False)
