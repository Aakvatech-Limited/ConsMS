// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Site Mobilization", {
	mobilization_template: function(frm) {
		if (frm.doc.mobilization_template) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "GE Mobilization Template",
					name: frm.doc.mobilization_template
				},
				callback: function(r) {
					if (r.message) {
						frm.clear_table("mobilization_checklist");
						$.each(r.message.tasks || [], function(i, d) {
							let row = frm.add_child("mobilization_checklist");
							row.task = d.task;
							row.status = "Pending";
						});
						frm.refresh_field("mobilization_checklist");
					}
				}
			});
		}
	}
});
