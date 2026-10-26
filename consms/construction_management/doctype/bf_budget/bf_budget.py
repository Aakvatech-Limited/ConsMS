# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import json
import re
from types import SimpleNamespace

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from consms.construction_management.budget import get_expense_account
from consms.construction_management.ipc import build_lines, run_lines


# a recipe's resources fill the line's four amounts
AMOUNT_FIELD = {"Material": "materials_amount", "Labour": "labour_amount", "Plant": "plant_amount"}
AMOUNT_FIELDS = ("materials_amount", "labour_amount", "plant_amount", "other_amount")

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
		"""One row per BOQ line in bill order, keeping recipes and amounts already typed."""
		previous = {line.boq_item: line for line in self.boq_lines}
		self.set("boq_lines", [])
		items = sorted(frappe.get_doc("BF Bill of Quantities", self.boq).items, key=lambda item: line_order(item.bill, item.item_no, item.idx))
		for item in items:
			old = previous.get(item.name)
			qty = flt(item.revised_qty or item.quantity)
			self.append(
				"boq_lines",
				{
					"boq_item": item.name,
					"item_no": item.item_no,
					"description": item.description,
					"bill": item.bill,
					"rate_analysis": old.rate_analysis if old else None,
					# a line whose quantity did not change keeps its resources (and any manual edits)
					"applied_rate_analysis": old.applied_rate_analysis if old and flt(old.boq_qty) == qty else None,
					"boq_qty": qty,
					"boq_unit": item.uom,
					"boq_rate": flt(item.unit_rate),
					"boq_amount": flt(item.revised_amount or item.amount),
					**{field: old.get(field) for field in AMOUNT_FIELDS if old},
				},
			)

	def apply_rate_analyses(self, rebuild_all=False):
		"""Rebuild resources only for BOQ lines whose recipe changed, so manual edits elsewhere are kept."""
		company = frappe.db.get_value("Project", self.project, "company")
		changed = [line for line in self.boq_lines if rebuild_all or line.rate_analysis != line.applied_rate_analysis]
		changed_items = {line.boq_item for line in changed}
		self.set("items", [row for row in self.items if row.boq_item not in changed_items])
		for line in changed:
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
							"description": res.description or res.item_name,
							"qty": flt(line.boq_qty) * flt(res.qty) * (1 + flt(res.wastage_percent) / 100),
							"uom": res.uom,
							"rate": res.rate,
							"expense_account": get_expense_account(res.item_code, company) if res.item_code
								else frappe.get_cached_value("Company", company, "default_expense_account"),
						},
					)
			line.applied_rate_analysis = line.rate_analysis

	def calculate_totals(self):
		"""Each line's budget is its four amounts: typed, or added up from its recipe's resources."""
		from_recipe = {}
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate)
			amounts = from_recipe.setdefault(row.boq_item, dict.fromkeys(AMOUNT_FIELDS, 0))
			amounts[AMOUNT_FIELD.get(row.resource_type, "other_amount")] += row.amount

		for line in self.boq_lines:
			if line.rate_analysis:
				line.update(from_recipe.get(line.boq_item) or dict.fromkeys(AMOUNT_FIELDS, 0))
			line.budget_cost = sum(flt(line.get(field)) for field in AMOUNT_FIELDS)
			line.budget_rate = line.budget_cost / flt(line.boq_qty) if flt(line.boq_qty) else 0
			line.margin = flt(line.boq_amount) - line.budget_cost
			line.margin_percent = line.margin / flt(line.boq_amount) * 100 if flt(line.boq_amount) else 0

		self.contract_value = sum(flt(line.boq_amount) for line in self.boq_lines)
		self.total_budget_cost = sum(flt(line.budget_cost) for line in self.boq_lines)
		self.missing_rate_analysis = "\n".join(line.description or "" for line in self.boq_lines if not flt(line.budget_cost))
		self.calculate_overheads()
		if flt(self.unplanned_percent):
			self.unplanned_amount = flt(self.total_budget_cost) * flt(self.unplanned_percent) / 100
		self.expected_margin = (flt(self.contract_value) - (flt(self.total_with_overheads) or self.total_budget_cost)
			- flt(self.unplanned_amount))
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
	budget.missing_rate_analysis = "\n".join(line.description or "" for line in budget.boq_lines)
	return budget


def line_order(bill, item_no, idx):
	"""BOQ lines in bill order: Bill No. 2 before Bill No. 10, then by Item No. (1.1.2 before 1.2.1)."""
	number = re.search(r"\d+", bill or "")
	return (int(number.group()) if number else 10**6, [int(n) for n in re.findall(r"\d+", item_no or "")], idx or 0)


@frappe.whitelist(methods=["POST"])
def make_recipe(budget_name, line_name, recipe_name, per_unit=0, materials=None, labour=0, plant=0, other=0):
	"""A recipe made from a budget line, in the line's unit, then used on the line.

	Quantities and amounts can be for the whole line (as in a costing sheet) or for 1 unit; the
	recipe always stores them per 1 unit, so it can be reused on other lines.
	"""
	budget = frappe.get_doc("BF Budget", budget_name)
	budget.check_permission("write")
	if budget.docstatus != 0:
		frappe.throw(_("Recipes can only be added to a draft budget."))
	line = next((row for row in budget.boq_lines if row.name == line_name), None)
	if not line:
		frappe.throw(_("The BOQ line was not found on this budget. Save the budget and try again."))

	unit = frappe.db.get_value("BF BOQ Item", line.boq_item, "erp_uom")
	if not unit:
		frappe.throw(_("BOQ line {0} has no ERP unit. Set it on the Bill of Quantities first.").format(line.item_no or line.description))
	divide_by = 1 if frappe.utils.cint(per_unit) else flt(line.boq_qty)
	if divide_by <= 0:
		frappe.throw(_("The BOQ line has no quantity, so the whole-line amounts cannot be turned into a rate."))

	recipe = frappe.get_doc({"doctype": "BF Rate Analysis", "rate_analysis_name": recipe_name, "uom": unit,
		"description": _("Made from budget {0}, BOQ line {1}.").format(budget.name, line.item_no or line.description)})
	for row in json.loads(materials) if isinstance(materials, str) else (materials or []):
		row = frappe._dict(row)
		if row.item_code and flt(row.qty):
			recipe.append("items", {"resource_type": "Material", "item_code": row.item_code, "qty": flt(row.qty) / divide_by,
				"rate": flt(row.rate), "wastage_percent": flt(row.wastage_percent)})
	for resource_type, label, amount in (("Labour", _("Labour"), labour), ("Plant", _("Machines"), plant), ("Other", _("Other costs"), other)):
		if flt(amount):
			recipe.append("items", {"resource_type": resource_type, "description": label, "qty": 1, "rate": flt(amount) / divide_by})
	if not recipe.items:
		frappe.throw(_("Add at least one material or amount."))
	recipe.insert()
	recipe.submit()

	line.rate_analysis = recipe.name
	budget.save()
	return recipe.name


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
		if not row.item_code:
			continue
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
