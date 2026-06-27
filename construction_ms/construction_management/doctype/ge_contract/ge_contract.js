// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Contract", {
	refresh(frm) {
		calculate_contingency(frm);
		
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Site Mobilization"), function() {
				frappe.model.open_mapped_doc({
					method: "construction_ms.construction_management.doctype.ge_contract.ge_contract.make_site_mobilization",
					frm: frm
				});
			}, __("Create"));
		}
	},
	contract_amount: function(frm) {
		calculate_contingency(frm);
	},
	contingency_percentage: function(frm) {
		calculate_contingency(frm);
	}
});

function calculate_contingency(frm) {
	let contingency = flt(frm.doc.contract_amount) * (flt(frm.doc.contingency_percentage) / 100.0);
	frm.set_value("contingency_amount", contingency);
	
	let total = flt(frm.doc.contract_amount) + contingency;
	frm.set_value("total_contract_amount", total);
}
