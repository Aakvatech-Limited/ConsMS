// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const BUDGET_METHOD = "consms.construction_management.doctype.bf_budget.bf_budget";

frappe.ui.form.on("BF Budget", {
	onload(frm) {
		// lines come from the template: no adding or removing rows by hand
		frm.set_df_property("overhead_lines", "cannot_add_rows", true);
		frm.set_df_property("overhead_lines", "cannot_delete_rows", true);
	},
	setup(frm) {
		const unit_of = (row) => ((frm.doc.__onload || {}).boq_units || {})[row.boq_item];
		// only approved recipes in the BOQ line's own unit
		frm.set_query("rate_analysis", "boq_lines", (doc, cdt, cdn) => {
			const unit = unit_of(locals[cdt][cdn]);
			return { filters: unit ? { docstatus: 1, uom: unit } : { docstatus: 1 } };
		});
		// "Create a new Rate Analysis" from a line starts with the line's unit and description
		frm.fields_dict.boq_lines.grid.get_field("rate_analysis").get_route_options_for_new_doc = (field) => {
			const row = field.doc || {};
			return { uom: unit_of(row), rate_analysis_name: row.description };
		};
	},

	refresh(frm) {
		const mismatches = (frm.doc.__onload || {}).unit_mismatches || [];
		if (mismatches.length) {
			frm.dashboard.add_comment(
				__("These lines use a recipe in a different unit from the BOQ line, so their cost is wrong:") +
					"<ul>" +
					mismatches.map((m) => `<li>${__("Row {0}", [m.idx])}: ${frappe.utils.escape_html(m.description || "")} — ` +
						__("BOQ in {0}, {1} per {2}", [m.boq_unit, m.rate_analysis, m.recipe_unit]) + "</li>").join("") +
					"</ul>",
				"red",
				true
			);
		}

		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Rebuild All Resources"), () => {
				frappe.confirm(__("Re-read the BOQ and rebuild every resource line from the chosen Rate Analyses? Manual changes to resource lines will be lost."), () => {
					frappe.xcall(`${BUDGET_METHOD}.rebuild_resources`, { budget_name: frm.doc.name }).then(() => frm.reload_doc());
				});
			});
			frm.add_custom_button(__("Re-price from Price List"), () => {
				frappe.xcall(`${BUDGET_METHOD}.reprice_from_price_list`, { budget_name: frm.doc.name }).then((changed) => {
					frm.reload_doc();
					frappe.msgprint({
						title: __("Re-priced"),
						message: changed && changed.length ? changed.join("<br>") : __("All rates already match the current prices."),
						indicator: "blue",
					});
				});
			});
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Material Request"), () => {
				frappe.model.open_mapped_doc({ method: `${BUDGET_METHOD}.get_items_for_material_request`, frm });
			}, __("Create"));
		}
	},
});

frappe.ui.form.on("BF Budget Item", {
	qty: (frm, cdt, cdn) => update_amount(frm, cdt, cdn),
	rate: (frm, cdt, cdn) => update_amount(frm, cdt, cdn),
});

function update_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}
