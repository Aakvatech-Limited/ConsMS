// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Bill of Quantities", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("BF Tender"), function() {
				frappe.call({
					method: "construction_ms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.check_existing_tender",
					args: { boq_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({message: __("A Tender already exists for this BOQ. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "BF Tender", r.message);
						} else {
							frappe.model.open_mapped_doc({
								method: "construction_ms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.make_bf_tender",
								frm: frm
							});
						}
					}
				});
			}, __("Create"));

			frm.add_custom_button(__("Material Request"), function() {
				frappe.model.open_mapped_doc({
					method: "construction_ms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.make_material_request",
					frm: frm
				});
			}, __("Create"));
		}
	},
});

frappe.ui.form.on("BF BOQ Item", {
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
