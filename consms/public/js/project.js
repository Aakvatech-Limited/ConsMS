// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new()) return;

		// The construction flow starts here: Project -> Tender -> BOQ -> Contract
		frm.add_custom_button(__("Tender"), () => {
			frappe.new_doc("BF Tender", {
				project: frm.doc.name,
				tender_name: frm.doc.project_name,
			});
		}, __("Create"));
	},
});
