// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Works Execution", {
	setup(frm) {
		frm.set_query("task", "tasks", () => ({
			filters: { project: frm.doc.project, is_template: 0 },
		}));
		// Labour rows pick trades, Plant rows pick machines
		frm.set_query("item_code", "resources", (doc, cdt, cdn) => ({
			filters: { item_group: RESOURCE_ITEM_GROUP[locals[cdt][cdn].resource_type], disabled: 0 },
		}));
		frm.set_query("employee", "resources", () => ({ filters: { status: "Active" } }));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.project) {
			frm.add_custom_button(__("Project Tasks"), () => {
				frappe.set_route("List", "Task", { project: frm.doc.project, type: frm.doc.activity_type });
			});
		}
	},

	activity_type(frm) {
		if (!frm.doc.activity_type) return;
		frappe.db.get_value("BF Activity Type", frm.doc.activity_type, "default_project_template").then((r) => {
			const template = r.message && r.message.default_project_template;
			if (template && !frm.doc.project_template && !(frm.doc.tasks || []).length) {
				frm.set_value("project_template", template);
			}
		});
	},

	project_template(frm) {
		if (!frm.doc.project_template) return;

		// Tasks are created from the template on save
		frm.clear_table("tasks");
		frm.refresh_field("tasks");
		calculate_status(frm);
		frappe.show_alert({
			message: __("The template's tasks will be created in project {0} when you save.", [frm.doc.project || ""]),
			indicator: "blue",
		});
	},
});

const RESOURCE_ITEM_GROUP = { Labour: "Labour", Plant: "Plant & Equipment" };

frappe.ui.form.on("BF Works Execution Resource", {
	resource_type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, { item_code: "", employee: "", asset: "" });
	},
	employee(frm, cdt, cdn) {
		if (locals[cdt][cdn].employee) frappe.model.set_value(cdt, cdn, "quantity", 1);
	},
});

frappe.ui.form.on("BF Works Execution Task", {
	status(frm) {
		calculate_status(frm);
	},
	tasks_remove(frm) {
		calculate_status(frm);
	},
});

function calculate_status(frm) {
	const statuses = (frm.doc.tasks || []).map((d) => d.status);
	let status = "Not Started";
	if (statuses.length && statuses.every((s) => s === "Completed")) {
		status = "Completed";
	} else if (statuses.some((s) => s === "In Progress" || s === "Completed")) {
		status = "In Progress";
	}
	frm.set_value("status", status);
}
