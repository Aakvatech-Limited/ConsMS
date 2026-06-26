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
