// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["Contract Status Summary"] = {
	filters: [
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "customer",
			label: __("Client"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "contract_type",
			label: __("Contract Type"),
			fieldtype: "Select",
			options: "\nMain Contract\nSubcontract",
			default: "Main Contract",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "percent_complete" && data && data.percent_complete >= 100) {
			value = `<span style="color: var(--green-600); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
