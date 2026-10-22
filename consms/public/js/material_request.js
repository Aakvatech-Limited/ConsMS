// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;

		frm.add_custom_button(__("Budget"), () => {
			const method = "consms.construction_management.doctype.bf_budget.bf_budget.get_items_for_material_request";

			// Opened from a Budget: pull straight from it, no need to pick it again
			if (frm.doc.bf_budget) {
				erpnext.utils.map_current_doc({ method, source_name: [frm.doc.bf_budget], target: frm });
				return;
			}

			erpnext.utils.map_current_doc({
				method,
				source_doctype: "BF Budget",
				target: frm,
				setters: { project: undefined },
				get_query_filters: { docstatus: 1 },
			});
		}, __("Get Items From"));
	},
});
