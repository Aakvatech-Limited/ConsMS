"""Shared figures per BOQ line: measured progress, budget and actual cost."""

import frappe
from frappe.utils import flt


def get_measured_qty(contract):
	"""Quantity measured to date per BOQ line (submitted Site Measurement Logs)."""
	rows = frappe.db.sql(
		"""
		select mi.boq_item, sum(mi.total_quantity) as qty
		from `tabBF Measurement Item` mi
		join `tabBF Site Measurement Log` log on log.name = mi.parent
		where log.contract = %s and log.docstatus = 1
		group by mi.boq_item
		""",
		contract,
		as_dict=True,
	)
	return {r.boq_item: flt(r.qty) for r in rows}


def get_budget_cost(contract):
	"""Budget cost per BOQ line from the contract's current submitted budget."""
	budget = frappe.db.get_value("BF Budget", {"contract": contract, "docstatus": 1}, "name", order_by="creation desc")
	if not budget:
		return None, {}
	rows = frappe.get_all("BF Budget Item", filters={"parent": budget}, fields=["boq_item", "amount"])
	cost = {}
	for r in rows:
		cost[r.boq_item] = cost.get(r.boq_item, 0) + flt(r.amount)
	return budget, cost


def get_actual_cost(contract):
	"""Actual cost per BOQ line, from the books.

	Per BOQ line: materials issued on site (Stock Issues) and bought-in services or hire (Purchase
	Invoices) that carry the line. Everything else booked to the project's expense accounts is
	returned under None, so the total equals the project's expenses in the General Ledger.
	"""
	project = frappe.db.get_value("BF Contract", contract, "project")
	if not project:
		return {}

	cost = {}
	linked = frappe.db.sql(
		"""
		select sed.bf_boq_item as boq_item, sum(sed.amount) as amount
		from `tabStock Entry Detail` sed
		join `tabStock Entry` se on se.name = sed.parent
		where se.docstatus = 1 and se.purpose = 'Material Issue'
			and coalesce(sed.project, se.project) = %(project)s and ifnull(sed.bf_boq_item, '') != ''
		group by sed.bf_boq_item

		union all

		select pii.bf_boq_item, sum(pii.base_net_amount)
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		join `tabItem` item on item.name = pii.item_code
		where pi.docstatus = 1 and item.is_stock_item = 0 and pii.is_fixed_asset = 0
			and coalesce(pii.project, pi.project) = %(project)s and ifnull(pii.bf_boq_item, '') != ''
		group by pii.bf_boq_item
		""",
		{"project": project},
		as_dict=True,
	)
	for r in linked:
		cost[r.boq_item] = cost.get(r.boq_item, 0) + flt(r.amount)

	booked = flt(
		frappe.db.sql(
			"""
			select sum(gle.debit - gle.credit)
			from `tabGL Entry` gle
			join `tabAccount` account on account.name = gle.account
			where gle.project = %s and gle.is_cancelled = 0 and account.root_type = 'Expense'
			""",
			project,
		)[0][0]
	)
	not_linked = booked - sum(cost.values())
	if abs(not_linked) >= 0.01:
		cost[None] = not_linked
	return cost


def get_committed_cost(contract):
	"""Money promised on submitted Purchase Orders that is not in the books yet, per BOQ line.

	Materials: the part not received yet (their cost reaches the books when issued on site).
	Services and hire: the part not invoiced yet.
	"""
	project = frappe.db.get_value("BF Contract", contract, "project")
	if not project:
		return {}
	rows = frappe.db.sql(
		"""
		select poi.bf_boq_item as boq_item, sum(
			case when item.is_stock_item = 1
				then greatest(poi.qty - poi.received_qty, 0) * poi.base_net_rate
				else greatest(poi.base_net_amount - poi.billed_amt * po.conversion_rate, 0)
			end) as amount
		from `tabPurchase Order Item` poi
		join `tabPurchase Order` po on po.name = poi.parent
		join `tabItem` item on item.name = poi.item_code
		where po.docstatus = 1 and po.status not in ('Closed', 'Completed')
			and coalesce(poi.project, po.project) = %s and ifnull(poi.bf_boq_item, '') != ''
		group by poi.bf_boq_item
		""",
		project,
		as_dict=True,
	)
	return {r.boq_item: flt(r.amount) for r in rows if flt(r.amount)}


def get_baseline_cost(contract):
	"""Budget cost per BOQ line from the first approved (baseline) version of the contract's budget.

	The first version stays as the baseline after it is cancelled and amended; a draft is not a baseline.
	"""
	baseline = frappe.db.get_value(
		"BF Budget", {"contract": contract, "amended_from": ["is", "not set"], "docstatus": ["!=", 0]}, "name", order_by="creation asc"
	)
	if not baseline:
		return {}
	cost = {}
	for r in frappe.get_all("BF Budget Item", filters={"parent": baseline}, fields=["boq_item", "amount"]):
		cost[r.boq_item] = cost.get(r.boq_item, 0) + flt(r.amount)
	return cost
