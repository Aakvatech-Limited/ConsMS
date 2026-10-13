"""Site measurement: quantity formulas per Construction Type, and Task progress.

Another app can add its own formula in hooks.py:

	consms_measurement_methods = {
		"Bridge Deck": "my_app.measurement.bridge_deck_quantity",
	}

The function receives the measurement row and the BF Construction Type and
returns the quantity. Select it on a Construction Type with method "Custom".
"""

import frappe
from frappe import _
from frappe.utils import flt

DEFAULT_METHOD = "Dimensions"

STANDARD_CONSTRUCTION_TYPES = [
	{
		"construction_type": "Building",
		"measurement_method": "Dimensions",
		"location_label": "Floor / Grid",
		"description": "Buildings and houses: No. x Length x Width x Height.",
	},
	{
		"construction_type": "Bridge",
		"measurement_method": "Dimensions",
		"location_label": "Span / Pier",
		"description": "Bridges and culverts (piers, abutments, decks): No. x Length x Width x Height.",
	},
	{
		"construction_type": "Road",
		"measurement_method": "Chainage",
		"location_label": "Section",
		"label_multiplier": "Layers",
		"label_width": "Width (m)",
		"label_height": "Thickness (m)",
		"description": "Roads: Layers x (Chainage To - From) x Width x Thickness.",
	},
	{
		"construction_type": "Pipeline",
		"measurement_method": "Chainage",
		"location_label": "Line / Section",
		"label_multiplier": "No. of Lines",
		"label_width": "",
		"label_height": "",
		"description": "Pipelines and cables: No. of lines x (Chainage To - From).",
	},
	{
		"construction_type": "Lump Sum",
		"measurement_method": "Percent Complete",
		"location_label": "Location",
		"label_multiplier": "",
		"label_width": "",
		"label_height": "",
		"description": "Lump-sum work: % complete x BOQ quantity.",
	},
]


def ensure_standard_construction_types():
	for values in STANDARD_CONSTRUCTION_TYPES:
		if not frappe.db.exists("BF Construction Type", values["construction_type"]):
			frappe.get_doc({"doctype": "BF Construction Type", **values}).insert(ignore_permissions=True)


def product_of_filled(*values):
	"""Multiply the values that were entered; empty boxes are skipped."""
	filled = [flt(v) for v in values if flt(v)]
	result = 1.0
	for value in filled:
		result *= value
	return result if filled else 0.0


def calculate_quantity(row, construction_type=None):
	method = construction_type.measurement_method if construction_type else DEFAULT_METHOD
	count = flt(row.multiplier) or 1

	if method == "Dimensions":
		dimensions = product_of_filled(row.length, row.width, row.height)
		return count * dimensions if dimensions else count

	if method == "Chainage":
		length = abs(flt(row.chainage_to) - flt(row.chainage_from))
		return count * length * (product_of_filled(row.width, row.height) or 1)

	if method == "Percent Complete":
		boq_qty = flt(frappe.db.get_value("BF BOQ Item", row.boq_item, "quantity")) if row.boq_item else 0
		return flt(row.percent_complete) / 100 * boq_qty

	if method == "Custom":
		paths = frappe.get_hooks("consms_measurement_methods").get(construction_type.custom_method)
		if not paths:
			frappe.throw(_("Measurement method {0} is not available.").format(construction_type.custom_method))
		return flt(frappe.get_attr(paths[-1])(row, construction_type))

	return count


def update_task_progress(tasks):
	"""Task progress % = value measured so far / value of its BOQ lines (quantity x rate)."""
	for task in {t for t in tasks if t}:
		boq_value = flt(
			frappe.db.sql(
				"""
				select sum(item.quantity * item.unit_rate)
				from `tabBF BOQ Item` item
				join `tabBF Bill of Quantities` boq on boq.name = item.parent
				where item.task = %s and boq.docstatus = 1
				""",
				task,
			)[0][0]
		)
		if not boq_value:
			continue

		measured_value = flt(
			frappe.db.sql(
				"""
				select sum(mi.total_quantity * boq_item.unit_rate)
				from `tabBF Measurement Item` mi
				join `tabBF Site Measurement Log` log on log.name = mi.parent
				join `tabBF BOQ Item` boq_item on boq_item.name = mi.boq_item
				where mi.task = %s and log.docstatus = 1
				""",
				task,
			)[0][0]
		)
		progress = min(100.0, measured_value / boq_value * 100)
		frappe.db.set_value("Task", task, "progress", progress)
