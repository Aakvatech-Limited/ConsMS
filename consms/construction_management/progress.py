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
	"""Actual cost per BOQ line from submitted Site Daily Reports (labour, machines, materials)."""
	cost = {}
	for table in ("BF Daily Labour", "BF Daily Plant", "BF Daily Material"):
		rows = frappe.db.sql(
			f"""
			select t.boq_item, sum(t.amount) as amount
			from `tab{table}` t
			join `tabBF Site Daily Report` r on r.name = t.parent
			where r.contract = %s and r.docstatus = 1
			group by t.boq_item
			""",
			contract,
			as_dict=True,
		)
		for r in rows:
			cost[r.boq_item] = cost.get(r.boq_item, 0) + flt(r.amount)
	return cost
