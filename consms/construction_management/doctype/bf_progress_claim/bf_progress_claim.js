// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Progress Claim", {
	onload(frm) {
		// lines come from the template: no adding or removing rows by hand
		frm.set_df_property("certificate_lines", "cannot_add_rows", true);
		frm.set_df_property("certificate_lines", "cannot_delete_rows", true);
	},
	setup: function(frm) {
		// only the templates made for this form
		frm.set_query("certificate_template", () => ({ filters: { used_for: "Payment Certificate" } }));
		// only the certificate documents for this kind of certificate (the same scopes the server adds rows for)
		frm.set_query("document_type", "documents", function() {
			let scopes = {
				"Interim": ["All Certificates"],
				"Substantial Completion": ["All Certificates", "Substantial Completion and Final"],
				"Final": ["All Certificates", "Substantial Completion and Final", "Final"]
			}[frm.doc.certificate_type || "Interim"];
			return {
				filters: {
					"applies_to": "Payment Certificate",
					"certificate_types": ["in", scopes]
				}
			};
		});
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
	
	// The certificate lines come from the template and are worked out on the server: save to see the figures
	certificate_type: function(frm) {
		frm.clear_table("certificate_lines");
		frm.refresh_field("certificate_lines");
		frm.trigger("show_save_hint");
	},
	certificate_template: function(frm) {
		frm.clear_table("certificate_lines");
		frm.refresh_field("certificate_lines");
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

frappe.ui.form.on("BF Certificate Line", {
	amount: function(frm) {
		frm.trigger("show_save_hint");
	},
});
