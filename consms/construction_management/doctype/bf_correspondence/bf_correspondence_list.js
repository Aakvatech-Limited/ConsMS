// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.listview_settings["BF Correspondence"] = {
	add_fields: ["status", "response_due_date"],
	get_indicator(doc) {
		if (doc.status === "Awaiting Response" && doc.response_due_date && doc.response_due_date < frappe.datetime.get_today()) {
			return [__("Overdue"), "red", `status,=,Awaiting Response|response_due_date,<,${frappe.datetime.get_today()}`];
		}
		const colors = { Open: "blue", "Awaiting Response": "orange", Responded: "green", Closed: "gray" };
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
