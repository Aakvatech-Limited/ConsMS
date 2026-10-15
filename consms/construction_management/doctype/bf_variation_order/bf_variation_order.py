# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from consms.construction_management.ipc import money
from consms.construction_management.variations import (
	apply_variation,
	get_budget_rate_analysis,
	measured_to_date,
)


class BFVariationOrder(Document):
	def validate(self):
		if self.contract and not self.boq:
			self.boq = frappe.db.get_value("BF Contract", self.contract, "boq")
		self.set_lines()

	def set_lines(self):
		"""BOQ-line changes take the BOQ line's unit and rate; amounts, new quantities and the cost impact."""
		measured = measured_to_date(self.contract, [l.boq_item for l in self.items if l.boq_item and l.change_type == "Change to BOQ Line"])
		total = lump_sum = cost = 0.0
		for line in self.items:
			if not flt(line.quantity):
				frappe.throw(_("Row {0}: enter the quantity (+ extra, - less).").format(line.idx))
			if line.change_type == "Change to BOQ Line":
				if not line.boq_item:
					frappe.throw(_("Row {0}: choose the BOQ line that changes.").format(line.idx))
				row = frappe.db.get_value("BF BOQ Item", line.boq_item,
					["parent", "item_no", "description", "uom", "unit_rate", "revised_qty"], as_dict=True)
				if not row or (self.boq and row.parent != self.boq):
					frappe.throw(_("Row {0}: the BOQ line is not from this contract's BOQ.").format(line.idx))
				line.item_no, line.description, line.uom, line.unit_rate = row.item_no, row.description, row.uom, row.unit_rate
				line.current_qty = flt(row.revised_qty)
				line.new_qty = line.current_qty + flt(line.quantity)
				if self.docstatus == 0 and line.new_qty < measured.get(line.boq_item, 0) - 1e-9:
					frappe.throw(_("Row {0}: {1} is already measured; the revised quantity cannot go below it.").format(
						line.idx, measured.get(line.boq_item, 0)))
				if not line.rate_analysis:
					line.rate_analysis = get_budget_rate_analysis(self.contract, line.boq_item)
			else:
				if not (line.description and line.uom):
					frappe.throw(_("Row {0}: enter the description and unit of the new item.").format(line.idx))
				if line.change_type == "New Item":
					line.bill = line.bill or _("Additional Works")
					if flt(line.quantity) < 0:
						frappe.throw(_("Row {0}: a new item needs a positive quantity.").format(line.idx))
			line.amount = money(flt(line.quantity) * flt(line.unit_rate))
			line.cost_impact = money(
				flt(line.quantity) * flt(frappe.db.get_value("BF Rate Analysis", line.rate_analysis, "cost_per_unit"))
			) if line.rate_analysis else 0
			total += line.amount
			cost += line.cost_impact
			if line.change_type == "Lump Sum":
				lump_sum += line.amount
		self.requested_amount = money(total)
		self.lump_sum_amount = money(lump_sum)
		self.cost_impact = money(cost)
		self.variation_margin = money(total - cost) if cost else 0

	def before_submit(self):
		missing = [label for field, label in (("client_instruction_no", _("Client Instruction No.")),
			("approval_date", _("Approval Date")), ("approval_letter", _("Approval Letter"))) if not self.get(field)]
		if missing:
			frappe.throw(_("Submitting means the client approved this variation. Enter: {0}").format(", ".join(missing)),
				title=_("Client approval missing"))

	def on_submit(self):
		apply_variation(self, 1)

	def on_cancel(self):
		apply_variation(self, -1)
