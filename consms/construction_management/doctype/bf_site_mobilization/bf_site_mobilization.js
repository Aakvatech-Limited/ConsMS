// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Site Mobilization", {
	setup(frm) {
		frm.set_query("task", "mobilization_checklist", () => ({
			filters: { project: frm.doc.project, is_template: 0 },
		}));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.project) {
			frm.add_custom_button(__("Project Tasks"), () => {
				frappe.set_route("List", "Task", { project: frm.doc.project, type: "Mobilization" });
			});
		}
	},

	mobilization_template(frm) {
		if (!frm.doc.mobilization_template) return;

		// Tasks are created from the template on save
		frm.clear_table("mobilization_checklist");
		frm.refresh_field("mobilization_checklist");
		calculate_status(frm);
		frappe.show_alert({
			message: __("The template's tasks will be created in project {0} when you save.", [frm.doc.project || ""]),
			indicator: "blue",
		});
	},
});

frappe.ui.form.on("BF Site Mobilization Item", {
	status(frm) {
		calculate_status(frm);
	},
	mobilization_checklist_remove(frm) {
		calculate_status(frm);
	},
});

function calculate_status(frm) {
	const statuses = (frm.doc.mobilization_checklist || []).map((d) => d.status);
	let status = "Not Started";
	if (statuses.length && statuses.every((s) => s === "Completed")) {
		status = "Completed";
	} else if (statuses.some((s) => s === "In Progress" || s === "Completed")) {
		status = "In Progress";
	}
	frm.set_value("mobilization_status", status);
}
