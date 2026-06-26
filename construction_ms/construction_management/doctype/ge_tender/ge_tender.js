// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Tender", {
	refresh(frm) {
		// Only allow creating a Contract if the Tender is officially Awarded!
		if (frm.doc.docstatus === 1 && frm.doc.status === "Awarded") {
			frm.add_custom_button(__("GE Contract"), function() {
				frappe.model.open_mapped_doc({
					method: "construction_ms.construction_management.doctype.ge_tender.ge_tender.make_ge_contract",
					frm: frm
				});
			}, __("Create"));
		}
	},
});
