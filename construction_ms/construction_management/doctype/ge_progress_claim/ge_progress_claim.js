// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Progress Claim", {
	refresh: function(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.contract) {
			frm.add_custom_button(__("Fetch Measurements"), function() {
				frappe.call({
					method: "construction_ms.construction_management.doctype.ge_progress_claim.ge_progress_claim.fetch_measurements",
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
		var gross = total_work + flt(frm.doc.materials_on_site);
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
