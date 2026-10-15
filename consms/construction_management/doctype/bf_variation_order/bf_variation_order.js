// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Variation Order", {
	setup(frm) {
		frm.set_query("boq_item", "items", () => ({ filters: { parent: frm.doc.boq } }));
		frm.set_query("rate_analysis", "items", () => ({ filters: { docstatus: 1 } }));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Update Budget"), () => {
				frappe.confirm(
					__("The current budget of this contract is replaced by a new version with the approved quantities and new items. Continue?"),
					() => frappe.call({
						method: "consms.construction_management.variations.make_budget_revision",
						args: { variation_order: frm.doc.name },
						freeze: true,
						callback: (r) => r.message && frappe.set_route("Form", "BF Budget", r.message),
					})
				);
			});
		}
	},
});

frappe.ui.form.on("BF Variation Item", {
	change_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.change_type !== "Change to BOQ Line") frappe.model.set_value(cdt, cdn, "boq_item", "");
		if (row.change_type === "New Item" && !row.bill) frappe.model.set_value(cdt, cdn, "bill", __("Additional Works"));
		if (row.change_type === "Lump Sum" && !row.quantity) frappe.model.set_value(cdt, cdn, "quantity", 1);
	},
	boq_item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.boq_item) return;
		frappe.db.get_value("BF BOQ Item", row.boq_item, ["item_no", "description", "uom", "unit_rate", "revised_qty"]).then((r) => {
			const d = r.message || {};
			frappe.model.set_value(cdt, cdn, { item_no: d.item_no, description: d.description, uom: d.uom, unit_rate: d.unit_rate, current_qty: d.revised_qty });
			calculate(cdt, cdn);
		});
	},
	quantity(frm, cdt, cdn) {
		calculate(cdt, cdn);
	},
	unit_rate(frm, cdt, cdn) {
		calculate(cdt, cdn);
	},
});

function calculate(cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.quantity) * flt(row.unit_rate));
	if (row.change_type === "Change to BOQ Line") frappe.model.set_value(cdt, cdn, "new_qty", flt(row.current_qty) + flt(row.quantity));
}
