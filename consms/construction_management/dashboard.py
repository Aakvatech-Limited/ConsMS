"""Values for the Construction MS workspace number cards.

Progress Claims store the work to date (gross valuation), so totals of work
read only the latest submitted claim of each contract. Amounts due, retention
and advance recovery are per certificate, so they are summed.
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
	"""Each certificate deducts its own retention; releases pay part of it back."""
	held = frappe.db.sql(
		"""
		select coalesce(sum(retention_deduction), 0) - coalesce(sum(retention_release), 0)
		from `tabBF Progress Claim` where docstatus = 1 and claim_type = 'Client Claim'
		"""
	)[0][0]
	return {
		"value": flt(held),
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
def expiring_documents(filters=None):
	from consms.construction_management.reminders import get_expiring_submittals

	rows = get_expiring_submittals()
	return {
		"value": len(rows),
		"fieldtype": "Int",
		"route": ["List", "BF Contract"],
		"route_options": {"name": ["in", list({r.contract for r in rows}) or [""]]},
	}


@frappe.whitelist()
def pending_submittals(filters=None):
	"""Submittals still pending on submitted contracts the user may see (counted through the contract, not the child table)."""
	contracts = frappe.get_list("BF Contract", filters={"docstatus": 1}, pluck="name") if frappe.has_permission("BF Contract") else []
	rows = frappe.get_all(
		"BF Contract Submittal",
		filters={"parenttype": "BF Contract", "parent": ["in", contracts or [""]], "status": "Pending"},
		pluck="parent",
	)
	return {
		"value": len(rows),
		"fieldtype": "Int",
		"route": ["List", "BF Contract"],
		"route_options": {"name": ["in", list(set(rows)) or [""]]},
	}
