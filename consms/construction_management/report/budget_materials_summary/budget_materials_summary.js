// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["Budget Materials Summary"] = {
	filters: [
		{
			fieldname: "budget",
			label: __("Budget"),
			fieldtype: "Link",
			options: "BF Budget",
			reqd: 1,
			get_query: () => ({ filters: { docstatus: ["<", 2] } }),
		},
		{
			fieldname: "resource_type",
			label: __("Resource Type"),
			fieldtype: "Select",
			options: "\nMaterial\nLabour\nPlant\nSubcontract\nOther",
			default: "Material",
		},
		{
			fieldname: "by_bill",
			label: __("Split by Bill / Structure"),
			fieldtype: "Check",
		},
	],
};
