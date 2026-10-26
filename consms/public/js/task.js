// Copyright (c) 2026, Sydney Kibanga and contributors
// For license information, please see license.txt

// Site Activity: what happened on this task across days (daily reports), and its cost from the books
frappe.ui.form.on("Task", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.is_template) return;
		frappe
			.xcall("consms.construction_management.task_activity.get_task_site_activity", { task: frm.doc.name })
			.then((a) => {
				if (!a || (!a.days_worked && !a.materials.length && !a.other_costs.length)) return;
				frm.dashboard.add_section(site_activity_html(a), __("Site Activity"));
			});
	},
});

function site_activity_html(a) {
	const esc = frappe.utils.escape_html;
	const num = (v) => format_number(v, null, 1);
	const date = (d) => (d ? frappe.datetime.str_to_user(d) : "");
	const figures = [
		[__("Done"), `${num(a.progress)}%`],
		[__("Days on Site"), a.days_worked],
		[__("Period"), a.first_day ? `${date(a.first_day)} – ${date(a.last_day)}` : "–"],
		[__("Materials Cost"), format_currency(a.materials_cost)],
		[__("Other Costs"), format_currency(a.other_cost)],
		[__("Total Cost"), format_currency(a.total_cost)],
	];
	const list = (title, rows) =>
		rows.length
			? `<div class="col-md-4"><div class="text-muted small mb-1">${title}</div>${rows.join("")}</div>`
			: "";
	const line = (left, right) =>
		`<div class="d-flex justify-content-between small" style="gap: 12px"><span>${left}</span><span class="text-muted text-nowrap">${right}</span></div>`;

	return `
		<div class="row mb-3">
			${figures.map(([label, value]) => `
				<div class="col-sm-4 col-md-2 mb-2">
					<div class="text-muted small">${label}</div>
					<div class="bold">${value}</div>
				</div>`).join("")}
		</div>
		<div class="row mb-2">
			${list(__("Materials Issued"), a.materials.map((r) => line(esc(r.item_code), `${num(r.qty)} ${esc(r.uom || "")} · ${format_currency(r.amount)}`)))}
			${list(__("Other Costs (labour, hire, services)"), a.other_costs.map((r) => line(esc(r.account), format_currency(r.amount))))}
		</div>
		<div class="small text-muted">
			${__("Daily reports")}:
			${a.reports.slice(0, 15).map((r) => `<a href="/app/bf-site-daily-report/${encodeURIComponent(r.name)}">${date(r.date)}</a>`).join(" · ")}
			${a.reports.length > 15 ? ` · ${__("and {0} more", [a.reports.length - 15])}` : ""}
		</div>`;
}
