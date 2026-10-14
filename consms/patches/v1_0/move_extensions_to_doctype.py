"""Turn the old Extensions of Time table rows on contracts into BF Extension of Time documents."""

import frappe

from consms.construction_management.doctype.bf_extension_of_time.bf_extension_of_time import update_contract_extensions


def execute():
	if not frappe.db.table_exists("BF Contract Extension"):
		return
	rows = frappe.db.sql("select * from `tabBF Contract Extension` where parenttype = 'BF Contract' order by parent, idx", as_dict=True)
	contracts = set()
	for r in rows:
		if frappe.db.get_value("BF Contract", r.parent, "docstatus") != 1:
			continue
		eot = frappe.get_doc({
			"doctype": "BF Extension of Time",
			"contract": r.parent,
			"request_date": r.request_date or frappe.utils.today(),
			"days_requested": r.days,
			"reason": r.reason or "Migrated from contract extensions table",
			"reference_no": r.reference,
			"attachment": r.attachment,
		}).insert(ignore_permissions=True)
		eot.submit()
		if r.status in ("Approved", "Rejected"):
			eot.db_set({
				"status": r.status,
				"days_approved": r.days if r.status == "Approved" else 0,
				"decision_date": r.approved_on or r.request_date,
			})
		contracts.add(r.parent)
	for contract in contracts:
		update_contract_extensions(contract)
	frappe.db.sql("delete from `tabBF Contract Extension`")
