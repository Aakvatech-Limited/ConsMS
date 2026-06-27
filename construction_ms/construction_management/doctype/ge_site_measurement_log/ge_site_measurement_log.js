// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("GE Site Measurement Log", {
	setup: function(frm) {
		// Filter BOQ Items to only show items from the Contract's BOQ
		frm.set_query("boq_item", "measurements", function(doc, cdt, cdn) {
			if (doc.boq) {
				return {
					filters: {
						"parent": doc.boq
					}
				};
			} else {
				frappe.msgprint(__("Please select a Contract first."));
				return {};
			}
		});
	}
});

var calculate_total_quantity = function(frm, cdt, cdn) {
	var row = frappe.get_doc(cdt, cdn);
	
	// If the user hasn't entered any dimensions, treat them as 1 for multiplication purposes,
	// UNLESS they are all empty, then just use the multiplier.
	var mult = flt(row.multiplier) || 1;
	
	var has_dims = row.length || row.width || row.height;
	
	if (!has_dims) {
		frappe.model.set_value(cdt, cdn, "total_quantity", mult);
	} else {
		var l = flt(row.length) || 1;
		var w = flt(row.width) || 1;
		var h = flt(row.height) || 1;
		frappe.model.set_value(cdt, cdn, "total_quantity", mult * l * w * h);
	}
};

frappe.ui.form.on("GE Measurement Item", {
	multiplier: calculate_total_quantity,
	length: calculate_total_quantity,
	width: calculate_total_quantity,
	height: calculate_total_quantity
});
