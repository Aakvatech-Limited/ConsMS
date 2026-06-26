// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Contract", {
	refresh(frm) {
		calculate_contingency(frm);
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
