"""VAT moves from the certificate templates to the contract (VAT Status and Basis) and Construction Settings (VAT Rate).

Each contract keeps the VAT its template charged: on the work without exempt bills -> Gross Work, on the running
total after deductions -> Net after Deductions, no VAT line -> Exempt. Then the VAT lines leave the payment
certificate templates (BOQ tender summaries keep theirs: VAT is part of the bid price).
"""

import frappe


def execute():
	if not frappe.db.get_single_value("BF Construction Settings", "vat_rate"):
		frappe.db.set_single_value("BF Construction Settings", "vat_rate", 18)

	default = frappe.db.get_single_value("BF Construction Settings", "default_certificate_template")
	vat_lines = {
		row.parent: row
		for row in frappe.get_all("BF Certificate Template Line", filters={"role": "VAT", "parenttype": "BF Certificate Template"},
			fields=["parent", "percentage_of"])
	}
	for contract in frappe.get_all("BF Contract", fields=["name", "certificate_template"]):
		line = vat_lines.get(contract.certificate_template or default)
		if not line:
			status, basis = "Exempt", "Gross Work"
		elif line.percentage_of == "Running Total":
			status, basis = "Standard Rated", "Net after Deductions"
		else:
			status, basis = "Standard Rated", "Gross Work"
		frappe.db.set_value("BF Contract", contract.name, {"vat_status": status, "vat_basis": basis}, update_modified=False)

	payment_templates = frappe.get_all("BF Certificate Template", filters={"used_for": "Payment Certificate"}, pluck="name")
	if payment_templates:
		frappe.db.delete("BF Certificate Template Line", {"parent": ["in", payment_templates], "role": "VAT"})
		for name in payment_templates:
			for idx, row in enumerate(frappe.get_all("BF Certificate Template Line", filters={"parent": name}, pluck="name", order_by="idx"), 1):
				frappe.db.set_value("BF Certificate Template Line", row, "idx", idx, update_modified=False)
