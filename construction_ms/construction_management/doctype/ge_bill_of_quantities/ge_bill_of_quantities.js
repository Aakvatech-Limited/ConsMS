// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Bill of Quantities", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Material Request"), function() {
				frappe.model.open_mapped_doc({
					method: "construction_ms.construction_management.doctype.ge_bill_of_quantities.ge_bill_of_quantities.make_material_request",
					frm: frm
				});
			}, __("Create"));
		}
	},
});

frappe.ui.form.on("GE BOQ Item", {
	quantity: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	unit_rate: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	}
});

function calculate_amount(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let amt = flt(row.quantity) * flt(row.unit_rate);
	frappe.model.set_value(cdt, cdn, "amount", amt);
}
