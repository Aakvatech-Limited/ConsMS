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
		// only approved recipes
		frm.set_query("rate_analysis", "boq_lines", () => ({ filters: { docstatus: 1 } }));
	},

	refresh(frm) {
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
