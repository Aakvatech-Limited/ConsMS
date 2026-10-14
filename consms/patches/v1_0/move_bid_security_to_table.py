"""Move the single bid-security fields on BF Tender into the Bid Securities table."""

import frappe

from consms.setup import ensure_bid_security_types


def execute():
	columns = frappe.db.get_table_columns("BF Tender")
	if "bid_security_type" not in columns:
		return
	ensure_bid_security_types()
	rows = frappe.db.sql(
		"""
		select name, bid_security_type, bid_security_amount, bid_security_number, bid_security_issuer,
			bid_security_issue_date, bid_security_expiry_date, bid_security_status, bid_security_returned_on
		from `tabBF Tender`
		where ifnull(bid_security_type, '') not in ('', 'Not Required')
		""",
		as_dict=True,
	)
	for r in rows:
		if frappe.db.exists("BF Bid Security", {"parent": r.name}):
			continue
		security_type = {"Cash": "Cash Deposit"}.get(r.bid_security_type, r.bid_security_type)
		if not frappe.db.exists("BF Bid Security Type", security_type):
			frappe.get_doc({"doctype": "BF Bid Security Type", "security_type": security_type}).insert(ignore_permissions=True)
		status = r.bid_security_status or "Held by Client"
		row = frappe.get_doc({
			"doctype": "BF Bid Security", "parent": r.name, "parenttype": "BF Tender", "parentfield": "bid_securities", "idx": 1,
			"security_type": security_type, "amount": r.bid_security_amount, "guarantee_no": r.bid_security_number,
			"issued_by": r.bid_security_issuer, "issue_date": r.bid_security_issue_date, "expiry_date": r.bid_security_expiry_date,
			"status": status, "returned_on": r.bid_security_returned_on,
		})
		row.db_insert()
		held = r.bid_security_amount if status == "Held by Client" else 0
		frappe.db.set_value("BF Tender", r.name, "total_bid_security", held or 0, update_modified=False)
