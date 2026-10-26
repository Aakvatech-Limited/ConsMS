// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Site Daily Report", {
	setup(frm) {
		// open tasks of this project
		frm.set_query("task", "materials", () => ({
			filters: { project: frm.doc.project, is_template: 0, status: ["not in", ["Completed", "Cancelled"]] },
		}));
		// BOQ lines of this contract, narrowed to the row's task when it has some
		frm.set_query("boq_item", "materials", (doc, cdt, cdn) => ({
			query: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_boq_items_query",
			filters: { parent: frm.doc.boq, task: locals[cdt][cdn].task },
		}));
		frm.set_query("item_code", "materials", () => ({ filters: { is_stock_item: 1 } }));
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.source_warehouse) {
			frappe.db.get_single_value("Stock Settings", "default_warehouse").then((w) => w && frm.set_value("source_warehouse", w));
		}
	},
});

// a BOQ line chosen for another task is cleared when the task changes
frappe.ui.form.on("BF Daily Material", {
	task(frm, cdt, cdn) {
		if (locals[cdt][cdn].boq_item) frappe.model.set_value(cdt, cdn, "boq_item", null);
	},
});
