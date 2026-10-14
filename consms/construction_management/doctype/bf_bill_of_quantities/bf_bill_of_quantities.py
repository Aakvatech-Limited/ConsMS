# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from frappe.utils import add_days, flt, nowdate

from consms.construction_management.ipc import calculate_boq_summary
from consms.construction_management.uom import get_uom_map, normalize, resolve_uom

PROVISIONAL_SUM_UNITS = {"ps", "p.s", "p.s.", "provisional sum"}

class BFBillofQuantities(Document):
	def after_insert(self):
		# Tender -> BOQ: keep the tender pointing at its (latest) BOQ so the contract picks it up
		if self.tender:
			frappe.db.set_value("BF Tender", self.tender, "boq", self.name)

	def validate(self):
		self.validate_one_boq_per_tender()
		self.set_erp_uoms()
		total = 0
		for item in self.get("items"):
			item.amount = flt(item.quantity) * flt(item.unit_rate)
			total += item.amount
		self.set_provisional_sums()
		self.total_amount = total
		if self.is_new() and not self.summary_template:
			self.summary_template = frappe.db.get_single_value("BF Construction Settings", "default_boq_summary_template")
		calculate_boq_summary(self)

	def before_update_after_submit(self):
		self.set_provisional_sums()
		calculate_boq_summary(self)

	def set_provisional_sums(self):
		for item in self.items:
			if normalize(item.uom) in PROVISIONAL_SUM_UNITS:
				item.is_provisional_sum = 1

	def before_submit(self):
		unmapped = sorted({row.uom or _("(blank)") for row in self.items if not row.erp_uom})
		if unmapped:
			frappe.throw(
				_("Map these BOQ units to an ERP UOM before submitting (UOM Mapping list): {0}").format(
					", ".join(frappe.bold(u) for u in unmapped)
				),
				title=_("Unmapped BOQ Units"),
			)

	def set_erp_uoms(self):
		uom_map = get_uom_map()
		for row in self.items:
			if row.uom and not row.erp_uom:
				row.erp_uom = resolve_uom(row.uom, uom_map)

	def validate_one_boq_per_tender(self):
		if not self.tender:
			return
		other = frappe.db.get_value(
			"BF Bill of Quantities",
			{"tender": self.tender, "docstatus": ["!=", 2], "name": ["not in", [self.name, self.amended_from or ""]]},
		)
		if other:
			frappe.throw(_("Tender {0} already has Bill of Quantities {1}.").format(self.tender, other))

@frappe.whitelist()
def get_awarded_tender(boq_name):
	tender = frappe.db.get_value("BF Tender", {"boq": boq_name, "docstatus": 1, "status": "Awarded"}, "name")
	if not tender:
		return None
	contract = frappe.db.get_value("BF Contract", {"tender": tender, "docstatus": ["!=", 2]}, "name")
	return {"tender": tender, "contract": contract}

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_items_query(doctype, txt, searchfield, start, page_len, filters):
	filters = filters or {}
	boq_name = filters.get("parent")
	
	conditions = []
	params = []

	if not boq_name:
		return []

	conditions = ["parent = %s"]
	params = [boq_name]

	if txt:
		search_txt = f"%{txt}%"
		conditions.append("(name LIKE %s OR IFNULL(description, '') LIKE %s)")
		params.extend([search_txt, search_txt])

	where_stmt = ("WHERE " + " AND ".join(conditions)) if conditions else ""

	query = f"""
		SELECT 
			name,
			CONCAT(
				IFNULL(description, ''), 
				IF(IFNULL(uom, '') != '', CONCAT(' | UOM: ', uom), ''),
				IF(IFNULL(quantity, 0) > 0, CONCAT(' | Qty: ', quantity), '')
			) AS title
		FROM `tabBF BOQ Item`
		{where_stmt}
		ORDER BY idx ASC
		LIMIT %s, %s
	"""
	params.extend([start, page_len])
	return frappe.db.sql(query, params)


@frappe.whitelist()
def set_vat_exempt_bills(boq, bills):
	"""Mark the lines of the given bills VAT exempt (and the others not), also on a submitted BOQ."""
	doc = frappe.get_doc("BF Bill of Quantities", boq)
	doc.check_permission("write")
	bills = set(frappe.parse_json(bills) if isinstance(bills, str) else bills or [])
	for row in doc.items:
		exempt = 1 if (row.bill or "") in bills else 0
		if row.vat_exempt != exempt:
			row.db_set("vat_exempt", exempt)
	return len([row for row in doc.items if row.vat_exempt])
