"""Progress Claims now certify each period on its own (like client IPCs).

Old claims stored the retention held to date; turn it into the retention of that
certificate, fill the new per-certificate fields and the contract balances.
"""

import frappe
from frappe.utils import flt

from consms.construction_management.ipc import update_contract_balances


def execute():
	contracts = frappe.get_all("BF Progress Claim", filters={"docstatus": 1}, pluck="contract", distinct=True)
	for contract in contracts:
		claims = frappe.get_all(
			"BF Progress Claim",
			filters={"contract": contract, "docstatus": 1},
			fields=["name", "retention_deduction", "net_amount_due", "this_period_work"],
			order_by="posting_date asc, creation asc",
		)
		retention_before = net_before = 0.0
		for claim in claims:
			if claim.this_period_work:  # already converted
				continue
			work = flt(frappe.db.sql(
				"select sum(this_period_value) from `tabBF Progress Claim Item` where parent = %s", claim.name)[0][0])
			variations = flt(frappe.db.sql(
				"select sum(this_period_amount) from `tabBF Progress Claim Variation` where parent = %s", claim.name)[0][0])
			frappe.db.set_value("BF Progress Claim", claim.name, {
				"this_period_work": work + variations,
				"retention_deduction": flt(claim.retention_deduction) - retention_before,
				"amount_due": claim.net_amount_due,
				"previous_certified_amount": net_before,
			}, update_modified=False)
			retention_before = flt(claim.retention_deduction)
			net_before += flt(claim.net_amount_due)
		update_contract_balances(contract)
