"""Interest lines on payment certificate templates get the Late Payment Interest role, so the
system can suggest the interest owed on earlier certificates paid late."""

import frappe


def execute():
	templates = frappe.get_all("BF Certificate Template", filters={"used_for": "Payment Certificate"}, pluck="name")
	drafts = frappe.get_all("BF Progress Claim", filters={"docstatus": 0}, pluck="name")
	for doctype, parents in (("BF Certificate Template Line", templates), ("BF Certificate Line", drafts)):
		if not parents:
			continue
		frappe.db.sql(
			f"""update `tab{doctype}` set role = 'Late Payment Interest'
			where parent in %(parents)s and ifnull(role, '') = '' and calculation = 'Typed Amount'
				and line_type = 'Add' and lower(label) like '%%interest%%'""",
			{"parents": parents},
		)
