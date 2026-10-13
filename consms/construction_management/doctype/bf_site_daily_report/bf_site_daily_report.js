// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Site Daily Report", {
	setup(frm) {
		const boq_line_query = () => ({
			query: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_boq_items_query",
			filters: { parent: frm.doc.boq },
		});
		["labour", "plant", "materials"].forEach((table) => {
			frm.set_query("boq_item", table, boq_line_query);
			frm.set_query("task", table, () => ({ filters: { project: frm.doc.project, is_template: 0 } }));
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

	calculate(frm) {
		let labour = 0, people = 0, plant = 0, fuel = 0, material = 0;
		(frm.doc.labour || []).forEach((r) => {
			r.amount = flt(r.headcount) * flt(r.days) * flt(r.rate);
			labour += r.amount;
			people += cint(r.headcount);
		});
		(frm.doc.plant || []).forEach((r) => {
			r.amount = flt(r.hours) * flt(r.rate);
			plant += r.amount;
			fuel += flt(r.fuel_litres);
		});
		(frm.doc.materials || []).forEach((r) => (material += flt(r.amount)));
		frm.refresh_fields(["labour", "plant"]);
		frm.set_value({
			labour_cost: labour,
			total_headcount: people,
			plant_cost: plant,
			total_fuel: fuel,
			material_cost: material,
			total_cost: labour + plant + material,
		});
	},
});

function set_buying_rate(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.item_code) return;
	frappe.xcall("consms.construction_management.budget.get_item_buying_rate", { item_code: row.item_code }).then((rate) => {
		frappe.model.set_value(cdt, cdn, "rate", rate || 0);
		frm.events.calculate(frm);
	});
}

frappe.ui.form.on("BF Daily Labour", {
	item_code: set_buying_rate,
	headcount: (frm) => frm.events.calculate(frm),
	days: (frm) => frm.events.calculate(frm),
	rate: (frm) => frm.events.calculate(frm),
	labour_remove: (frm) => frm.events.calculate(frm),
});

frappe.ui.form.on("BF Daily Plant", {
	item_code: set_buying_rate,
	hours: (frm) => frm.events.calculate(frm),
	fuel_litres: (frm) => frm.events.calculate(frm),
	rate: (frm) => frm.events.calculate(frm),
	plant_remove: (frm) => frm.events.calculate(frm),
});
