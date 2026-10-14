# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

"""Total of each resource (cement, sand, steel...) over the whole budget, optionally per bill / structure:
what to order for the project, with what has been requested and received so far."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 170},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 80},
		{"label": _("Budget Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 110},
		{"label": _("Budget Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
		{"label": _("Requested Qty"), "fieldname": "requested_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Still to Request"), "fieldname": "to_request", "fieldtype": "Float", "width": 120},
	]
	if filters.by_bill:
		columns.insert(0, {"label": _("Bill / Structure"), "fieldname": "bill", "fieldtype": "Data", "width": 220})

	conditions = "and bi.resource_type = %(resource_type)s" if filters.resource_type else ""
	group = "boq.bill, bi.item_code" if filters.by_bill else "bi.item_code"
	rows = frappe.db.sql(
		f"""
		select {"coalesce(boq.bill, '') as bill," if filters.by_bill else ""}
			bi.item_code, max(bi.item_name) as item_name, max(bi.uom) as uom,
			sum(bi.qty) as qty, sum(bi.amount) as amount, sum(bi.requested_qty) as requested_qty,
			group_concat(bi.name) as budget_items
		from `tabBF Budget Item` bi
		left join `tabBF BOQ Item` boq on boq.name = bi.boq_item
		where bi.parent = %(budget)s {conditions}
		group by {group}
		order by {"bill, " if filters.by_bill else ""}amount desc
		""",
		filters,
		as_dict=True,
	)
	for row in rows:
		row.received_qty = flt(frappe.db.sql(
			"""select sum(pri.stock_qty) from `tabPurchase Receipt Item` pri
			join `tabPurchase Receipt` pr on pr.name = pri.parent
			where pr.docstatus = 1 and pri.bf_budget_item in %(items)s""",
			{"items": (row.pop("budget_items") or "").split(",")},
		)[0][0])
		row.to_request = max(flt(row.qty) - flt(row.requested_qty), 0)
	return columns, rows
