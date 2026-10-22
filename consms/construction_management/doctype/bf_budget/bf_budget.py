# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

from types import SimpleNamespace

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from consms.construction_management.budget import get_expense_account
from consms.construction_management.ipc import build_lines, run_lines


BUYING_DOCTYPES = (
	"Material Request",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
)


class BFBudget(Document):
	def before_insert(self):
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
		if self.amended_from:
			self.relink_procurement()

	def before_cancel(self):
		# a budget is replaced by its revision, so buying documents that point at it stay valid
		self.ignore_linked_doctypes = BUYING_DOCTYPES

	def relink_procurement(self):
		"""Point buying documents of the previous version at this revision, line by line, and carry Requested Qty over."""
		from consms.material_request import update_budget_requested_qty

		new_rows = {(row.boq_item, row.item_code): row.name for row in self.items}
		old_rows = frappe.get_all("BF Budget Item", filters={"parent": self.amended_from}, fields=["name", "boq_item", "item_code"])
		mapping = {old.name: new_rows[(old.boq_item, old.item_code)] for old in old_rows if (old.boq_item, old.item_code) in new_rows}

		for doctype in BUYING_DOCTYPES:
			frappe.db.sql(
				f"update `tab{doctype}` set bf_budget = %s where bf_budget = %s", (self.name, self.amended_from)
			)
			for old, new in mapping.items():
				frappe.db.sql(
					f"update `tab{doctype} Item` set bf_budget = %s, bf_budget_item = %s where bf_budget_item = %s",
					(self.name, new, old),
				)

		update_budget_requested_qty(SimpleNamespace(items=[frappe._dict(bf_budget_item=new) for new in mapping.values()]))

	def validate_one_budget_per_contract(self):
		other = frappe.db.get_value(
			"BF Budget",
			{"contract": self.contract, "docstatus": ["!=", 2], "name": ["not in", [self.name or "", self.amended_from or ""]]},
		)
		if other:
			frappe.throw(_("Contract {0} already has Budget {1}. Amend it to make a revision.").format(self.contract, other))

	def onload(self):
		# the recipe picker and "create a new recipe" use each line's unit; mismatched lines are flagged
		self.set_onload("boq_units", self.get_boq_units())
		self.set_onload("unit_mismatches", self.get_unit_mismatches())

	def get_boq_units(self):
		"""{BOQ line: its ERP unit}."""
		items = [line.boq_item for line in self.boq_lines if line.boq_item]
		if not items:
			return {}
		return dict(frappe.get_all("BF BOQ Item", filters={"name": ["in", items]}, fields=["name", "erp_uom"], as_list=True))

	def get_unit_mismatches(self):
		"""Lines whose recipe is for a different unit than the BOQ line: their cost is multiplied by the wrong quantity."""
		units = self.get_boq_units()
		recipes = {line.rate_analysis for line in self.boq_lines if line.rate_analysis}
		recipe_units = dict(frappe.get_all("BF Rate Analysis", filters={"name": ["in", list(recipes)]}, fields=["name", "uom"], as_list=True)) if recipes else {}
		return [
			{"idx": line.idx, "description": line.description, "boq_unit": units.get(line.boq_item),
			 "rate_analysis": line.rate_analysis, "recipe_unit": recipe_units.get(line.rate_analysis)}
			for line in self.boq_lines
			if line.rate_analysis and units.get(line.boq_item) and recipe_units.get(line.rate_analysis) != units.get(line.boq_item)
		]

	def validate_rate_analyses(self):
		units = self.get_boq_units()
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
			boq_uom = units.get(line.boq_item)
			if boq_uom and ra.uom != boq_uom:
				frappe.throw(
					_("Row {0} ({1}): the BOQ line is in {2} but Rate Analysis {3} is per {4}. "
					  "A recipe gives the resources for 1 unit of the BOQ line, so its unit must be {2}.").format(
						line.idx, line.description, frappe.bold(boq_uom), line.rate_analysis, frappe.bold(ra.uom)
					),
					title=_("Recipe unit does not match the BOQ line"),
				)

	def build_boq_lines(self):
		"""One row per BOQ line, keeping recipes already chosen."""
		chosen = {line.boq_item: line.rate_analysis for line in self.boq_lines}
		applied = {line.boq_item: (line.applied_rate_analysis, flt(line.boq_qty)) for line in self.boq_lines}
		self.set("boq_lines", [])
		for item in frappe.get_doc("BF Bill of Quantities", self.boq).items:
			self.append(
				"boq_lines",
				{
					"boq_item": item.name,
					"description": item.description,
					"bill": item.bill,
					"rate_analysis": chosen.get(item.name),
					# a line whose quantity did not change keeps its resources (and any manual edits)
					"applied_rate_analysis": applied[item.name][0]
						if item.name in applied and applied[item.name][1] == flt(item.revised_qty or item.quantity) else None,
					"boq_qty": flt(item.revised_qty or item.quantity),
					"boq_unit": item.uom,
					"boq_amount": flt(item.revised_amount or item.amount),
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
		self.calculate_overheads()
		self.expected_margin = flt(self.contract_value) - (flt(self.total_with_overheads) or self.total_budget_cost)
		self.margin_percent = self.expected_margin / self.contract_value * 100 if self.contract_value else 0

	def calculate_overheads(self):
		"""Contingency, supervision fee, wear and tear... from the Budget Overheads template."""
		if not self.overhead_template:
			self.set("overhead_lines", [])
			self.total_with_overheads = self.total_budget_cost
			return
		if not self.overhead_lines or (not self.is_new() and self.has_value_changed("overhead_template")):
			build_lines(self, "overhead_lines", self.overhead_template)
		bases = {"Direct Cost": flt(self.total_budget_cost), "BOQ Value": flt(self.contract_value)}
		self.total_with_overheads, _roles = run_lines(self.overhead_lines, bases, contract_value=flt(self.contract_value))


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
def reprice_from_price_list(budget_name):
	"""Apply current buying prices to the quantity not yet requested; what is already requested keeps its old price."""
	from consms.construction_management.budget import get_item_buying_rate

	budget = frappe.get_doc("BF Budget", budget_name)
	if budget.docstatus != 0:
		frappe.throw(_("Only a draft budget can be re-priced. Cancel and Amend it to make a revision."))

	requested = {}
	if budget.amended_from:
		for old in frappe.get_all("BF Budget Item", filters={"parent": budget.amended_from}, fields=["boq_item", "item_code", "requested_qty"]):
			requested[(old.boq_item, old.item_code)] = flt(old.requested_qty)

	changed = []
	for row in budget.items:
		new_price = get_item_buying_rate(row.item_code, row.uom)
		if not new_price or flt(new_price) == flt(row.rate):
			continue
		done = min(requested.get((row.boq_item, row.item_code), 0), flt(row.qty))
		remaining = flt(row.qty) - done
		row.previous_rate = row.rate
		row.rate = (done * flt(row.rate) + remaining * new_price) / flt(row.qty) if flt(row.qty) else new_price
		changed.append(_("{0}: {1} -> {2} (for {3} not yet requested)").format(
			row.item_code, frappe.format(row.previous_rate, "Currency"), frappe.format(new_price, "Currency"), round(remaining, 2)))

	budget.save()
	return changed


@frappe.whitelist()
def get_items_for_material_request(source_name, target_doc=None):
	"""Get Items From > BF Budget: stock materials still left to request."""
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.bf_budget = source.name
		target.bf_boq = source.boq
		site_store = frappe.db.get_value("BF Contract", source.contract, "site_warehouse")
		if site_store:
			target.set_warehouse = site_store
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
					"warehouse": target.get("set_warehouse"),
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
