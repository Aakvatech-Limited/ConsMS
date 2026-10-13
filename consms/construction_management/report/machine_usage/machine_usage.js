// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["Machine Usage"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
		{ fieldname: "asset", label: __("Asset"), fieldtype: "Link", options: "Asset" },
	],
};
