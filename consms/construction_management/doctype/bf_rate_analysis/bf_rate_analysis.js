// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Rate Analysis", {
	refresh(frm) {
		frm.events.calculate(frm);
	},

	calculate(frm) {
		let total = 0;
		(frm.doc.items || []).forEach((row) => {
			row.amount = flt(row.qty) * (1 + flt(row.wastage_percent) / 100) * flt(row.rate);
			total += row.amount;
		});
		frm.refresh_field("items");
		frm.set_value("cost_per_unit", total);
	},
});

frappe.ui.form.on("BF Rate Analysis Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) return;
		frappe
			.xcall("consms.construction_management.budget.get_item_buying_rate", { item_code: row.item_code, uom: row.uom })
			.then((rate) => {
				if (rate) frappe.model.set_value(cdt, cdn, "rate", rate);
			});
	},
	qty: (frm) => frm.events.calculate(frm),
	rate: (frm) => frm.events.calculate(frm),
	wastage_percent: (frm) => frm.events.calculate(frm),
	items_remove: (frm) => frm.events.calculate(frm),
});
