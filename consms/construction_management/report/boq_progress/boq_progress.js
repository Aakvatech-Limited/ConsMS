// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["BOQ Progress"] = {
	filters: [
		{
			fieldname: "contract",
			label: __("Contract"),
			fieldtype: "Link",
			options: "BF Contract",
			reqd: 1,
			get_query: () => ({ filters: { docstatus: 1 } }),
		},
	],
};
