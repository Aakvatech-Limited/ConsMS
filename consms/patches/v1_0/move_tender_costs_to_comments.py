"""Tender costs are now booked in accounting against the tender's Project, not typed on the tender.

Each cost typed on a tender before is kept as a comment on that tender, then the old table is dropped.
"""

import frappe
from frappe import _
from frappe.utils import fmt_money, formatdate

DOCTYPE = "BF Tender Cost"


def execute():
	if frappe.db.table_exists(DOCTYPE):
		for row in frappe.db.sql(f"select * from `tab{DOCTYPE}` order by parent, idx", as_dict=True):
			if not frappe.db.exists("BF Tender", row.parent):
				continue
			details = " · ".join(
				str(value)
				for value in (formatdate(row.date) if row.date else None, row.cost_type, row.description, fmt_money(row.amount))
				if value
			)
			reference = f" ({row.reference_doctype} {row.reference_name})" if row.reference_name else ""
			frappe.get_doc("BF Tender", row.parent).add_comment(
				"Comment",
				_("Tender cost typed before costs moved to accounting: {0}{1}").format(details, reference),
			)
		frappe.db.sql_ddl(f"drop table `tab{DOCTYPE}`")

	frappe.delete_doc_if_exists("DocType", DOCTYPE, force=True)
