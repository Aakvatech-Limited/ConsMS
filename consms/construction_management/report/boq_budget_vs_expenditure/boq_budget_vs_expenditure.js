// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["BOQ Budget vs Expenditure"] = {
	"filters": [
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "boq",
			"label": __("Bill of Quantities"),
			"fieldtype": "Link",
			"options": "BF Bill of Quantities"
		}
	]
};
