// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Progress Claim", {
	setup: function(frm) {
		frm.set_query("variation_order", "variations", function() {
			return {
				filters: {
					"contract": frm.doc.contract,
					"docstatus": 1
				}
			};
		});
	},
	refresh: function(frm) {
		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.contract) {
			frm.add_custom_button(__("Fetch Measurements"), function() {
				frappe.call({
					method: "consms.construction_management.doctype.bf_progress_claim.bf_progress_claim.fetch_measurements",
					args: {
						claim_name: frm.doc.name,
						contract: frm.doc.contract,
						period_from: frm.doc.period_from,
						period_to: frm.doc.period_to
					},
					freeze: true,
					freeze_message: __("Calculating Valuation..."),
					callback: function(r) {
						if (r.message && r.message.status === "success") {
							frm.reload_doc();
							frappe.show_alert({message: __("Fetched " + r.message.count + " BOQ Items with measurements"), indicator: 'green'});
						}
					}
				});
			}, __("Actions"));

			frm.add_custom_button(__("Release Retention"), function() {
				const held = flt(frm.doc.retention_held_to_date) + flt(frm.doc.retention_release) - flt(frm.doc.retention_deduction);
				frappe.prompt([
					{ fieldname: "percent", fieldtype: "Percent", label: __("Release (% of retention held)"), default: 50, reqd: 1,
						description: __("Retention held before this certificate: {0}", [format_currency(held)]) },
				], (values) => {
					frm.set_value("retention_release", flt(held * values.percent / 100, 2));
					frm.save();
				}, __("Release Retention"), __("Release"));
			}, __("Actions"));
		}

		if (frm.doc.docstatus === 1) {
			if (frm.doc.claim_type === "Client Claim") {
				frm.add_custom_button(__("Sales Invoice"), function() {
					frappe.model.open_mapped_doc({
						method: "consms.construction_management.doctype.bf_progress_claim.bf_progress_claim.make_sales_invoice",
						frm: frm
					});
				}, __("Create"));
			} else {
				frm.add_custom_button(__("Purchase Invoice"), function() {
					frappe.model.open_mapped_doc({
						method: "consms.construction_management.doctype.bf_progress_claim.bf_progress_claim.make_purchase_invoice",
						frm: frm
					});
				}, __("Create"));
			}
		}
	},
	
	// The certificate is calculated on the server (retention and advance limits, VAT base): save to see the figures
	materials_on_site: function(frm) {
		frm.trigger("show_save_hint");
	},
	retention_release: function(frm) {
		frm.trigger("show_save_hint");
	},
	liquidated_damages: function(frm) {
		frm.trigger("show_save_hint");
	},
	show_save_hint: function(frm) {
		frappe.show_alert({ message: __("Save to recalculate the certificate."), indicator: "blue" });
	},
});

frappe.ui.form.on("BF Progress Claim Variation", {
	this_period_amount: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.cumulative_amount = flt(row.previously_certified) + flt(row.this_period_amount);
		
		if (flt(row.cumulative_amount) > flt(row.approved_amount)) {
			frappe.msgprint(__("Cumulative Claimed amount cannot exceed the Approved Amount."));
			frappe.model.set_value(cdt, cdn, "this_period_amount", flt(row.approved_amount) - flt(row.previously_certified));
		}
		frm.trigger("show_save_hint");
	},
	variations_remove: function(frm) {
		frm.trigger("show_save_hint");
	}
});
