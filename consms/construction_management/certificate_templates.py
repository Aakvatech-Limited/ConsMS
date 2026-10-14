"""Starter Certificate Templates, taken from real Gemen certificates (SEUWASA, TANROADS, FIDIC).

Each line: (label, Add/Less/Subtotal, amount from, rate, % of, options).
Users copy a template and change the lines for a new client; nothing here is fixed in the code.
"""

import frappe

W, P, T = "Work This Certificate", "Percentage", "Typed Amount"

PAYMENT_TEMPLATES = {
	"Ministry of Water (SEUWASA)": (
		"Retention 5% up to 5% of the contract, advance recovered 20% per certificate, 50% retention back on the last "
		"certificate, VAT 18% on the work excluding P&G (IPC No. 02 Seuwasa).",
		[
			("Completed execution of the works (this certificate)", "Add", W, 0, None, {"role": "Work"}),
			("Less: Retention 5% (to a maximum of 5% of the contract sum)", "Less", P, 5, W,
				{"role": "Retention", "limit": "% of Contract Value", "limit_rate": 5}),
			("Less: Advance recovery 20%", "Less", P, 20, W, {"role": "Advance Recovery", "limit": "Advance Payment"}),
			("Add: Value of materials on site", "Add", T, 0, None, {"role": "Materials on Site"}),
			("Add: 50% of retention (last certificate)", "Add", P, 50, "Retention Held",
				{"role": "Retention Release", "applies_to": "Final"}),
			("Add: VAT 18% (excluding P&G items)", "Add", P, 18, "Work This Certificate (excl. VAT-Exempt)", {"role": "VAT"}),
			("Less: Liquidated damages", "Less", T, 0, None,
				{"role": "Liquidated Damages", "limit": "% of Contract Value", "limit_rate": 10}),
		],
	),
	"TANROADS": (
		"Retention 10%, advance recovered as 30% of the work to date, the rest at substantial completion; 50% retention "
		"released at substantial completion and 50% at the final certificate; no VAT on the certificate (Msangazi Bridge).",
		[
			("Work done (this certificate)", "Add", W, 0, None, {"role": "Work"}),
			("Less: Retention 10%", "Less", P, 10, W, {"role": "Retention"}),
			("Less: Advance recovery 30% of work to date", "Less", P, 30, "Work to Date",
				{"role": "Advance Recovery", "deduct_previous": 1, "limit": "Advance Payment", "applies_to": "Interim Only"}),
			("Less: Recovery of the remaining advance", "Less", P, 100, "Advance Balance",
				{"role": "Advance Recovery", "applies_to": "Substantial Completion and Final"}),
			("Add: Release of 50% retention", "Add", P, 50, "Retention Held",
				{"role": "Retention Release", "applies_to": "Substantial Completion"}),
			("Add: Release of the remaining retention", "Add", P, 100, "Retention Held",
				{"role": "Retention Release", "applies_to": "Final"}),
			("Add: Interest for late payment", "Add", T, 0, None, {}),
			("Less: Liquidated damages", "Less", T, 0, None, {"role": "Liquidated Damages"}),
		],
	),
	"FIDIC (Price Adjustment, VAT on Net)": (
		"Retention 10% on work + price adjustment + contingencies, advance repaid 15% of the amount after retention, "
		"VAT 18% on the net (Kagera bridges).",
		[
			("Work done (this certificate)", "Add", W, 0, None, {"role": "Work"}),
			("Add: Price adjustment (Clause 45.1)", "Add", T, 0, None, {}),
			("Add: Provisional sums for physical contingencies", "Add", T, 0, None, {}),
			("Sub-total 1", "Subtotal", None, 0, None, {}),
			("Less: Retention 10% (Clause 46.1)", "Less", P, 10, "Running Total", {"role": "Retention"}),
			("Add: Release of retention (Clause 46.2)", "Add", T, 0, None, {"role": "Retention Release", "limit": "Retention Held"}),
			("Sub-total 2", "Subtotal", None, 0, None, {}),
			("Add: Advance payment (Clause 49.1)", "Add", T, 0, None, {"role": "Advance Payment"}),
			("Less: Repayment of advance 15%", "Less", P, 15, "Total at Line", {"line_no": 7, "role": "Advance Recovery", "limit": "Advance Payment"}),
			("Sub-total 3", "Subtotal", None, 0, None, {}),
			("Add: VAT 18%", "Add", P, 18, "Running Total", {"role": "VAT"}),
			("Add: Interest for delayed payment", "Add", T, 0, None, {}),
		],
	),
}

BOQ_TEMPLATES = {
	"Tender Summary A-I": (
		"A Total of bills, B less provisional sums, C sub-total, D contingency 10%, E sub-total, F variation of prices, "
		"G sub-total, H VAT 18%; bid price = A + D + F + H (Arusha Chini, Sange).",
		[
			("A. Total of Bills", "Add", "Total of Bills", 0, None, {}),
			("B. Less specified provisional sums", "Less", "Provisional Sums", 0, None, {"calculation_only": 1}),
			("C. Sub-total (A - B)", "Subtotal", None, 0, None, {}),
			("D. Add provisional sum of physical contingency 10%", "Add", P, 10, "Running Total", {}),
			("E. Sub-total (C + D)", "Subtotal", None, 0, None, {}),
			("F. Add provisional sum of variation of prices", "Add", T, 0, None, {}),
			("G. Sub-total (E + F)", "Subtotal", None, 0, None, {}),
			("H. Add VAT 18% of G", "Add", P, 18, "Running Total", {"role": "VAT"}),
		],
	),
	"Bills + VAT 18%": (
		"Total of bills plus 18% VAT.",
		[
			("Total of Bills", "Add", "Total of Bills", 0, None, {}),
			("Add: VAT 18%", "Add", P, 18, "Running Total", {"role": "VAT"}),
		],
	),
}


def ensure_certificate_templates():
	for used_for, templates in (("Payment Certificate", PAYMENT_TEMPLATES), ("BOQ Summary", BOQ_TEMPLATES)):
		for name, (description, lines) in templates.items():
			if frappe.db.exists("BF Certificate Template", name):
				continue
			doc = frappe.get_doc({"doctype": "BF Certificate Template", "template_name": name, "used_for": used_for, "description": description})
			for label, line_type, calculation, rate, percentage_of, options in lines:
				doc.append("lines", {
					"label": label,
					"line_type": line_type,
					"calculation": calculation or "Typed Amount",
					"rate": rate,
					"percentage_of": percentage_of,
					**options,
				})
			doc.insert(ignore_permissions=True)

	if not frappe.db.get_single_value("BF Construction Settings", "default_certificate_template"):
		frappe.db.set_single_value("BF Construction Settings", "default_certificate_template", "Ministry of Water (SEUWASA)")
