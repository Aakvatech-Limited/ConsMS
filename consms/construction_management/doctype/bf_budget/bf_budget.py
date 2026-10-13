# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from consms.construction_management.budget import cancel_erp_budget, get_expense_account, sync_erp_budget


class BFBudget(Document):
	def before_insert(self):
		# a revision gets its own ERPNext Budget on submit
		self.erp_budget = None
		for row in self.items:
			row.requested_qty = 0

	def validate(self):
		if self.amended_from and not (self.revision_reason or "").strip():
			frappe.throw(_("Enter the Revision Reason: why this budget is being revised."))
		self.validate_one_budget_per_contract()
		self.calculate_totals()

	def on_submit(self):
		sync_erp_budget(self)

	def on_cancel(self):
		cancel_erp_budget(self)

	def validate_one_budget_per_contract(self):
		other = frappe.db.get_value(
			"BF Budget",
			{"contract": self.contract, "docstatus": ["!=", 2], "name": ["not in", [self.name or "", self.amended_from or ""]]},
		)
		if other:
			frappe.throw(_("Contract {0} already has Budget {1}. Amend it to make a revision.").format(self.contract, other))

	def populate_from_boq(self):
		"""Budget resources = each BOQ line's quantity x its Rate Analysis recipe."""
		company = frappe.db.get_value("Project", self.project, "company")
		self.set("items", [])
		missing = []
		for line in frappe.get_doc("BF Bill of Quantities", self.boq).items:
			if not line.rate_analysis:
				missing.append(line.description)
				continue
			for res in frappe.get_doc("BF Rate Analysis", line.rate_analysis).items:
				self.append(
					"items",
					{
						"boq_item": line.name,
						"boq_description": line.description,
						"rate_analysis": line.rate_analysis,
						"resource_type": res.resource_type,
						"item_code": res.item_code,
						"qty": flt(line.quantity) * flt(res.qty) * (1 + flt(res.wastage_percent) / 100),
						"uom": res.uom,
						"rate": res.rate,
						"expense_account": get_expense_account(res.item_code, company),
					},
				)
		self.missing_rate_analysis = "\n".join(missing)

	def calculate_totals(self):
		cost_per_line = {}
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate)
			cost_per_line[row.boq_item] = cost_per_line.get(row.boq_item, 0) + row.amount

		self.set("boq_lines", [])
		self.contract_value = 0
		for line in frappe.get_doc("BF Bill of Quantities", self.boq).items if self.boq else []:
			boq_amount = flt(line.amount)
			cost = cost_per_line.get(line.name, 0)
			self.contract_value += boq_amount
			self.append(
				"boq_lines",
				{
					"boq_item": line.name,
					"description": line.description,
					"rate_analysis": line.rate_analysis,
					"boq_qty": line.quantity,
					"boq_unit": line.uom,
					"boq_amount": boq_amount,
					"budget_cost": cost,
					"margin": boq_amount - cost,
					"margin_percent": (boq_amount - cost) / boq_amount * 100 if boq_amount else 0,
				},
			)
		self.total_budget_cost = sum(cost_per_line.values())
		self.expected_margin = flt(self.contract_value) - self.total_budget_cost
		self.margin_percent = self.expected_margin / self.contract_value * 100 if self.contract_value else 0


@frappe.whitelist()
def make_bf_budget(source_name, target_doc=None):
	"""Contract -> Budget, filled from the contract's BOQ and the Rate Analysis on each BOQ line."""
	existing = frappe.db.get_value("BF Budget", {"contract": source_name, "docstatus": ["!=", 2]})
	if existing:
		frappe.throw(_("This contract already has Budget {0}.").format(existing))

	contract = frappe.get_doc("BF Contract", source_name)
	if not contract.boq:
		frappe.throw(_("The contract has no Bill of Quantities."))

	budget = frappe.new_doc("BF Budget")
	budget.update({"contract": contract.name, "project": contract.project, "boq": contract.boq})
	budget.populate_from_boq()
	budget.calculate_totals()
	return budget


@frappe.whitelist()
def refresh_from_boq(budget_name):
	budget = frappe.get_doc("BF Budget", budget_name)
	if budget.docstatus != 0:
		frappe.throw(_("Only a draft budget can be refreshed. Amend it to make a revision."))
	budget.populate_from_boq()
	budget.save()
	return budget.name


@frappe.whitelist()
def get_items_for_material_request(source_name, target_doc=None):
	"""Get Items From > BF Budget: stock materials still left to request."""
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.bf_budget = source.name
		target.bf_boq = source.boq
		target.schedule_date = target.schedule_date or nowdate()
		already_added = {row.bf_budget_item for row in target.get("items") if row.get("bf_budget_item")}
		for row in source.items:
			if row.name in already_added or row.resource_type != "Material":
				continue
			if not frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
				continue
			remaining = flt(row.qty) - flt(row.requested_qty)
			if remaining <= 0:
				continue
			target.append(
				"items",
				{
					"item_code": row.item_code,
					"qty": remaining,
					"uom": row.uom,
					"schedule_date": target.schedule_date,
					"project": source.project,
					"bf_budget": source.name,
					"bf_budget_item": row.name,
					"bf_boq": source.boq,
					"bf_boq_item": row.boq_item,
				},
			)

	doc = get_mapped_doc("BF Budget", source_name, {"BF Budget": {"doctype": "Material Request"}}, target_doc, set_missing_values)
	doc.material_request_type = "Purchase"
	doc.run_method("set_missing_values")
	return doc
