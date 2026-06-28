// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Variation Order", {
	refresh(frm) {
		
	},
});

frappe.ui.form.on("BF Variation Item", {
	item_code: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			// First try to get Item Price
			frappe.call({
				method: "erpnext.stock.get_item_details.get_item_details",
				args: {
					args: {
						item_code: row.item_code,
						company: frappe.defaults.get_user_default("Company") || frappe.boot.default_company,
						qty: row.quantity || 1
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
	frm.set_value("requested_amount", total);
}
