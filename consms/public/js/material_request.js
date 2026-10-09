// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;

		frm.add_custom_button(__("BF Bill of Quantities"), () => {
			const method =
				"consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_items_for_material_request";

			// Opened from a BOQ: pull straight from it, no need to pick it again
			if (frm.doc.bf_boq) {
				erpnext.utils.map_current_doc({ method, source_name: [frm.doc.bf_boq], target: frm });
				return;
			}

			erpnext.utils.map_current_doc({
				method,
				source_doctype: "BF Bill of Quantities",
				target: frm,
				setters: {
					project: undefined,
				},
				get_query_filters: {
					docstatus: 1,
				},
			});
		}, __("Get Items From"));
	},

	setup(frm) {
		frm.set_query("bf_boq_item", "items", function(doc, cdt, cdn) {
			let row = frappe.get_doc(cdt, cdn);
			let boq = row.bf_boq || doc.bf_boq;
			return {
				query: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_boq_items_query",
				filters: {
					parent: boq
				}
			};
		});
	}
});

frappe.ui.form.on("Material Request Item", {
	bf_boq_item(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "bf_boq_item_id", row.bf_boq_item || "");
	}
});
