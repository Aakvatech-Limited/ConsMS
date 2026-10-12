// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const MEASUREMENT_FIELDS = [
	"multiplier",
	"chainage_from",
	"chainage_to",
	"length",
	"width",
	"height",
	"percent_complete",
];

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

	onload: function(frm) {
		frm.events.apply_construction_type(frm);
	},

	construction_type: function(frm) {
		frm.events.apply_construction_type(frm);
	},

	refresh: function(frm) {
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

	// Show only the boxes the contract's Construction Type uses, with its labels
	apply_construction_type: async function(frm) {
		const type = frm.doc.construction_type
			? await frappe.db.get_doc("BF Construction Type", frm.doc.construction_type)
			: { measurement_method: "Dimensions" };
		frm.construction_type_doc = type;

		const method = type.measurement_method;
		const labels = {
			multiplier: type.label_multiplier ?? __("No."),
			length: type.label_length ?? __("Length (L)"),
			width: type.label_width ?? __("Width (W)"),
			height: type.label_height ?? __("Height/Depth (H)"),
			chainage_from: __("Chainage From"),
			chainage_to: __("Chainage To"),
			percent_complete: __("% Complete"),
		};
		const shown = {
			multiplier: method !== "Percent Complete" && !!labels.multiplier,
			length: ["Dimensions", "Custom"].includes(method) && !!labels.length,
			width: ["Dimensions", "Chainage", "Custom"].includes(method) && !!labels.width,
			height: ["Dimensions", "Chainage", "Custom"].includes(method) && !!labels.height,
			chainage_from: method === "Chainage",
			chainage_to: method === "Chainage",
			percent_complete: method === "Percent Complete",
		};

		const grid = frm.fields_dict.measurements.grid;
		MEASUREMENT_FIELDS.forEach((fieldname) => {
			grid.update_docfield_property(fieldname, "label", labels[fieldname] || fieldname);
			grid.update_docfield_property(fieldname, "hidden", shown[fieldname] ? 0 : 1);
		});
		frm.set_df_property("location_grid", "label", type.location_label || __("Location / Grid Ref"));
		grid.refresh();
	},
});

// Same formulas as consms/construction_management/measurement.py; Percent Complete
// and Custom are calculated on save because they need server data.
function calculate_total_quantity(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const method = (frm.construction_type_doc || {}).measurement_method || "Dimensions";
	const count = flt(row.multiplier) || 1;
	const product = (...values) => {
		const filled = values.map(flt).filter((v) => v);
		return filled.length ? filled.reduce((a, b) => a * b, 1) : 0;
	};

	if (method === "Dimensions") {
		const dims = product(row.length, row.width, row.height);
		frappe.model.set_value(cdt, cdn, "total_quantity", dims ? count * dims : count);
	} else if (method === "Chainage") {
		const length = Math.abs(flt(row.chainage_to) - flt(row.chainage_from));
		frappe.model.set_value(cdt, cdn, "total_quantity", count * length * (product(row.width, row.height) || 1));
	}
}

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
	multiplier: calculate_total_quantity,
	chainage_from: calculate_total_quantity,
	chainage_to: calculate_total_quantity,
	length: calculate_total_quantity,
	width: calculate_total_quantity,
	height: calculate_total_quantity,
});
