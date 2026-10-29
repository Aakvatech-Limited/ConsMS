// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Construction Settings", {
	setup(frm) {
		// only the templates made for this form
		frm.set_query("default_certificate_template", () => ({ filters: { used_for: "Payment Certificate" } }));
		frm.set_query("default_boq_summary_template", () => ({ filters: { used_for: "BOQ Summary" } }));
	},
	refresh(frm) {
		frm.add_custom_button(__("Test AI Connection"), () => {
			if (frm.is_dirty()) {
				frappe.msgprint(__("Save the settings first."));
				return;
			}
			frappe.call({
				method: "consms.construction_management.boq_ai_import.test_connection",
				freeze: true,
				freeze_message: __("Asking the AI provider..."),
				callback(r) {
					if (r.message && r.message.ok) {
						frappe.msgprint({ title: __("AI connected"), indicator: "green", message: __("The AI answered (model {0}). Import with AI is ready on the BOQ.", [r.message.model]) });
					}
				},
			});
		});
	},
});
