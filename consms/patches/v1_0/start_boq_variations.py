"""BOQ lines get Original / Variation / Revised quantities; old Variation Orders become lump sums.

Old Variation Orders listed ERPNext items with an amount and were claimed in full, so they
stay lump sums (claimed by amount); new ones change BOQ quantities and are paid by measurement.
"""

import frappe

from consms.construction_management.variations import update_contract_variations


def execute():
	frappe.db.sql(
		"""update `tabBF BOQ Item`
		set original_qty = quantity, variation_qty = 0, revised_qty = quantity, revised_amount = amount
		where ifnull(variation_order, '') = '' and ifnull(original_qty, 0) = 0 and ifnull(revised_qty, 0) = 0"""
	)
	frappe.db.sql("update `tabBF Bill of Quantities` set revised_total = total_amount, variations_total = 0 where ifnull(revised_total, 0) = 0")

	frappe.db.sql("update `tabBF Variation Item` set change_type = 'Lump Sum' where ifnull(change_type, '') in ('', 'Change to BOQ Line') and ifnull(boq_item, '') = ''")
	for vo in frappe.get_all("BF Variation Order", fields=["name", "contract", "requested_amount"]):
		frappe.db.set_value("BF Variation Order", vo.name, {
			"lump_sum_amount": vo.requested_amount,
			"boq": frappe.db.get_value("BF Contract", vo.contract, "boq") if vo.contract else None,
		}, update_modified=False)

	for contract in frappe.get_all("BF Contract", filters={"docstatus": 1}, pluck="name"):
		update_contract_variations(contract)
