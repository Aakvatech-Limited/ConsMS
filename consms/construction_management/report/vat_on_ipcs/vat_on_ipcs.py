# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""Every submitted certificate with its VAT: what was certified, what was taxable, the VAT, and the invoice."""

import frappe
from frappe import _

from consms.construction_management.ipc import certificate_vat_figures


def execute(filters=None):
	filters = frappe._dict(filters or {})
	claim_type = filters.claim_type or "Client Claim"
	conditions = {"docstatus": 1, "claim_type": claim_type}
	if filters.contract:
		conditions["contract"] = filters.contract
	if filters.from_date or filters.to_date:
		conditions["posting_date"] = ["between", [filters.from_date or "1900-01-01", filters.to_date or "2999-12-31"]]

	invoice_doctype = "Sales Invoice" if claim_type == "Client Claim" else "Purchase Invoice"
	data, to_date = [], {}
	for name in frappe.get_all("BF Progress Claim", filters=conditions, pluck="name", order_by="contract, period_to, creation"):
		claim = frappe.get_doc("BF Progress Claim", name)
		f = certificate_vat_figures(claim)
		to_date[claim.contract] = to_date.get(claim.contract, 0) + f.vat
		data.append({
			"claim": claim.name,
			"posting_date": claim.posting_date,
			"contract": claim.contract,
			"certificate_type": claim.certificate_type,
			"work": f.work,
			"exempt": f.exempt,
			"taxable": f.taxable,
			"vat_base": f.base,
			"vat": f.vat,
			"vat_to_date": to_date[claim.contract],
			"amount_due": f.due,
			"invoice": frappe.db.get_value(invoice_doctype, {"bf_progress_claim": claim.name, "docstatus": 1}, "name"),
		})
	return get_columns(invoice_doctype), data, None, None, get_summary(data)


def get_columns(invoice_doctype):
	return [
		{"label": _("Certificate"), "fieldname": "claim", "fieldtype": "Link", "options": "BF Progress Claim", "width": 140},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Contract"), "fieldname": "contract", "fieldtype": "Link", "options": "BF Contract", "width": 160},
		{"label": _("Type"), "fieldname": "certificate_type", "fieldtype": "Data", "width": 110},
		{"label": _("Work This Certificate"), "fieldname": "work", "fieldtype": "Currency", "width": 140},
		{"label": _("VAT-Exempt"), "fieldname": "exempt", "fieldtype": "Currency", "width": 120},
		{"label": _("Taxable"), "fieldname": "taxable", "fieldtype": "Currency", "width": 140},
		{"label": _("VAT Base"), "fieldname": "vat_base", "fieldtype": "Currency", "width": 140},
		{"label": _("VAT"), "fieldname": "vat", "fieldtype": "Currency", "width": 130},
		{"label": _("VAT to Date"), "fieldname": "vat_to_date", "fieldtype": "Currency", "width": 130},
		{"label": _("Amount Due incl. VAT"), "fieldname": "amount_due", "fieldtype": "Currency", "width": 150},
		{"label": _(invoice_doctype), "fieldname": "invoice", "fieldtype": "Link", "options": invoice_doctype, "width": 150},
	]


def get_summary(data):
	return [
		{"value": len(data), "indicator": "Blue", "label": _("Certificates"), "datatype": "Int"},
		{"value": sum(d["taxable"] for d in data), "indicator": "Green", "label": _("Taxable Work"), "datatype": "Currency"},
		{"value": sum(d["vat"] for d in data), "indicator": "Orange", "label": _("VAT"), "datatype": "Currency"},
		{"value": sum(1 for d in data if not d["invoice"]), "indicator": "Red", "label": _("Not Invoiced"), "datatype": "Int"},
	]
