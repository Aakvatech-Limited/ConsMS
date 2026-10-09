"""Values for the Construction MS workspace number cards.

Progress Claims store cumulative figures (work executed, retention), so
totals that depend on them read only the latest submitted claim of each
contract. Net Amount Due is per claim, so it can be summed directly.
"""

import frappe
from frappe.utils import flt

CLAIM_LIST = ["List", "BF Progress Claim"]


def get_latest_client_claims():
	"""Latest submitted Client Claim of each contract."""
	return frappe.db.sql(
		"""
		select pc.name, pc.contract, pc.gross_valuation, pc.retention_deduction
		from `tabBF Progress Claim` pc
		where pc.docstatus = 1 and pc.claim_type = 'Client Claim'
			and pc.name = (
				select latest.name from `tabBF Progress Claim` latest
				where latest.contract = pc.contract and latest.docstatus = 1
					and latest.claim_type = 'Client Claim'
				order by latest.posting_date desc, latest.creation desc
				limit 1
			)
		""",
		as_dict=True,
	)


def get_certified_to_date():
	return flt(
		frappe.db.sql(
			"""
			select sum(net_amount_due) from `tabBF Progress Claim`
			where docstatus = 1 and claim_type = 'Client Claim'
			"""
		)[0][0]
	)


@frappe.whitelist()
def certified_to_date(filters=None):
	return {
		"value": get_certified_to_date(),
		"fieldtype": "Currency",
		"route": CLAIM_LIST,
		"route_options": {"docstatus": 1, "claim_type": "Client Claim"},
	}


@frappe.whitelist()
def retention_held(filters=None):
	return {
		"value": sum(flt(c.retention_deduction) for c in get_latest_client_claims()),
		"fieldtype": "Currency",
		"route": ["query-report", "Contract Status Summary"],
	}


@frappe.whitelist()
def claims_not_invoiced(filters=None):
	names = frappe.db.sql_list(
		"""
		select pc.name from `tabBF Progress Claim` pc
		where pc.docstatus = 1 and pc.claim_type = 'Client Claim'
			and not exists (
				select 1 from `tabSales Invoice` si
				where si.bf_progress_claim = pc.name and si.docstatus = 1
			)
		"""
	)
	return {
		"value": len(names),
		"fieldtype": "Int",
		"route": CLAIM_LIST,
		"route_options": {"name": ["in", names or [""]]},
	}


@frappe.whitelist()
def billed_percent(filters=None):
	contract_value = flt(
		frappe.db.sql(
			"""
			select sum(total_contract_amount) from `tabBF Contract`
			where docstatus = 1 and contract_type = 'Main Contract'
			"""
		)[0][0]
	)
	certified = sum(flt(c.gross_valuation) for c in get_latest_client_claims())
	percent = certified / contract_value * 100 if contract_value else 0
	return {
		# Sent as text: the card shortens numbers, which rounds small percentages
		"value": f"{percent:.2f}%",
		"fieldtype": "Data",
		"route": ["query-report", "Contract Status Summary"],
	}
