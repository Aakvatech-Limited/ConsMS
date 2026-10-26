"""Task becomes an accounting dimension; ConsMS no longer records workers or machines.

Labour gangs, fundis and hired machines are Suppliers paid by Purchase Invoice with the project and
task, so the daily report and Works Execution drop their labour and machine tables. Stock issues move
from the ConsMS field bf_task to the dimension's task field.
"""

import frappe

from consms.setup import ensure_task_dimension

REMOVED = ["BF Daily Labour", "BF Daily Plant", "BF Works Execution Resource"]


def execute():
	ensure_task_dimension()

	if frappe.db.has_column("Stock Entry Detail", "bf_task"):
		frappe.db.sql("update `tabStock Entry Detail` set task = bf_task where ifnull(bf_task, '') != '' and ifnull(task, '') = ''")
		# where an issue had one task only, its header and its books carry the task too
		single_task = """
			select parent, max(bf_task) as task from `tabStock Entry Detail`
			where ifnull(bf_task, '') != '' group by parent having count(distinct bf_task) = 1"""
		frappe.db.sql(f"""update `tabStock Entry` se join ({single_task}) issue on issue.parent = se.name
			set se.task = issue.task where ifnull(se.task, '') = ''""")
		frappe.db.sql(f"""update `tabGL Entry` gle join ({single_task}) issue on issue.parent = gle.voucher_no
			set gle.task = issue.task where gle.voucher_type = 'Stock Entry' and ifnull(gle.task, '') = ''""")
	for name in frappe.get_all("Custom Field", filters={"dt": "Stock Entry Detail", "fieldname": "bf_task"}, pluck="name"):
		frappe.delete_doc("Custom Field", name, force=True)

	for doctype in REMOVED:
		frappe.delete_doc_if_exists("DocType", doctype, force=True)
		if frappe.db.table_exists(doctype):
			frappe.db.sql_ddl(f"drop table `tab{doctype}`")
