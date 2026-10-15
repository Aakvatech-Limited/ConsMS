// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

frappe.ui.form.on("BF Bill of Quantities", {
	onload(frm) {
		// lines come from the template: no adding or removing rows by hand
		frm.set_df_property("summary_lines", "cannot_add_rows", true);
		frm.set_df_property("summary_lines", "cannot_delete_rows", true);
	},
	setup(frm) {
		frm.set_query("task", "items", () => ({
			filters: { project: frm.doc.project, is_template: 0 },
		}));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Import with AI"), () => import_with_ai(frm)).addClass("btn-primary");
		}
		if (!frm.is_new() && frm.doc.docstatus < 2 && (frm.doc.items || []).length) {
			frm.add_custom_button(__("VAT Exempt Bills"), () => set_vat_exempt_bills(frm), __("Actions"));
		}
		if (frm.doc.docstatus === 1) {
			frappe.call({
				method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.get_awarded_tender",
				args: { boq_name: frm.doc.name },
				callback: function(r) {
					if (!r.message) return;
					frm.add_custom_button(__("BF Contract"), function() {
						if (r.message.contract) {
							frappe.show_alert({message: __("Contract already exists. Redirecting..."), indicator: 'green'});
							frappe.set_route("Form", "BF Contract", r.message.contract);
						} else {
							frappe.model.open_mapped_doc({
								method: "consms.construction_management.doctype.bf_tender.bf_tender.make_bf_contract",
								source_name: r.message.tender
							});
						}
					}, __("Create"));
				}
			});
		}
	},
});

frappe.ui.form.on("BF BOQ Item", {
	uom: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.uom) return;
		frappe.xcall("consms.construction_management.uom.get_erp_uom", { unit: row.uom }).then((uom) => {
			frappe.model.set_value(cdt, cdn, "erp_uom", uom || "");
		});
	},
	quantity: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	unit_rate: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	amount: function(frm, cdt, cdn) {
		calculate_total(frm);
	},
	items_remove: function(frm) {
		calculate_total(frm);
	}
});

function calculate_amount(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let amt = flt(row.quantity) * flt(row.unit_rate);
	frappe.model.set_value(cdt, cdn, "amount", amt);
}

function calculate_total(frm) {
	let total = 0;
	if (frm.doc.items) {
		frm.doc.items.forEach(item => {
			total += flt(item.amount);
		});
	}
	frm.set_value("total_amount", total);
}

// Bills such as Preliminaries & General carry no VAT on the payment certificates
function set_vat_exempt_bills(frm) {
	const bills = [...new Set((frm.doc.items || []).map((row) => row.bill || ""))].filter((b) => b);
	const exempt = new Set((frm.doc.items || []).filter((row) => row.vat_exempt).map((row) => row.bill));
	const dialog = new frappe.ui.Dialog({
		title: __("VAT Exempt Bills"),
		fields: [{
			fieldname: "bills",
			fieldtype: "MultiCheck",
			label: __("Bills with no VAT on Progress Claims"),
			options: bills.map((b) => ({ label: b, value: b, checked: exempt.has(b) })),
		}],
		primary_action_label: __("Save"),
		primary_action(values) {
			frappe.call({
				method: "consms.construction_management.doctype.bf_bill_of_quantities.bf_bill_of_quantities.set_vat_exempt_bills",
				args: { boq: frm.doc.name, bills: values.bills || [] },
				callback() {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}

// Import a client's BOQ Excel as received: the AI works out the layout, the numbers come from the Excel
function import_with_ai(frm) {
	const has_lines = (frm.doc.items || []).length > 0;
	const dialog = new frappe.ui.Dialog({
		title: __("Import BOQ with AI"),
		size: "extra-large",
		fields: [
			{ fieldname: "file", fieldtype: "Attach", label: __("Client BOQ Excel (as received)"), reqd: 1 },
			{ fieldname: "replace", fieldtype: "Check", label: __("Replace the {0} lines already in this BOQ", [(frm.doc.items || []).length]), hidden: !has_lines },
			{ fieldname: "set_summary", fieldtype: "Check", label: __("Also set the Tender Summary from the file's summary"), default: 1, hidden: 1 },
			{ fieldname: "preview", fieldtype: "HTML" },
		],
		primary_action_label: __("Read File"),
		primary_action(values) {
			if (dialog.token) {
				insert(values);
			} else {
				read(values);
			}
		},
	});

	function show(html) {
		dialog.fields_dict.preview.$wrapper.html(html);
	}

	function read(values) {
		dialog.disable_primary_action();
		show(`<div class="text-muted">${__("Reading the file... (large BOQs take up to a minute)")}</div>`);
		frappe.call({
			method: "consms.construction_management.boq_ai_import.preview_import",
			args: { boq: frm.doc.name, file_url: values.file },
			callback(r) {
				if (r.message) poll(r.message, 0);
			},
			error() {
				dialog.enable_primary_action();
			},
		});
	}

	function poll(token, tries) {
		frappe.call({
			method: "consms.construction_management.boq_ai_import.get_preview",
			args: { token },
			callback(r) {
				const state = r.message || {};
				if (state.status === "done") {
					dialog.token = token;
					render(state.result);
					dialog.set_primary_action(__("Insert into BOQ"), () => insert(dialog.get_values()));
					dialog.enable_primary_action();
				} else if (state.status === "error" || state.status === "expired" || tries > 150) {
					show(`<div class="text-danger">${frappe.utils.escape_html(state.message || __("Reading the file failed. Try again."))}</div>`);
					dialog.enable_primary_action();
				} else {
					setTimeout(() => poll(token, tries + 1), 2000);
				}
			},
		});
	}

	function render(result) {
		const fmt = (v) => format_currency(v);
		const esc = frappe.utils.escape_html;
		const counts = Object.entries(result.counts || {}).map(([k, v]) => `${v} ${k}`).join(", ");
		const matches = result.file_total == null || Math.abs(result.total - result.file_total) <= 1;
		let html = `<div class="mb-3">
			<div><b>${__("Read by")}:</b> ${esc(result.source)}</div>
			<div><b>${__("Rows")}:</b> ${esc(counts)}</div>
			<div><b>${__("Items to import")}:</b> ${result.items.length} &nbsp; <b>${__("Total")}:</b> ${fmt(result.total)}
				${result.file_total == null ? "" : `&nbsp; <b>${__("File total")}:</b> ${fmt(result.file_total)}
				<span class="indicator-pill ${matches ? "green" : "red"}">${matches ? __("Totals match") : __("Totals differ")}</span>`}</div>
		</div>`;
		if ((result.notes || []).length) {
			html += `<div class="alert alert-warning small"><b>${__("Check")}:</b><ul class="mb-0">${result.notes.slice(0, 30).map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>`;
		}
		const sm = result.summary;
		dialog.set_df_property("set_summary", "hidden", !sm);
		if (sm) {
			html += `<div class="mb-3"><b>${__("Tender Summary from the file")}</b>
				<span class="indicator-pill ${sm.matches ? "green" : "red"}">${sm.matches ? __("Bid price matches the file") : __("Bid price differs")}</span>
				<div class="small text-muted">${__("Template")}: ${esc(sm.template)} &nbsp; ${__("Contingency")}: ${sm.contingency_rate}% &nbsp; ${__("VAT")}: ${sm.vat_rate}%
				${sm.variation_amount ? "&nbsp; " + __("Variation of prices") + ": " + fmt(sm.variation_amount) : ""}</div>
				<table class="table table-sm table-bordered small mt-1" style="max-width: 640px"><tbody>
				${sm.summary_lines.map((l) => `<tr><td>${esc(l.label)}</td><td class="text-right">${fmt(l.amount)}</td></tr>`).join("")}
				<tr><td><b>${__("Bid Price")}</b></td><td class="text-right"><b>${fmt(sm.bid)}</b>${sm.file_bid == null ? "" : ` <span class="text-muted">(${__("file")}: ${fmt(sm.file_bid)})</span>`}</td></tr>
				</tbody></table></div>`;
		}
		html += `<div style="max-height: 420px; overflow: auto"><table class="table table-sm table-bordered small">
			<thead><tr><th>${__("Item No")}</th><th>${__("Description")}</th><th>${__("Bill / Section")}</th><th>${__("Unit")}</th>
			<th class="text-right">${__("Qty")}</th><th class="text-right">${__("Rate")}</th><th class="text-right">${__("Amount")}</th></tr></thead><tbody>`;
		for (const i of result.items) {
			html += `<tr><td>${esc(i.item_no)}</td><td>${esc(i.description)}</td><td>${esc(i.bill)}</td><td>${esc(i.unit)}</td>
				<td class="text-right">${i.quantity}</td><td class="text-right">${fmt(i.rate)}</td><td class="text-right">${fmt(i.quantity * i.rate)}</td></tr>`;
		}
		html += "</tbody></table></div>";
		show(html);
	}

	function insert(values) {
		frappe.call({
			method: "consms.construction_management.boq_ai_import.insert_into_boq",
			args: { boq: frm.doc.name, token: dialog.token, replace: values.replace ? 1 : 0, set_summary: values.set_summary ? 1 : 0 },
			freeze: true,
			callback(r) {
				if (!r.message) return;
				dialog.hide();
				frm.reload_doc();
				frappe.show_alert({ message: __("{0} lines imported. Total {1}, bid price {2}", [r.message.count, format_currency(r.message.total), format_currency(r.message.bid_price)]), indicator: "green" });
			},
		});
	}

	dialog.show();
}
