"""BF Site Mobilization became BF Works Execution, with Mobilization as one Activity Type.

Copy every mobilization (and its task and resource rows) into the new tables as
Activity Type "Mobilization", point comments, versions and attachments at the new
doctype, then drop the old tables.
"""

import frappe

from consms.setup import ensure_activity_types

PARENT = ("BF Site Mobilization", "BF Works Execution", {
	"mobilization_status": "status",
	"mobilization_template": "project_template",
})
CHILDREN = [
	("BF Site Mobilization Item", "BF Works Execution Task", "tasks"),
	("BF Mobilization Resource", "BF Works Execution Resource", "resources"),
]
REFERENCES = [
	("Version", "ref_doctype"),
	("Comment", "reference_doctype"),
	("Communication", "reference_doctype"),
	("File", "attached_to_doctype"),
	("ToDo", "reference_type"),
	("DocShare", "share_doctype"),
]


def execute():
	old, new, renamed = PARENT
	if not frappe.db.table_exists(old):
		return

	ensure_activity_types()
	mobilization = frappe.db.get_value("BF Activity Type", {"is_mobilization": 1}, "name")

	copy_rows(old, new, renamed, extra={"activity_type": mobilization})
	for old_child, new_child, parentfield in CHILDREN:
		if frappe.db.table_exists(old_child):
			copy_rows(old_child, new_child, extra={"parenttype": new, "parentfield": parentfield})

	for doctype, field in REFERENCES:
		frappe.db.sql(f"update `tab{doctype}` set `{field}` = %s where `{field}` = %s", (new, old))

	for doctype in [old] + [c[0] for c in CHILDREN]:
		if frappe.db.table_exists(doctype):
			frappe.db.sql_ddl(f"drop table `tab{doctype}`")
		frappe.db.delete("DocType", {"name": doctype})

	frappe.delete_doc_if_exists("Number Card", "Mobilizations in Progress")


def copy_rows(old, new, renamed=None, extra=None):
	"""insert ... select the columns both tables share, renaming and setting some on the way."""
	renamed, extra = renamed or {}, extra or {}
	old_columns = set(frappe.db.get_table_columns(old))
	new_columns = set(frappe.db.get_table_columns(new))

	targets, sources, values = [], [], []
	for column in old_columns:
		target = renamed.get(column, column)
		if target in new_columns and target not in extra:
			targets.append(f"`{target}`")
			sources.append(f"`{column}`")
	for column, value in extra.items():
		targets.append(f"`{column}`")
		sources.append("%s")
		values.append(value)

	frappe.db.sql(
		f"""insert into `tab{new}` ({", ".join(targets)})
		select {", ".join(sources)} from `tab{old}`
		where name not in (select name from `tab{new}`)""",
		values,
	)
