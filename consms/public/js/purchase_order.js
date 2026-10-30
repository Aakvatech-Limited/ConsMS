// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

// BOQ Line on a purchase row: the project's BOQ lines, shown as Item No. and description,
// so every order is checked against the line's budget amount
frappe.ui.form.on("Purchase Order", {
	setup(frm) {
		frm.set_query("bf_boq_item", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {
				query: "consms.budget_control.boq_line_query",
				filters: { project: row.project || doc.project || "" },
			};
		});
	},
});
