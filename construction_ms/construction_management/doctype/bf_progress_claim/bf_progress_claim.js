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
		if (frm.doc.docstatus === 0 && frm.doc.contract) {
			frm.add_custom_button(__("Fetch Measurements"), function() {
				frappe.call({
					method: "construction_ms.construction_management.doctype.bf_progress_claim.bf_progress_claim.fetch_measurements",
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
			frm.add_custom_button(__("Sales Invoice"), function() {
				frappe.model.open_mapped_doc({
					method: "construction_ms.construction_management.doctype.bf_progress_claim.bf_progress_claim.make_sales_invoice",
					frm: frm
				});
			}, __("Create"));
		}
	},
	
	materials_on_site: function(frm) {
		frm.trigger("calculate_totals_frontend");
	},
	retention_percentage: function(frm) {
		frm.trigger("calculate_totals_frontend");
	},
	advance_payment_recovery: function(frm) {
		frm.trigger("calculate_totals_frontend");
	},
	vat_percentage: function(frm) {
		frm.trigger("calculate_totals_frontend");
	},
	
	calculate_totals_frontend: function(frm) {
		var total_work = frm.doc.total_work_executed || 0.0;
		var total_var = 0.0;
		$.each(frm.doc.variations || [], function(i, d) {
			total_var += flt(d.this_period_amount);
		});
		frm.set_value("approved_variations", total_var);

		var gross = total_work + flt(frm.doc.materials_on_site) + total_var;
		frm.set_value("gross_valuation", gross);
		
		var retention = (flt(frm.doc.retention_percentage) / 100.0) * gross;
		frm.set_value("retention_deduction", retention);
		
		var deductions = retention + flt(frm.doc.advance_payment_recovery) + flt(frm.doc.previous_certified_amount);
		var net = gross - deductions;
		frm.set_value("net_amount_due", net);
		
		var vat = (flt(frm.doc.vat_percentage) / 100.0) * net;
		frm.set_value("vat_amount", vat);
		
		frm.set_value("total_amount_certified", net + vat);
	}
});

frappe.ui.form.on("BF Progress Claim Variation", {
	this_period_amount: function(frm, cdt, cdn) {
		frm.trigger("calculate_totals_frontend");
	},
	variations_remove: function(frm) {
		frm.trigger("calculate_totals_frontend");
	}
});
