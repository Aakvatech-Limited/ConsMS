// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["Running Cost vs Budget"] = {
	filters: [
		{
			fieldname: "contract",
			label: __("Contract"),
			fieldtype: "Link",
			options: "BF Contract",
			reqd: 1,
			get_query: () => ({ filters: { docstatus: 1 } }),
		},
		{
			fieldname: "group_by_bill",
			label: __("Group by Bill / Structure"),
			fieldtype: "Check",
		},
	],
};
