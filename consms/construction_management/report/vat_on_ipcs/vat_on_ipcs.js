// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.query_reports["VAT on IPCs"] = {
	filters: [
		{ fieldname: "contract", label: __("Contract"), fieldtype: "Link", options: "BF Contract" },
		{
			fieldname: "claim_type",
			label: __("Certificates"),
			fieldtype: "Select",
			options: "Client Claim\nSubcontractor Claim",
			default: "Client Claim",
		},
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
	],
};
