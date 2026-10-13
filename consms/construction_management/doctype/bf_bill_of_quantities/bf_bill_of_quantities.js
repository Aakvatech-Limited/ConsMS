// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Bill of Quantities", {
	setup(frm) {
		frm.set_query("task", "items", () => ({
			filters: { project: frm.doc.project, is_template: 0 },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frappe.call({
				method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_awarded_tender",
				args: { boq_name: frm.doc.name },
				callback: function(r) {
					if (!r.message) return;
					frm.add_custom_button(__("BF Contract"), function() {
						if (r.message.contract) {
							frappe.show_alert({message: __("Contract already exists. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "BF Contract", r.message.contract);
						} else {
							frappe.model.open_mapped_doc({
								method: "consms.construction_management.doctype.bf_tender.bf_tender.make_bf_contract",
								source_name: r.message.tender
							});
						}
					}, __("Create"));
				}
			});
		}
	},
});

frappe.ui.form.on("BF BOQ Item", {
	uom: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.uom) return;
		frappe.xcall("consms.construction_management.uom.get_erp_uom", { unit: row.uom }).then((uom) => {
			frappe.model.set_value(cdt, cdn, "erp_uom", uom || "");
		});
	},
	quantity: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	unit_rate: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	amount: function(frm, cdt, cdn) {
		calculate_total(frm);
	},
	items_remove: function(frm) {
		calculate_total(frm);
	}
});

function calculate_amount(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let amt = flt(row.quantity) * flt(row.unit_rate);
	frappe.model.set_value(cdt, cdn, "amount", amt);
}

function calculate_total(frm) {
	let total = 0;
	if (frm.doc.items) {
		frm.doc.items.forEach(item => {
			total += flt(item.amount);
		});
	}
	frm.set_value("total_amount", total);
}
