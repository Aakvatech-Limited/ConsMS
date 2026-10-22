"""Budget control on buying: a Material Request or Purchase Order may not take more of a material
than is left on its budget line.

Material Requests are measured against what other submitted requests have asked for; Purchase
Orders against what other submitted orders have ordered, so a PO made from a request is not
counted twice. What happens is set in BF Construction Settings: Warn, Stop, or Stop unless
approved by a role. On save it only warns, so drafts can always be kept; the rule applies on submit.
"""

import frappe
from frappe import _
from frappe.utils import flt

WARN, STOP, APPROVAL = "Warn", "Stop", "Stop unless approved"

# what each document is measured against: its own kind, submitted, other than itself
USED = {
	"Material Request": ("Material Request Item", "Material Request", _("requested")),
	"Purchase Order": ("Purchase Order Item", "Purchase Order", _("ordered")),
}


def get_over_budget(doc):
	"""Budget lines this document takes beyond what is left on them."""
	asked = {}
	for row in doc.items:
		if row.get("bf_budget_item"):
			asked[row.bf_budget_item] = asked.get(row.bf_budget_item, 0) + flt(row.stock_qty)
	if not asked:
		return []

	child, parent, _verb = USED[doc.doctype]
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


def qty(value):
	"""2500.0 -> 2,500; 12.5 -> 12.5"""
	return f"{flt(value, 3):,.3f}".rstrip("0").rstrip(".")


def over_budget_message(doc, over):
	verb = USED[doc.doctype][2]
	return "<br>".join(
		_("{0} for {1}: {2} {3} now, but only {4} left on budget {5} (budget {6}, already {7} {8}).").format(
			frappe.bold(o.item_code), (o.boq_description or "")[:80], qty(o.asked), o.uom or "",
			qty(max(o.left, 0)), o.parent, qty(o.qty), verb, qty(o.used))
		for o in over
	)


def warn(doc, method=None):
	"""On save: show what is over the budget, whatever the setting, so it is seen before submitting."""
	over = get_over_budget(doc)
	if over:
		action = frappe.db.get_single_value("BF Construction Settings", "over_budget_action") or WARN
		after = {
			WARN: _("You can still submit it."),
			STOP: _("It cannot be submitted until the budget is revised."),
			APPROVAL: _("Only a {0} can submit it.").format(approver_role() or _("budget approver")),
		}[action]
		frappe.msgprint(over_budget_message(doc, over) + "<br><br>" + after,
			title=_("More than the budget quantity"), indicator="orange")


def enforce(doc, method=None):
	"""On submit: apply the setting."""
	over = get_over_budget(doc)
	if not over:
		return
	action = frappe.db.get_single_value("BF Construction Settings", "over_budget_action") or WARN
	if action == WARN:
		return
	role = approver_role()
	if action == APPROVAL and role and role in frappe.get_roles():
		doc.add_comment("Info", _("Submitted over the budget, approved by {0} ({1}): {2}").format(
			frappe.session.user, role, over_budget_message(doc, over)))
		return
	frappe.throw(
		over_budget_message(doc, over) + "<br><br>" + (
			_("Revise the budget first, or ask a {0} to submit it.").format(role) if action == APPROVAL and role
			else _("Revise the budget first (Cancel and Amend it with the new quantity).")),
		title=_("Over the budget"),
	)


def approver_role():
	return frappe.db.get_single_value("BF Construction Settings", "over_budget_approver_role")
