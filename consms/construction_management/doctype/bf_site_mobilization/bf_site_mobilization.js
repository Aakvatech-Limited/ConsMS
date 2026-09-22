// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Site Mobilization", {
	mobilization_template: function(frm) {
		if (frm.doc.mobilization_template) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "BF Mobilization Template",
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
						calculate_status(frm);
					}
				}
			});
		}
	}
});

frappe.ui.form.on("BF Site Mobilization Item", {
	status: function(frm, cdt, cdn) {
		calculate_status(frm);
	},
	mobilization_checklist_remove: function(frm, cdt, cdn) {
		calculate_status(frm);
	}
});

function calculate_status(frm) {
	let all_completed = true;
	let any_started = false;
	
	if (!frm.doc.mobilization_checklist || frm.doc.mobilization_checklist.length === 0) {
		frm.set_value("mobilization_status", "Not Started");
		return;
	}
	
	frm.doc.mobilization_checklist.forEach(d => {
		if (d.status === "Completed") {
			any_started = true;
		} else if (d.status === "In Progress") {
			any_started = true;
			all_completed = false;
		} else { // Pending
			all_completed = false;
		}
	});
	
	if (all_completed) {
		frm.set_value("mobilization_status", "Completed");
	} else if (any_started) {
		frm.set_value("mobilization_status", "In Progress");
	} else {
		frm.set_value("mobilization_status", "Not Started");
	}
}
