// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const STATUS_ACTIONS = {
	Submitted: [
		[__("Under Evaluation"), "Under Evaluation"],
		[__("Reject"), "Rejected"],
	],
	"Under Evaluation": [
		[__("Award"), "Awarded"],
		[__("Reject"), "Rejected"],
	],
};

frappe.ui.form.on("BF Tender", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			(STATUS_ACTIONS[frm.doc.status] || []).forEach(([label, status]) => {
				frm.add_custom_button(label, () => frm.events.set_status(frm, status), __("Status"));
			});
		}

		if (frm.doc.docstatus === 1 && frm.doc.status === "Awarded") {
			frm.add_custom_button(__("BF Contract"), function() {
				frappe.call({
					method: "consms.construction_management.doctype.bf_tender.bf_tender.check_existing_contract",
					args: { tender_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({message: __("Contract already exists. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "BF Contract", r.message);
						} else {
							frappe.model.open_mapped_doc({
								method: "consms.construction_management.doctype.bf_tender.bf_tender.make_bf_contract",
								frm: frm
							});
						}
					}
				});
			}, __("Create"));
		}
	},

	set_status(frm, status) {
		frappe.confirm(__("Change Tender status to {0}?", [__(status)]), () => {
			frappe.call({
				method: "consms.construction_management.doctype.bf_tender.bf_tender.set_status",
				args: { tender_name: frm.doc.name, status: status },
				freeze: true,
				callback: () => frm.reload_doc(),
			});
		});
	},
});
