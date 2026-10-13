// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const BUDGET_METHOD = "consms.construction_management.doctype.bf_budget.bf_budget";

frappe.ui.form.on("BF Budget", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Refresh from BOQ"), () => {
				frappe.confirm(__("Rebuild the resources from the BOQ and its Rate Analysis? Manual changes to resource lines will be lost."), () => {
					frappe.xcall(`${BUDGET_METHOD}.refresh_from_boq`, { budget_name: frm.doc.name }).then(() => frm.reload_doc());
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
