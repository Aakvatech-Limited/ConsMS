"""Daily reminders for documents about to expire: contract submittals and bid securities."""

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

	for t in frappe.get_all(
		"BF Tender",
		filters=[
			["bid_security_expiry_date", "is", "set"],
			["bid_security_expiry_date", "<=", add_days(today(), BID_SECURITY_DAYS)],
			["bid_security_status", "not in", ["Returned", "Forfeited"]],
			["docstatus", "!=", 2],
		],
		fields=["name", "owner", "tender_name", "bid_security_expiry_date"],
	):
		remind(
			"BF Tender",
			t.name,
			t.owner,
			key=f"bid-security:{t.name}:{t.bid_security_expiry_date}",
			text=_("Bid security for tender {0} expires on {1}. Extend it or follow up its return.").format(
				t.tender_name, formatdate(t.bid_security_expiry_date)
			),
			date=t.bid_security_expiry_date,
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
