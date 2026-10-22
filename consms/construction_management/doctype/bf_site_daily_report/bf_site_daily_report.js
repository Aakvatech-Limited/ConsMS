// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const DAILY_TABLES = ["labour", "plant", "materials"];

frappe.ui.form.on("BF Site Daily Report", {
	setup(frm) {
		DAILY_TABLES.forEach((table) => {
			// open tasks of this project
			frm.set_query("task", table, () => ({
				filters: { project: frm.doc.project, is_template: 0, status: ["not in", ["Completed", "Cancelled"]] },
			}));
			// BOQ lines of this contract, narrowed to the row's task when it has some
			frm.set_query("boq_item", table, (doc, cdt, cdn) => ({
				query: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_boq_items_query",
				filters: { parent: frm.doc.boq, task: locals[cdt][cdn].task },
			}));
		});
		frm.set_query("item_code", "labour", () => ({ filters: { item_group: "Labour" } }));
		frm.set_query("item_code", "plant", () => ({ filters: { item_group: "Plant & Equipment" } }));
		frm.set_query("item_code", "materials", () => ({ filters: { is_stock_item: 1 } }));
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.source_warehouse) {
			frappe.db.get_single_value("Stock Settings", "default_warehouse").then((w) => w && frm.set_value("source_warehouse", w));
		}
	},

	set_summary(frm) {
		const labour = frm.doc.labour || [];
		frm.set_value({
			total_headcount: labour.reduce((t, r) => t + cint(r.headcount), 0),
			man_days: labour.reduce((t, r) => t + cint(r.headcount) * flt(r.days), 0),
			machines_on_site: (frm.doc.plant || []).length,
		});
	},
});

frappe.ui.form.on("BF Daily Labour", {
	employee(frm, cdt, cdn) {
		if (locals[cdt][cdn].employee) frappe.model.set_value(cdt, cdn, "headcount", 1);
	},
	headcount: (frm) => frm.events.set_summary(frm),
	days: (frm) => frm.events.set_summary(frm),
	labour_remove: (frm) => frm.events.set_summary(frm),
});

frappe.ui.form.on("BF Daily Plant", {
	plant_add: (frm) => frm.events.set_summary(frm),
	plant_remove: (frm) => frm.events.set_summary(frm),
});

// a BOQ line chosen for another task is cleared when the task changes
DAILY_TABLES.forEach((table) => {
	const child = { labour: "BF Daily Labour", plant: "BF Daily Plant", materials: "BF Daily Material" }[table];
	frappe.ui.form.on(child, {
		task(frm, cdt, cdn) {
			if (locals[cdt][cdn].boq_item) frappe.model.set_value(cdt, cdn, "boq_item", null);
		},
	});
});
