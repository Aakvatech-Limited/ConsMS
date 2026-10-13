// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Contract", {
	refresh(frm) {
		calculate_contingency(frm);
		show_time_status(frm);
		
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Variation Order"), function() {
				frappe.model.open_mapped_doc({
					method: "consms.construction_management.doctype.bf_contract.bf_contract.make_variation_order",
					frm: frm
				});
			}, __("Create"));

			frm.add_custom_button(__("Progress Claim (IPC)"), function() {
				frappe.model.open_mapped_doc({
					method: "consms.construction_management.doctype.bf_contract.bf_contract.make_progress_claim",
					frm: frm
				});
			}, __("Create"));

			frm.add_custom_button(__("Budget"), function() {
				frappe.db.get_value("BF Budget", { contract: frm.doc.name, docstatus: ["!=", 2] }, "name").then((r) => {
					if (r.message && r.message.name) {
						frappe.set_route("Form", "BF Budget", r.message.name);
					} else {
						frappe.model.open_mapped_doc({
							method: "consms.construction_management.doctype.bf_budget.bf_budget.make_bf_budget",
							frm: frm
						});
					}
				});
			}, __("Create"));

			frm.add_custom_button(__("Site Mobilization"), function() {
				frappe.model.open_mapped_doc({
					method: "consms.construction_management.doctype.bf_contract.bf_contract.make_site_mobilization",
					frm: frm
				});
			}, __("Create"));

			frappe.db.get_value("BF Site Mobilization", { contract: frm.doc.name, docstatus: 1 }, "name").then((r) => {
				if (!r.message || !r.message.name) return;
				frm.add_custom_button(__("Site Daily Report"), function() {
					frappe.model.open_mapped_doc({
						method: "consms.construction_management.doctype.bf_contract.bf_contract.make_site_daily_report",
						frm: frm
					});
				}, __("Create"));
				frm.add_custom_button(__("Site Measurement Log"), function() {
					frappe.model.open_mapped_doc({
						method: "consms.construction_management.doctype.bf_contract.bf_contract.make_site_measurement_log",
						frm: frm
					});
				}, __("Create"));
			});
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

function show_time_status(frm) {
	const d = frm.doc;
	if (d.docstatus !== 1 || !d.revised_completion_date || d.actual_completion_date) return;
	const days = frappe.datetime.get_diff(d.revised_completion_date, frappe.datetime.get_today());
	if (days < 0) {
		frm.dashboard.set_headline_alert(__("Overdue by {0} days (completion was {1}).", [-days, frappe.datetime.str_to_user(d.revised_completion_date)]), "red");
	} else {
		frm.dashboard.set_headline_alert(__("{0} days remaining to completion ({1}).", [days, frappe.datetime.str_to_user(d.revised_completion_date)]), days <= 30 ? "orange" : "blue");
	}
}
