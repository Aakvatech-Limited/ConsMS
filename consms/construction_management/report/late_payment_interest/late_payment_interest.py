# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""Each client certificate against its payment due date: what was paid when, days late and the interest owed."""

import frappe
from frappe import _
from frappe.utils import flt

from consms.construction_management.ipc import get_late_payments


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.contract:
		return get_columns(), [], _("Select a Contract.")
	terms = frappe.db.get_value("BF Contract", filters.contract, ["payment_period_days", "late_payment_interest_rate", "interest_clause"], as_dict=True)
	if not terms.payment_period_days:
		return get_columns(), [], _("Set the Payment Period (Days) on the contract first: certificates then get a due date.")

	data = get_late_payments(filters.contract, filters.as_at or frappe.utils.today())
	claimed = flt(frappe.db.sql(
		"select sum(late_payment_interest) from `tabBF Progress Claim` where contract = %s and docstatus = 1", filters.contract)[0][0])
	message = _("Payment within {0} days of certification; interest {1}% a year{2}.").format(
		terms.payment_period_days, flt(terms.late_payment_interest_rate), f" ({terms.interest_clause})" if terms.interest_clause else "")
	return get_columns(), data, message, None, get_summary(data, claimed)


def get_columns():
	return [
		{"label": _("Certificate"), "fieldname": "claim", "fieldtype": "Link", "options": "BF Progress Claim", "width": 150},
		{"label": _("Certified"), "fieldname": "certified_date", "fieldtype": "Date", "width": 100},
		{"label": _("Due"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Amount Due"), "fieldname": "amount", "fieldtype": "Currency", "width": 150},
		{"label": _("Sales Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
		{"label": _("Paid"), "fieldname": "paid", "fieldtype": "Currency", "width": 150},
		{"label": _("Last Paid"), "fieldname": "last_paid", "fieldtype": "Date", "width": 100},
		{"label": _("Unpaid"), "fieldname": "unpaid", "fieldtype": "Currency", "width": 140},
		{"label": _("Days Late"), "fieldname": "days_late", "fieldtype": "Int", "width": 90},
		{"label": _("Interest"), "fieldname": "interest", "fieldtype": "Currency", "width": 130,
		 "description": "Simple interest on each payment for the days after the due date, and on what is unpaid up to the date chosen."},
	]


def get_summary(data, claimed):
	owed = sum(flt(row.interest) for row in data)
	return [
		{"value": sum(1 for row in data if row.days_late), "indicator": "Red", "label": _("Certificates Paid Late or Overdue"), "datatype": "Int"},
		{"value": sum(flt(row.unpaid) for row in data), "indicator": "Orange", "label": _("Unpaid"), "datatype": "Currency"},
		{"value": owed, "indicator": "Blue", "label": _("Interest Owed"), "datatype": "Currency"},
		{"value": claimed, "indicator": "Green", "label": _("Interest Claimed on Certificates"), "datatype": "Currency"},
		{"value": max(owed - claimed, 0), "indicator": "Red", "label": _("Not Yet Claimed"), "datatype": "Currency"},
	]
