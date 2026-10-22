// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Rate Analysis", {
	refresh(frm) {
		frm.events.calculate(frm);
		frm.events.show_unit(frm);
	},

	uom: (frm) => frm.events.show_unit(frm),

	show_unit(frm) {
		// quantities are per 1 unit of the BOQ line, never totals
		const unit = frm.doc.uom;
		frm.set_df_property("sb_resources", "label", unit ? __("Resources per 1 {0}", [unit]) : __("Resources per Unit"));
		frm.set_df_property(
			"items",
			"description",
			unit
				? __("Quantities for 1 {0} of the BOQ line (not totals). The budget multiplies them by the BOQ quantity.", [unit])
				: __("Set the unit above first: quantities are for 1 unit of the BOQ line.")
		);
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
