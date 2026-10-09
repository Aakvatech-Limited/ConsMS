// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Bill of Quantities", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("BF Tender"), function() {
				frappe.call({
					method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.check_existing_tender",
					args: { boq_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({message: __("A Tender already exists for this BOQ. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "BF Tender", r.message);
						} else {
							frappe.model.open_mapped_doc({
								method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.make_bf_tender",
								frm: frm
							});
						}
					}
				});
			}, __("Create"));

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

			frm.add_custom_button(__("Material Request"), function() {
				frappe.model.open_mapped_doc({
					method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.make_material_request",
					frm: frm
				});
			}, __("Create"));
		}
	},
});

frappe.ui.form.on("BF BOQ Item", {
	item_code: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			frappe.call({
				method: "erpnext.stock.get_item_details.get_item_details",
				args: {
					args: {
						item_code: row.item_code,
						company: frappe.defaults.get_user_default("Company") || frappe.boot.default_company,
						qty: row.quantity || 1,
						doctype: "Sales Order"
					}
				},
				callback: function(r) {
					if (r.message) {
						let rate = r.message.price_list_rate || r.message.standard_rate || r.message.valuation_rate || 0;
						frappe.model.set_value(cdt, cdn, "unit_rate", rate);
						
						if (!row.description && r.message.description) {
							frappe.model.set_value(cdt, cdn, "description", r.message.description);
						}
						if (!row.uom && r.message.stock_uom) {
							frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
						}
					}
				}
			});
		}
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
