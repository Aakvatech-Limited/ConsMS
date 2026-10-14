// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Site Measurement Log", {
	setup: function(frm) {
		// Filter BOQ Items to only show items from the Contract's BOQ
		frm.set_query("boq_item", "measurements", function(doc, cdt, cdn) {
			if (doc.boq) {
				return {
					query: "consms.construction_management.doctype.bf_site_measurement_log.bf_site_measurement_log.get_boq_items_query",
					filters: {
						"parent": doc.boq
					}
				};
			} else {
				frappe.msgprint(__("Please select a Contract first."));
				return {};
			}
		});
		frm.set_query("task", "measurements", () => ({
			filters: { project: frm.doc.project, is_template: 0 },
		}));
	},

	refresh: function(frm) {
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			// Quantities beyond the revised BOQ need an approved Variation Order first
			frm.add_custom_button(__("Create Variation Order"), function() {
				frappe.call({
					method: "consms.construction_management.variations.make_variation_order_from_measurement",
					args: { measurement_log: frm.doc.name },
					callback: function(r) {
						if (!r.message) return;
						const doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					},
				});
			}, __("Actions"));
		}
		if (frm.doc.boq && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch BOQ Items"), function() {
				frappe.call({
					method: "consms.construction_management.doctype.bf_site_measurement_log.bf_site_measurement_log.fetch_boq_items",
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
								row.task = item.task;
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
	},
});

frappe.ui.form.on("BF Measurement Item", {
	boq_item: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (row.boq_item) {
			frappe.call({
				method: "consms.construction_management.doctype.bf_site_measurement_log.bf_site_measurement_log.get_boq_item_details",
				args: { item_name: row.boq_item },
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "item_description", r.message.description);
						frappe.model.set_value(cdt, cdn, "uom", r.message.uom);
						if (!row.task && r.message.task) {
							frappe.model.set_value(cdt, cdn, "task", r.message.task);
						}
					}
				}
			});
		}
	},
});
