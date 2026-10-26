// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const EOT_METHOD = "consms.construction_management.doctype.bf_extension_of_time.bf_extension_of_time";

frappe.ui.form.on("BF Extension of Time", {
	setup(frm) {
		frm.set_query("contract", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("correspondence", () => ({ filters: { contract: frm.doc.contract } }));
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== "Requested") return;

		const request = (frm.doc.documents || []).find((row) => row.document_type === "Request Letter");
		const sent = Boolean(request);
		if (request) show_response_due(frm, request.reference);
		frm.add_custom_button(sent ? __("Send Reminder") : __("Send Request"), () => send_request(frm, sent), __("Email"));

		frm.add_custom_button(__("Approve"), () => {
			frappe.prompt(
				[
					{ fieldname: "days_approved", fieldtype: "Int", label: __("Days Approved"), reqd: 1, default: frm.doc.days_requested,
						description: __("Up to {0} days requested.", [frm.doc.days_requested]) },
					{ fieldname: "decision_date", fieldtype: "Date", label: __("Approval Date"), reqd: 1, default: frappe.datetime.get_today() },
					{ fieldname: "reference", fieldtype: "Data", label: __("Letter Reference") },
					{ fieldname: "letter", fieldtype: "Attach", label: __("Approval Letter"), reqd: 1 },
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
					{ fieldname: "reference", fieldtype: "Data", label: __("Letter Reference") },
					{ fieldname: "letter", fieldtype: "Attach", label: __("Rejection Letter") },
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
	frappe.call({ method: `${EOT_METHOD}.set_decision`, args: { name: frm.doc.name, decision, ...values }, freeze: true }).then(() => frm.reload_doc());
}

function show_response_due(frm, correspondence) {
	frappe.db.get_value("BF Correspondence", correspondence, ["status", "response_due_date"]).then(({ message: c }) => {
		if (!c || c.status !== "Awaiting Response" || !c.response_due_date) return;
		const days = frappe.datetime.get_diff(c.response_due_date, frappe.datetime.get_today());
		const due = frappe.datetime.str_to_user(c.response_due_date);
		if (days < 0) {
			frm.dashboard.add_comment(__("No decision yet: the response was due on {0} ({1} days ago). Send a reminder.", [due, -days]), "red", true);
		} else {
			frm.dashboard.add_comment(__("Request sent; response due on {0}.", [due]), "blue", true);
		}
	});
}

function send_request(frm, reminder) {
	frappe.call({
		method: `${EOT_METHOD}.get_eot_request`,
		args: { name: frm.doc.name, reminder: reminder ? 1 : 0 },
		freeze: true,
		freeze_message: __("Preparing the request letter..."),
	}).then(({ message: data }) => {
		if (!data) return;
		(data.warnings || []).forEach((w) => frappe.show_alert({ message: w, indicator: "orange" }, 8));
		frm.reload_doc().then(() => {
			const composer = new frappe.views.CommunicationComposer({
				doc: frm.doc,
				frm,
				recipients: data.recipients,
				subject: data.subject,
				message: data.message,
				attachments: data.files,
			});
			// tick the letter and every supporting file so all go in one email
			const list = $(composer.dialog.fields_dict.select_attachments.wrapper);
			data.files.forEach((f) => list.find(`[data-file-name="${f.name}"]`).prop("checked", true));
		});
	});
}
