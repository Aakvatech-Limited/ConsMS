// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const EOT_METHOD = "consms.construction_management.doctype.bf_extension_of_time.bf_extension_of_time.set_decision";

frappe.ui.form.on("BF Extension of Time", {
	setup(frm) {
		frm.set_query("contract", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("correspondence", () => ({ filters: { contract: frm.doc.contract } }));
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== "Requested") return;

		frm.add_custom_button(__("Approve"), () => {
			frappe.prompt(
				[
					{ fieldname: "days_approved", fieldtype: "Int", label: __("Days Approved"), reqd: 1, default: frm.doc.days_requested,
						description: __("Up to {0} days requested.", [frm.doc.days_requested]) },
					{ fieldname: "decision_date", fieldtype: "Date", label: __("Approval Date"), reqd: 1, default: frappe.datetime.get_today() },
					{ fieldname: "reference", fieldtype: "Data", label: __("Approval Letter / Reference") },
					{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") },
				],
				(values) => decide(frm, "Approved", values),
				__("Approve Extension of Time"),
				__("Approve")
			);
		}, __("Decision"));

		frm.add_custom_button(__("Reject"), () => {
			frappe.prompt(
				[
					{ fieldname: "decision_date", fieldtype: "Date", label: __("Date"), reqd: 1, default: frappe.datetime.get_today() },
					{ fieldname: "reference", fieldtype: "Data", label: __("Letter / Reference") },
					{ fieldname: "remarks", fieldtype: "Small Text", label: __("Reason for Rejection"), reqd: 1 },
				],
				(values) => decide(frm, "Rejected", values),
				__("Reject Extension of Time"),
				__("Reject")
			);
		}, __("Decision"));
	},
});

function decide(frm, decision, values) {
	frappe.call({ method: EOT_METHOD, args: { name: frm.doc.name, decision, ...values }, freeze: true }).then(() => frm.reload_doc());
}
