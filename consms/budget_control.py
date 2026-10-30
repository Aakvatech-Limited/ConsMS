"""Budget control on buying.

Money: a Purchase Order may not take a BOQ line beyond its budget amount (Materials + Labour +
Machines + Other on the submitted budget). The order is added to the other submitted orders of
the line, before taxes.

Quantity: a Material Request or Purchase Order may not take more of a recipe material than is left
on its budget line. Material Requests are measured against what other submitted requests have
asked for; Purchase Orders against what other submitted orders have ordered, so a PO made from a
request is not counted twice.

What happens is set in BF Construction Settings: Warn, Stop, or Stop unless approved by a role.
On save it only warns, so drafts can always be kept; the rule applies on submit.
"""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money

WARN, STOP, APPROVAL = "Warn", "Stop", "Stop unless approved"

def measured_against(doctype):
	"""(child table, document, word) a document is measured against: its own kind, submitted, other than itself."""
	return {
		"Material Request": ("Material Request Item", "Material Request", _("requested")),
		"Purchase Order": ("Purchase Order Item", "Purchase Order", _("ordered")),
	}[doctype]


def get_over_budget(doc):
	"""Budget lines this document takes beyond what is left on them."""
	asked = {}
	for row in doc.items:
		if row.get("bf_budget_item"):
			asked[row.bf_budget_item] = asked.get(row.bf_budget_item, 0) + flt(row.stock_qty)
	if not asked:
		return []

	child, parent, _verb = measured_against(doc.doctype)
	used = dict(frappe.db.sql(
		f"""
		select row.bf_budget_item, sum(row.stock_qty)
		from `tab{child}` row
		join `tab{parent}` doc on doc.name = row.parent
		where row.bf_budget_item in %(lines)s and doc.docstatus = 1 and doc.name != %(name)s
		group by row.bf_budget_item
		""",
		{"lines": list(asked), "name": doc.name or ""},
	))

	over = []
	for line in frappe.get_all(
		"BF Budget Item",
		filters={"name": ["in", list(asked)]},
		fields=["name", "parent", "item_code", "boq_description", "qty", "uom"],
	):
		left = flt(line.qty) - flt(used.get(line.name))
		if asked[line.name] > left + 1e-9:
			over.append(frappe._dict(line, asked=asked[line.name], used=flt(used.get(line.name)), left=left))
	return over


def get_over_budget_amount(doc):
	"""BOQ lines a Purchase Order takes beyond their budget amount, with what other orders already took."""
	if doc.doctype != "Purchase Order":
		return []
	asked = {}
	for row in doc.items:
		if row.get("bf_boq_item"):
			asked[row.bf_boq_item] = asked.get(row.bf_boq_item, 0) + flt(row.base_net_amount)
	if not asked:
		return []

	values = {"lines": list(asked), "name": doc.name or ""}
	budgets = frappe.db.sql(
		"""
		select line.boq_item, sum(line.budget_cost) as budget, max(line.item_no) as item_no,
			max(line.description) as description, max(budget.name) as budget_name
		from `tabBF Budget BOQ Line` line
		join `tabBF Budget` budget on budget.name = line.parent
		where line.boq_item in %(lines)s and budget.docstatus = 1
		group by line.boq_item
		""",
		values,
		as_dict=True,
	)
	ordered = dict(frappe.db.sql(
		"""
		select row.bf_boq_item, sum(row.base_net_amount)
		from `tabPurchase Order Item` row
		join `tabPurchase Order` po on po.name = row.parent
		where row.bf_boq_item in %(lines)s and po.docstatus = 1 and po.name != %(name)s
		group by row.bf_boq_item
		""",
		values,
	))

	over = []
	for line in budgets:
		earlier = flt(ordered.get(line.boq_item))
		total = earlier + asked[line.boq_item]
		if total > flt(line.budget) + 0.005:
			over.append(frappe._dict(line, asked=asked[line.boq_item], earlier=earlier, total=total))
	return over


def over_budget_amount_message(doc, over):
	currency = frappe.get_cached_value("Company", doc.company, "default_currency")
	money = lambda value: fmt_money(value, currency=currency)
	return "<br>".join(
		_("{0} {1}: this order {2} + earlier orders {3} = {4}, but the line budget is {5} ({6} over, budget {7}).").format(
			frappe.bold(o.item_no or ""), (o.description or "")[:80], money(o.asked), money(o.earlier), money(o.total),
			money(o.budget), frappe.bold(money(o.total - flt(o.budget))), o.budget_name)
		for o in over
	)


def over_budget_messages(doc):
	"""Everything this document takes beyond the budget: money per BOQ line, then recipe quantities."""
	messages = []
	over_amount = get_over_budget_amount(doc)
	if over_amount:
		messages.append(over_budget_amount_message(doc, over_amount))
	over_qty = get_over_budget(doc)
	if over_qty:
		messages.append(over_budget_message(doc, over_qty))
	return "<br><br>".join(messages)


def qty(value):
	"""2500.0 -> 2,500; 12.5 -> 12.5"""
	return f"{flt(value, 3):,.3f}".rstrip("0").rstrip(".")


def over_budget_message(doc, over):
	verb = measured_against(doc.doctype)[2]
	return "<br>".join(
		_("{0} for {1}: {2} {3} now, but only {4} left on budget {5} (budget {6}, already {7} {8}).").format(
			frappe.bold(o.item_code), (o.boq_description or "")[:80], qty(o.asked), o.uom or "",
			qty(max(o.left, 0)), o.parent, qty(o.qty), verb, qty(o.used))
		for o in over
	)


def warn(doc, method=None):
	"""On save: show what is over the budget, whatever the setting, so it is seen before submitting."""
	message = over_budget_messages(doc)
	if message:
		action = frappe.db.get_single_value("BF Construction Settings", "over_budget_action") or WARN
		after = {
			WARN: _("You can still submit it."),
			STOP: _("It cannot be submitted until the budget is revised."),
			APPROVAL: _("Only a {0} can submit it.").format(approver_role() or _("budget approver")),
		}[action]
		frappe.msgprint(message + "<br><br>" + after, title=_("More than the budget"), indicator="orange")


def enforce(doc, method=None):
	"""On submit: apply the setting."""
	message = over_budget_messages(doc)
	if not message:
		return
	action = frappe.db.get_single_value("BF Construction Settings", "over_budget_action") or WARN
	if action == WARN:
		return
	role = approver_role()
	if action == APPROVAL and role and role in frappe.get_roles():
		doc.add_comment("Info", _("Submitted over the budget, approved by {0} ({1}): {2}").format(
			frappe.session.user, role, message))
		return
	frappe.throw(
		message + "<br><br>" + (
			_("Revise the budget first, or ask a {0} to submit it.").format(role) if action == APPROVAL and role
			else _("Revise the budget first (Cancel and Amend it with the new quantity).")),
		title=_("Over the budget"),
	)


def approver_role():
	return frappe.db.get_single_value("BF Construction Settings", "over_budget_approver_role")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def boq_line_query(doctype, txt, searchfield, start, page_len, filters):
	"""BOQ lines of the project's submitted BOQs for a purchase row: shown as Item No. and description."""
	conditions, values = "", {"txt": f"%{txt}%", "start": start, "page_len": page_len}
	if filters.get("project"):
		conditions = "and boq.project = %(project)s"
		values["project"] = filters["project"]
	return frappe.db.sql(
		f"""
		select line.name, concat_ws(' - ', line.item_no, left(line.description, 120)), boq.name
		from `tabBF BOQ Item` line
		join `tabBF Bill of Quantities` boq on boq.name = line.parent
		where boq.docstatus = 1 {conditions}
			and (line.item_no like %(txt)s or line.description like %(txt)s or line.bill like %(txt)s)
		order by boq.name, line.idx
		limit %(start)s, %(page_len)s
		""",
		values,
	)
