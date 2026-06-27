// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Tender", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Awarded") {
			frm.add_custom_button(__("GE Contract"), function() {
				frappe.call({
					method: "construction_ms.construction_management.doctype.ge_tender.ge_tender.check_existing_contract",
					args: { tender_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({message: __("Contract already exists. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "GE Contract", r.message);
						} else {
							frappe.model.open_mapped_doc({
								method: "construction_ms.construction_management.doctype.ge_tender.ge_tender.make_ge_contract",
								frm: frm
							});
						}
					}
				});
			}, __("Create"));
		}
	},
});
