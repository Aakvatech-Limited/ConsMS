// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Site Measurement Log", {
	setup: function(frm) {
		// Filter BOQ Items to only show items from the Contract's BOQ
		frm.set_query("boq_item", "measurements", function(doc, cdt, cdn) {
			if (doc.boq) {
				return {
					filters: {
						"parent": doc.boq
					}
				};
			} else {
				frappe.msgprint(__("Please select a Contract first."));
				return {};
			}
		});
	},
	refresh: function(frm) {
		if (frm.doc.boq && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch BOQ Items"), function() {
				frappe.call({
					method: "construction_ms.construction_management.doctype.ge_site_measurement_log.ge_site_measurement_log.fetch_boq_items",
					args: {
						boq_name: frm.doc.boq
					},
					callback: function(r) {
						if (r.message && r.message.length > 0) {
							frm.clear_table("measurements");
							r.message.forEach(function(item) {
								var row = frm.add_child("measurements");
								row.boq_item = item.name;
								row.item_description = item.description;
								row.uom = item.uom;
							});
							frm.refresh_field("measurements");
							frappe.show_alert({message: __("Fetched " + r.message.length + " BOQ Items"), indicator: 'green'});
						} else {
							frappe.msgprint(__("No items found in the attached BOQ."));
						}
					}
				});
			}, __("Actions"));
		}
	}
});

var calculate_total_quantity = function(frm, cdt, cdn) {
	var row = frappe.get_doc(cdt, cdn);
	
	// If the user hasn't entered any dimensions, treat them as 1 for multiplication purposes,
	// UNLESS they are all empty, then just use the multiplier.
	var mult = flt(row.multiplier) || 1;
	
	var has_dims = row.length || row.width || row.height;
	
	if (!has_dims) {
		frappe.model.set_value(cdt, cdn, "total_quantity", mult);
	} else {
		var l = flt(row.length) || 1;
		var w = flt(row.width) || 1;
		var h = flt(row.height) || 1;
		frappe.model.set_value(cdt, cdn, "total_quantity", mult * l * w * h);
	}
};

frappe.ui.form.on("GE Measurement Item", {
	boq_item: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (row.boq_item) {
			frappe.call({
				method: "construction_ms.construction_management.doctype.ge_site_measurement_log.ge_site_measurement_log.get_boq_item_details",
				args: { item_name: row.boq_item },
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "item_description", r.message.description);
						frappe.model.set_value(cdt, cdn, "uom", r.message.uom);
					}
				}
			});
		}
	},
	multiplier: calculate_total_quantity,
	length: calculate_total_quantity,
	width: calculate_total_quantity,
	height: calculate_total_quantity
});
