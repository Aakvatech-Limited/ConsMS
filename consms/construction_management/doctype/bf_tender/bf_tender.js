// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const TENDER_METHOD = "consms.construction_management.doctype.bf_tender.bf_tender";

frappe.ui.form.on("BF Tender", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.boq) {
			frm.add_custom_button(__("Bill of Quantities"), () => frappe.set_route("Form", "BF Bill of Quantities", frm.doc.boq), __("View"));
		} else if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("BOQ"), () => {
				frappe.model.open_mapped_doc({ method: `${TENDER_METHOD}.make_bf_boq`, frm });
			}, __("Create"));
		}

		if (frm.doc.docstatus === 1 && frm.doc.status === "Bid Submitted") {
			[["Awarded", __("Mark Awarded")], ["Lost", __("Mark Lost")]].forEach(([status, label]) => {
				frm.add_custom_button(label, () => frm.events.set_status(frm, status), __("Status"));
			});
		}

		if (frm.doc.docstatus === 1 && frm.doc.status === "Awarded") {
			frm.add_custom_button(__("BF Contract"), function() {
				frappe.call({
					method: `${TENDER_METHOD}.check_existing_contract`,
					args: { tender_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({message: __("Contract already exists. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "BF Contract", r.message);
						} else {
							frappe.model.open_mapped_doc({
								method: `${TENDER_METHOD}.make_bf_contract`,
								frm: frm
							});
						}
					}
				});
			}, __("Create"));
		}
	},

	set_status(frm, status) {
		frappe.confirm(__("Mark this tender as {0}?", [__(status)]), () => {
			frappe.call({
				method: `${TENDER_METHOD}.set_status`,
				args: { tender_name: frm.doc.name, status },
				freeze: true,
				callback: () => frm.reload_doc(),
			});
		});
	},
});
