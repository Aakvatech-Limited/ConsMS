"""Daily reminders for documents about to expire: contract submittals, bid securities and advance payment guarantees."""

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, today

SUBMITTAL_DAYS = 30
BID_SECURITY_DAYS = 14


def get_expiring_submittals(days=SUBMITTAL_DAYS):
	"""Submittals on submitted contracts that expire within `days` (or already expired)."""
	return frappe.db.sql(
		"""
		select s.name, s.parent as contract, s.submittal_type, s.expiry_date, c.owner
		from `tabBF Contract Submittal` s
		join `tabBF Contract` c on c.name = s.parent
		where c.docstatus = 1 and s.expiry_date is not null and s.expiry_date <= %(until)s
		""",
		{"until": add_days(today(), days)},
		as_dict=True,
	)


def send_expiry_reminders():
	send_response_reminders()
	send_advance_guarantee_reminders()
	for row in get_expiring_submittals():
		remind(
			"BF Contract",
			row.contract,
			row.owner,
			key=f"{row.name}:{row.expiry_date}",
			text=_("{0} on contract {1} expires on {2}. Renew it and attach the new document.").format(
				row.submittal_type, row.contract, formatdate(row.expiry_date)
			),
			date=row.expiry_date,
		)

	for row in frappe.db.sql(
		"""
		select bs.name, bs.parent, bs.security_type, bs.guarantee_no, bs.expiry_date, t.owner, t.tender_name
		from `tabBF Bid Security` bs
		join `tabBF Tender` t on t.name = bs.parent
		where t.docstatus < 2 and bs.status = 'Held by Client' and bs.expiry_date is not null and bs.expiry_date <= %(until)s
		""",
		{"until": add_days(today(), BID_SECURITY_DAYS)},
		as_dict=True,
	):
		remind(
			"BF Tender",
			row.parent,
			row.owner,
			key=f"bid-security:{row.name}:{row.expiry_date}",
			text=_("{0} {1} for tender {2} expires on {3}. Extend it or follow up its return.").format(
				row.security_type, row.guarantee_no or "", row.tender_name, formatdate(row.expiry_date)
			),
			date=row.expiry_date,
		)


def send_advance_guarantee_reminders():
	"""Advance payment guarantees expiring within 30 days while part of the advance is still to be recovered."""
	for c in frappe.get_all(
		"BF Contract",
		filters=[["docstatus", "=", 1], ["advance_guarantee_expiry", "is", "set"],
			["advance_guarantee_expiry", "<=", add_days(today(), SUBMITTAL_DAYS)], ["advance_balance", ">", 0]],
		fields=["name", "owner", "advance_guarantee_no", "advance_guarantee_expiry", "advance_balance"],
	):
		remind(
			"BF Contract",
			c.name,
			c.owner,
			key=f"advance-guarantee:{c.name}:{c.advance_guarantee_expiry}",
			text=_("Advance Payment Guarantee {0} on contract {1} expires on {2}; {3} of the advance is still to be recovered. Extend it.").format(
				c.advance_guarantee_no or "", c.name, formatdate(c.advance_guarantee_expiry),
				frappe.format_value(c.advance_balance, "Currency")),
			date=c.advance_guarantee_expiry,
		)


def send_response_reminders():
	"""Letters needing a reply that is due within 3 days or overdue."""
	for c in frappe.get_all(
		"BF Correspondence",
		filters=[["status", "=", "Awaiting Response"], ["response_due_date", "is", "set"], ["response_due_date", "<=", add_days(today(), 3)]],
		fields=["name", "owner", "subject", "response_due_date"],
	):
		remind(
			"BF Correspondence",
			c.name,
			c.owner,
			key=f"response:{c.name}:{c.response_due_date}",
			text=_("Response due on {0}: {1}").format(formatdate(c.response_due_date), c.subject),
			date=c.response_due_date,
		)


def remind(doctype, name, user, key, text, date):
	"""One ToDo per document and expiry date, so users are not reminded every day."""
	if frappe.db.exists("ToDo", {"reference_type": doctype, "reference_name": name, "description": ["like", f"%[{key}]%"]}):
		return
	frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": user,
			"reference_type": doctype,
			"reference_name": name,
			"date": date,
			"priority": "High",
			"description": f"{text} [{key}]",
		}
	).insert(ignore_permissions=True)
