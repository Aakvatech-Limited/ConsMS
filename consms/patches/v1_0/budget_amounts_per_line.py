"""Budgets show four amounts per BOQ line (materials, labour, machines, other).

Existing lines were all costed by recipe: fill their amounts from their resources, with the line's
Item No., bill, BOQ rate and budget rate, and put the lines in bill order. Line budgets do not change.
"""

import frappe
from frappe.utils import flt

from consms.construction_management.doctype.bf_budget.bf_budget import line_order

FIELDS = ("idx", "item_no", "bill", "boq_rate", "materials_amount", "labour_amount", "plant_amount", "other_amount", "budget_rate")


def execute():
	for name in frappe.get_all("BF Budget", pluck="name"):
		budget = frappe.get_doc("BF Budget", name)
		boq = {
			item.name: item
			for item in frappe.get_all("BF BOQ Item", filters={"parent": budget.boq}, fields=["name", "idx", "item_no", "bill", "unit_rate"])
		}
		for line in budget.boq_lines:
			item = boq.get(line.boq_item)
			line.item_no = item.item_no if item else None
			line.bill = item.bill if item else line.bill
			line.boq_rate = flt(item.unit_rate) if item else 0
		budget.boq_lines.sort(key=lambda line: line_order(line.bill, line.item_no, boq[line.boq_item].idx if line.boq_item in boq else 0))
		for idx, line in enumerate(budget.boq_lines, 1):
			line.idx = idx
		budget.calculate_totals()
		for line in budget.boq_lines:
			frappe.db.set_value("BF Budget BOQ Line", line.name, {f: line.get(f) for f in FIELDS}, update_modified=False)
