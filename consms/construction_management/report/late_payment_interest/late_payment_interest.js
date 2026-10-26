// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["Late Payment Interest"] = {
	filters: [
		{ fieldname: "contract", label: __("Contract"), fieldtype: "Link", options: "BF Contract", reqd: 1,
			get_query: () => ({ filters: { docstatus: 1, contract_type: ["!=", "Subcontract"] } }) },
		{ fieldname: "as_at", label: __("Interest up to"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_late" && data && data.days_late > 0) value = `<span class="text-danger">${value}</span>`;
		return value;
	},
};
