"""BOQ units as written by clients (m³, Nr, Ls...) mapped to ERPNext UOMs."""

import frappe

EXTRA_UOMS = ["Lump Sum", "Bag"]

STANDARD_MAPPINGS = {
	"Meter": ["m", "lm", "metre", "meter", "rm", "linear meter", "linear metre", "lin m"],
	"Square Meter": ["m2", "m²", "sqm", "sq.m", "sq m"],
	"Cubic Meter": ["m3", "m³", "cum", "cu.m", "cu m"],
	"Kg": ["kg", "kgs", "kilogram", "kilograms"],
	"Tonne": ["t", "ton", "tons", "tonne"],
	"Nos": ["nr", "no", "no.", "nos", "pcs", "pc", "each", "ea", "number", "numbers"],
	"Lump Sum": ["ls", "l.s", "l.s.", "sum", "lump sum", "lumpsum", "item", "ps", "provisional sum"],
	"Percent": ["%", "percent"],
	"Litre": ["l", "ltr", "litre", "liter", "lts"],
	"Day": ["day", "days"],
	"Hour": ["hr", "hrs", "hour", "hours"],
	"Bag": ["bag", "bags"],
}


def normalize(unit):
	return " ".join((unit or "").split()).lower()


def ensure_standard_uom_mappings():
	for uom in EXTRA_UOMS:
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)

	for uom, units in STANDARD_MAPPINGS.items():
		if not frappe.db.exists("UOM", uom):
			continue
		for unit in units:
			# the database treats e.g. "m2" and "m²" as the same name, so one mapping covers both
			if not frappe.db.exists("BF UOM Mapping", unit):
				frappe.get_doc({"doctype": "BF UOM Mapping", "boq_unit": unit, "uom": uom}).insert(ignore_permissions=True)


def get_uom_map():
	return {normalize(m.boq_unit): m.uom for m in frappe.get_all("BF UOM Mapping", fields=["boq_unit", "uom"])}


def resolve_uom(unit, uom_map=None):
	"""ERP UOM for a BOQ unit: from the mapping, or the unit itself if it is already an ERP UOM."""
	if not unit:
		return None
	uom_map = uom_map if uom_map is not None else get_uom_map()
	unit = unit.strip()
	return (
		uom_map.get(normalize(unit))
		# the database matches e.g. "m²" to the "m2" mapping
		or frappe.db.get_value("BF UOM Mapping", unit, "uom")
		or frappe.db.get_value("UOM", unit)
	)


@frappe.whitelist()
def get_erp_uom(unit):
	return resolve_uom(unit)
