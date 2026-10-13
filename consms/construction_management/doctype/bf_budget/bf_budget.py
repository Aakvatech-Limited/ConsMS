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
		self.validate_rate_analyses()
		self.apply_rate_analyses()
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

	def validate_rate_analyses(self):
		for line in self.boq_lines:
			if not line.rate_analysis or line.rate_analysis == line.applied_rate_analysis:
				continue
			ra = frappe.db.get_value("BF Rate Analysis", line.rate_analysis, ["docstatus", "uom"], as_dict=True)
			if ra.docstatus != 1:
				frappe.throw(
					_("Row {0}: Rate Analysis {1} is not approved. Only submitted Rate Analyses can be used.").format(
						line.idx, frappe.bold(line.rate_analysis)
					)
				)
			boq_uom = frappe.db.get_value("BF BOQ Item", line.boq_item, "erp_uom")
			if boq_uom and ra.uom != boq_uom:
				frappe.msgprint(
					_("Row {0} ({1}): the BOQ line is in {2} but Rate Analysis {3} is per {4}. Check the quantities.").format(
						line.idx, line.description, frappe.bold(boq_uom), line.rate_analysis, frappe.bold(ra.uom)
					),
					title=_("Unit mismatch"),
					indicator="orange",
				)

	def build_boq_lines(self):
		"""One row per BOQ line, keeping recipes already chosen."""
		chosen = {line.boq_item: line.rate_analysis for line in self.boq_lines}
		self.set("boq_lines", [])
		for item in frappe.get_doc("BF Bill of Quantities", self.boq).items:
			self.append(
				"boq_lines",
				{
					"boq_item": item.name,
					"description": item.description,
					"rate_analysis": chosen.get(item.name),
					"boq_qty": item.quantity,
					"boq_unit": item.uom,
					"boq_amount": item.amount,
				},
			)

	def apply_rate_analyses(self, rebuild_all=False):
		"""Rebuild resources only for BOQ lines whose recipe changed, so manual edits elsewhere are kept."""
		company = frappe.db.get_value("Project", self.project, "company")
		for line in self.boq_lines:
			if not rebuild_all and line.rate_analysis == line.applied_rate_analysis:
				continue
			self.set("items", [row for row in self.items if row.boq_item != line.boq_item])
			if line.rate_analysis:
				for res in frappe.get_doc("BF Rate Analysis", line.rate_analysis).items:
					self.append(
						"items",
						{
							"boq_item": line.boq_item,
							"boq_description": line.description,
							"rate_analysis": line.rate_analysis,
							"resource_type": res.resource_type,
							"item_code": res.item_code,
							"qty": flt(line.boq_qty) * flt(res.qty) * (1 + flt(res.wastage_percent) / 100),
							"uom": res.uom,
							"rate": res.rate,
							"expense_account": get_expense_account(res.item_code, company),
						},
					)
			line.applied_rate_analysis = line.rate_analysis
		self.missing_rate_analysis = "\n".join(line.description for line in self.boq_lines if not line.rate_analysis)

	def calculate_totals(self):
		cost_per_line = {}
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate)
			cost_per_line[row.boq_item] = cost_per_line.get(row.boq_item, 0) + row.amount

		for line in self.boq_lines:
			line.budget_cost = cost_per_line.get(line.boq_item, 0)
			line.margin = flt(line.boq_amount) - line.budget_cost
			line.margin_percent = line.margin / flt(line.boq_amount) * 100 if flt(line.boq_amount) else 0

		self.contract_value = sum(flt(line.boq_amount) for line in self.boq_lines)
		self.total_budget_cost = sum(cost_per_line.values())
		self.expected_margin = flt(self.contract_value) - self.total_budget_cost
		self.margin_percent = self.expected_margin / self.contract_value * 100 if self.contract_value else 0


@frappe.whitelist()
def make_bf_budget(source_name, target_doc=None):
	"""Contract -> Budget with one row per BOQ line; the QS then picks a Rate Analysis per line."""
	existing = frappe.db.get_value("BF Budget", {"contract": source_name, "docstatus": ["!=", 2]})
	if existing:
		frappe.throw(_("This contract already has Budget {0}.").format(existing))

	contract = frappe.get_doc("BF Contract", source_name)
	if not contract.boq:
		frappe.throw(_("The contract has no Bill of Quantities."))

	budget = frappe.new_doc("BF Budget")
	budget.update({"contract": contract.name, "project": contract.project, "boq": contract.boq})
	budget.build_boq_lines()
	budget.missing_rate_analysis = "\n".join(line.description for line in budget.boq_lines)
	return budget


@frappe.whitelist()
def rebuild_resources(budget_name):
	"""Re-read the BOQ lines and rebuild all resources from the chosen Rate Analyses (draft only)."""
	budget = frappe.get_doc("BF Budget", budget_name)
	if budget.docstatus != 0:
		frappe.throw(_("Only a draft budget can be rebuilt. Cancel and Amend it to make a revision."))
	budget.build_boq_lines()
	budget.apply_rate_analyses(rebuild_all=True)
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
