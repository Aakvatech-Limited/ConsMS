// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("Material Request", {
	setup(frm) {
		frm.set_query("bf_boq_item", "items", function(doc, cdt, cdn) {
			let row = frappe.get_doc(cdt, cdn);
			let boq = row.bf_boq || doc.bf_boq;
			return {
				query: "construction_ms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_boq_items_query",
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
