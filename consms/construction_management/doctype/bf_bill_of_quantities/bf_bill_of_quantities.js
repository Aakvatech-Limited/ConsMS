// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Bill of Quantities", {
	onload(frm) {
		// lines come from the template: no adding or removing rows by hand
		frm.set_df_property("summary_lines", "cannot_add_rows", true);
		frm.set_df_property("summary_lines", "cannot_delete_rows", true);
	},
	setup(frm) {
		frm.set_query("task", "items", () => ({
			filters: { project: frm.doc.project, is_template: 0 },
		}));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2 && (frm.doc.items || []).length) {
			frm.add_custom_button(__("VAT Exempt Bills"), () => set_vat_exempt_bills(frm), __("Actions"));
		}
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

// Bills such as Preliminaries & General carry no VAT on the payment certificates
function set_vat_exempt_bills(frm) {
	const bills = [...new Set((frm.doc.items || []).map((row) => row.bill || ""))].filter((b) => b);
	const exempt = new Set((frm.doc.items || []).filter((row) => row.vat_exempt).map((row) => row.bill));
	const dialog = new frappe.ui.Dialog({
		title: __("VAT Exempt Bills"),
		fields: [{
			fieldname: "bills",
			fieldtype: "MultiCheck",
			label: __("Bills with no VAT on Progress Claims"),
			options: bills.map((b) => ({ label: b, value: b, checked: exempt.has(b) })),
		}],
		primary_action_label: __("Save"),
		primary_action(values) {
			frappe.call({
				method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.set_vat_exempt_bills",
				args: { boq: frm.doc.name, bills: values.bills || [] },
				callback() {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}
