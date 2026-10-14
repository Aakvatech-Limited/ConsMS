// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Contract", {
	refresh(frm) {
		calculate_contingency(frm);
		show_time_status(frm);
		show_expiring_documents(frm);
		
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

			if (frm.doc.customer && flt(frm.doc.advance_payment_amount)) {
				frm.add_custom_button(__("Advance Payment Invoice"), function() {
					frappe.call({
						method: "consms.construction_management.doctype.bf_contract.bf_contract.make_advance_payment_invoice",
						args: { source_name: frm.doc.name },
						callback(r) {
							if (!r.message) return;
							const doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
						},
					});
				}, __("Create"));
			}

			frm.add_custom_button(__("Extension of Time"), function() {
				frappe.model.open_mapped_doc({
					method: "consms.construction_management.doctype.bf_contract.bf_contract.make_extension_of_time",
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

			frm.add_custom_button(__("Works Execution"), function() {
				frappe.model.open_mapped_doc({
					method: "consms.construction_management.doctype.bf_contract.bf_contract.make_works_execution",
					frm: frm
				});
			}, __("Create"));

			frappe.xcall("consms.construction_management.doctype.bf_works_execution.bf_works_execution.is_mobilized", {
				contract: frm.doc.name,
			}).then((mobilized) => {
				if (!mobilized) return;
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
	advance_payment_percentage(frm) {
		if (flt(frm.doc.advance_payment_percentage)) {
			frm.set_value("advance_payment_amount", flt(frm.doc.total_contract_amount) * flt(frm.doc.advance_payment_percentage) / 100);
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

function show_expiring_documents(frm) {
	const today = frappe.datetime.get_today();
	const soon = frappe.datetime.add_days(today, 30);
	const rows = (frm.doc.submittals || []).filter((r) => r.expiry_date);
	const expired = rows.filter((r) => r.expiry_date < today).map((r) => r.submittal_type);
	const expiring = rows.filter((r) => r.expiry_date >= today && r.expiry_date <= soon).map((r) => r.submittal_type);
	if (expired.length) {
		frm.dashboard.add_comment(__("Expired documents: {0}", [expired.join(", ")]), "red", true);
	}
	if (expiring.length) {
		frm.dashboard.add_comment(__("Expiring within 30 days: {0}", [expiring.join(", ")]), "orange", true);
	}
}
