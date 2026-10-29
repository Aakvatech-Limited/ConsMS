// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

const BUDGET_METHOD = "consms.construction_management.doctype.bf_budget.bf_budget";
const AMOUNT_FIELDS = ["materials_amount", "labour_amount", "plant_amount", "other_amount"];

frappe.ui.form.on("BF Budget", {
	onload(frm) {
		// lines come from the template: no adding or removing rows by hand
		frm.set_df_property("overhead_lines", "cannot_add_rows", true);
		frm.set_df_property("overhead_lines", "cannot_delete_rows", true);
		// one row per BOQ line, made from the BOQ
		frm.set_df_property("boq_lines", "cannot_add_rows", true);
		frm.set_df_property("boq_lines", "cannot_delete_rows", true);
	},
	setup(frm) {
		// only the templates made for this form
		frm.set_query("overhead_template", () => ({ filters: { used_for: "Budget Overheads" } }));
		const unit_of = (row) => ((frm.doc.__onload || {}).boq_units || {})[row.boq_item];
		// only approved recipes in the BOQ line's own unit
		frm.set_query("rate_analysis", "boq_lines", (doc, cdt, cdn) => {
			const unit = unit_of(locals[cdt][cdn]);
			return { filters: unit ? { docstatus: 1, uom: unit } : { docstatus: 1 } };
		});
		// "Create a new Rate Analysis" from a line starts with the line's unit and description
		frm.fields_dict.boq_lines.grid.get_field("rate_analysis").get_route_options_for_new_doc = (field) => {
			const row = field.doc || {};
			return { uom: unit_of(row), rate_analysis_name: row.description };
		};
	},

	refresh(frm) {
		render_bill_summary(frm);

		const mismatches = (frm.doc.__onload || {}).unit_mismatches || [];
		if (mismatches.length) {
			frm.dashboard.add_comment(
				__("These lines use a recipe in a different unit from the BOQ line, so their cost is wrong:") +
					"<ul>" +
					mismatches.map((m) => `<li>${__("Row {0}", [m.idx])}: ${frappe.utils.escape_html(m.description || "")} — ` +
						__("BOQ in {0}, {1} per {2}", [m.boq_unit, m.rate_analysis, m.recipe_unit]) + "</li>").join("") +
					"</ul>",
				"red",
				true
			);
		}

		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Rebuild from BOQ and Recipes"), () => {
				frappe.confirm(__("Re-read the BOQ and rebuild the resources of every line from its recipe? Typed amounts are kept; manual changes to recipe resources are lost."), () => {
					frappe.xcall(`${BUDGET_METHOD}.rebuild_resources`, { budget_name: frm.doc.name }).then(() => frm.reload_doc());
				});
			}, __("Tools"));
			frm.add_custom_button(__("Re-price from Price List"), () => {
				frappe.xcall(`${BUDGET_METHOD}.reprice_from_price_list`, { budget_name: frm.doc.name }).then((changed) => {
					frm.reload_doc();
					frappe.msgprint({
						title: __("Re-priced"),
						message: changed && changed.length ? changed.join("<br>") : __("All rates already match the current prices."),
						indicator: "blue",
					});
				});
			}, __("Tools"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Material Request"), () => {
				frappe.model.open_mapped_doc({ method: `${BUDGET_METHOD}.get_items_for_material_request`, frm });
			}, __("Create"));
		}
	},
});

frappe.ui.form.on("BF Budget", {
	unplanned_percent(frm) {
		if (flt(frm.doc.unplanned_percent)) {
			frm.set_value("unplanned_amount", (flt(frm.doc.total_budget_cost) * flt(frm.doc.unplanned_percent)) / 100);
		}
	},
});

frappe.ui.form.on("BF Budget BOQ Line", {
	materials_amount: (frm, cdt, cdn) => update_line(frm, cdt, cdn),
	labour_amount: (frm, cdt, cdn) => update_line(frm, cdt, cdn),
	plant_amount: (frm, cdt, cdn) => update_line(frm, cdt, cdn),
	other_amount: (frm, cdt, cdn) => update_line(frm, cdt, cdn),

	make_recipe(frm, cdt, cdn) {
		// the server needs the saved line, so save first when something changed
		const open = () => make_recipe_dialog(frm, locals[cdt][cdn]);
		if (frm.is_new() || frm.is_dirty()) {
			frm.save().then(() => {
				const row = (frm.doc.boq_lines || []).find((r) => r.boq_item === locals[cdt][cdn]?.boq_item) || locals[cdt][cdn];
				make_recipe_dialog(frm, row);
			});
		} else {
			open();
		}
	},
});

frappe.ui.form.on("BF Budget Item", {
	qty: (frm, cdt, cdn) => update_amount(frm, cdt, cdn),
	rate: (frm, cdt, cdn) => update_amount(frm, cdt, cdn),
});

function update_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}

// a typed amount changes the line's budget and margin at once; the totals follow on save
function update_line(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const budget = AMOUNT_FIELDS.reduce((total, field) => total + flt(row[field]), 0);
	const margin = flt(row.boq_amount) - budget;
	frappe.model.set_value(cdt, cdn, {
		budget_cost: budget,
		budget_rate: flt(row.boq_qty) ? budget / flt(row.boq_qty) : 0,
		margin,
		margin_percent: flt(row.boq_amount) ? (margin / flt(row.boq_amount)) * 100 : 0,
	});
	render_bill_summary(frm);
}

function render_bill_summary(frm) {
	const wrapper = frm.get_field("bill_summary").$wrapper;
	const lines = frm.doc.boq_lines || [];
	if (!lines.length) {
		wrapper.html("");
		return;
	}

	const bills = [];
	const by_name = {};
	lines.forEach((line) => {
		const name = line.bill || __("General Items");
		if (!by_name[name]) {
			by_name[name] = { name, lines: 0, done: 0, boq: 0, budget: 0 };
			bills.push(by_name[name]);
		}
		const bill = by_name[name];
		bill.lines += 1;
		bill.done += flt(line.budget_cost) ? 1 : 0;
		bill.boq += flt(line.boq_amount);
		bill.budget += flt(line.budget_cost);
	});
	const total = bills.reduce((t, b) => ({ lines: t.lines + b.lines, done: t.done + b.done, boq: t.boq + b.boq, budget: t.budget + b.budget }),
		{ lines: 0, done: 0, boq: 0, budget: 0 });

	const esc = frappe.utils.escape_html;
	const money = (v) => format_currency(v, frm.doc.currency, 0);
	const margin = (b) => {
		if (!b.budget) return `<span class="text-muted">–</span>`;
		const pct = b.boq ? ((b.boq - b.budget) / b.boq) * 100 : 0;
		return `<span class="indicator-pill ${pct < 0 ? "red" : pct < 5 ? "orange" : "green"}">${format_number(pct, null, 1)}%</span>`;
	};
	const progress = (b) => {
		const pct = b.lines ? (b.done / b.lines) * 100 : 0;
		return `<div class="d-flex align-items-center" style="gap: 8px">
				<div class="progress" style="height: 6px; width: 80px; margin: 0">
					<div class="progress-bar ${b.done === b.lines ? "bg-success" : ""}" style="width: ${pct}%"></div>
				</div>
				<span class="small text-muted text-nowrap">${b.done} / ${b.lines}</span>
			</div>`;
	};
	const row = (b, bold) => `
		<tr${bold ? ' class="bold"' : ""}>
			<td>${bold ? __("Total") : esc(b.name)}</td>
			<td>${progress(b)}</td>
			<td class="text-right">${money(b.boq)}</td>
			<td class="text-right">${b.budget ? money(b.budget) : '<span class="text-muted">–</span>'}</td>
			<td class="text-right">${margin(b)}</td>
		</tr>`;

	wrapper.html(`
		<div class="text-muted small mb-2">${__("Summary by Bill")}</div>
		<table class="table table-sm table-hover" style="margin-bottom: var(--margin-md)">
			<thead>
				<tr class="text-muted small">
					<th style="font-weight: normal">${__("Bill")}</th>
					<th style="font-weight: normal">${__("Lines Budgeted")}</th>
					<th class="text-right" style="font-weight: normal">${__("BOQ Amount")}</th>
					<th class="text-right" style="font-weight: normal">${__("Budget")}</th>
					<th class="text-right" style="font-weight: normal">${__("Margin")}</th>
				</tr>
			</thead>
			<tbody>${bills.map((b) => row(b)).join("")}${bills.length > 1 ? row(total, true) : ""}</tbody>
		</table>`);
}

function make_recipe_dialog(frm, line) {
	const unit = ((frm.doc.__onload || {}).boq_units || {})[line.boq_item];
	if (!unit) {
		frappe.msgprint(__("This BOQ line has no ERP unit. Set it on the Bill of Quantities first."));
		return;
	}
	const qty = `${format_number(line.boq_qty, null, 2)} ${unit}`;
	const WHOLE = __("For the whole line ({0})", [qty]);
	const PER_UNIT = __("Per 1 {0}", [unit]);

	const dialog = new frappe.ui.Dialog({
		title: __("Make Recipe"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				options: `<div class="small text-muted mb-3">${frappe.utils.escape_html(line.item_no || "")}
					${frappe.utils.escape_html((line.description || "").slice(0, 160))}<br>
					${__("BOQ")}: ${qty} × ${format_currency(line.boq_rate)} = <b>${format_currency(line.boq_amount)}</b></div>`,
			},
			{ fieldname: "recipe_name", fieldtype: "Data", label: __("Recipe Name"), reqd: 1,
				default: (line.description || "").slice(0, 140),
				description: __("Name it after the work, e.g. Concrete C25, so it can be reused on other lines.") },
			{ fieldtype: "Column Break" },
			{ fieldname: "basis", fieldtype: "Select", label: __("Quantities and Amounts Are"), reqd: 1,
				options: [WHOLE, PER_UNIT].join("\n"), default: WHOLE,
				description: __("The recipe is kept per 1 {0}, so it can be used on other {0} lines.", [unit]) },
			{ fieldtype: "Section Break" },
			{
				fieldname: "materials",
				fieldtype: "Table",
				label: __("Materials"),
				description: __("Material, quantity and buying rate (filled from the price list)."),
				cannot_add_rows: false,
				in_place_edit: true,
				data: [],
				fields: [
					{ fieldname: "item_code", fieldtype: "Link", options: "Item", label: __("Material"), in_list_view: 1, columns: 4,
						get_query: () => ({ filters: { is_stock_item: 1, disabled: 0 } }),
						onchange() { fill_rate(dialog, this); } },
					{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), in_list_view: 1, columns: 2 },
					{ fieldname: "rate", fieldtype: "Currency", label: __("Rate"), in_list_view: 1, columns: 2 },
					{ fieldname: "wastage_percent", fieldtype: "Percent", label: __("Wastage %"), in_list_view: 1, columns: 2 },
				],
			},
			{ fieldtype: "Section Break", label: __("Labour, Machines and Other"),
				description: __("Amounts in money. No item is needed: gangs and hired machines are paid as suppliers.") },
			{ fieldname: "labour", fieldtype: "Currency", label: __("Labour") },
			{ fieldtype: "Column Break" },
			{ fieldname: "plant", fieldtype: "Currency", label: __("Machines") },
			{ fieldtype: "Column Break" },
			{ fieldname: "other", fieldtype: "Currency", label: __("Other") },
		],
		primary_action_label: __("Save and Use on This Line"),
		primary_action(values) {
			frappe.call({
				method: `${BUDGET_METHOD}.make_recipe`,
				args: {
					budget_name: frm.doc.name,
					line_name: line.name,
					recipe_name: values.recipe_name,
					per_unit: values.basis === PER_UNIT ? 1 : 0,
					materials: (values.materials || []).filter((m) => m.item_code),
					labour: values.labour,
					plant: values.plant,
					other: values.other,
				},
				freeze: true,
				freeze_message: __("Making the recipe..."),
			}).then(({ message }) => {
				dialog.hide();
				frm.reload_doc().then(() => {
					frappe.show_alert({ message: __("Recipe {0} made and used on the line.", [message]), indicator: "green" });
				});
			});
		},
	});
	dialog.show();
}

// the material's buying price, as on the Rate Analysis
function fill_rate(dialog, control) {
	const row = control.doc;
	if (!row || !row.item_code) return;
	frappe.xcall("consms.construction_management.budget.get_item_buying_rate", { item_code: row.item_code }).then((rate) => {
		if (rate && !flt(row.rate)) {
			row.rate = rate;
			dialog.fields_dict.materials.grid.refresh();
		}
	});
}
