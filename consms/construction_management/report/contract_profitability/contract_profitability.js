// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["Contract Profitability"] = {
	filters: [
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
		{ fieldname: "customer", label: __("Client"), fieldtype: "Link", options: "Customer" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (["profit_to_date", "estimated_profit", "margin_to_date"].includes(column.fieldname) && data && data[column.fieldname] < 0) {
			value = `<span class="text-danger">${value}</span>`;
		}
		return value;
	},
};
