"""Correspondence is replaced by Frappe's own tools: emails stay on each document's timeline, letters are
attachments, and follow-ups are ToDos.

Each existing letter's file is attached to its contract (or tender, or project) with a comment saying what
it was, then the doctype and its table are removed.
"""

import frappe
from frappe.utils import strip_html

DOCTYPE = "BF Correspondence"


def execute():
	if frappe.db.table_exists(DOCTYPE):
		for letter in frappe.db.sql(f"select * from `tab{DOCTYPE}`", as_dict=True):
			keep_on_parent(letter)
		frappe.db.set_value("ToDo", {"reference_type": DOCTYPE, "status": "Open"}, "status", "Cancelled")

	frappe.delete_doc_if_exists("DocType", DOCTYPE, force=True)
	if frappe.db.table_exists(DOCTYPE):
		frappe.db.sql_ddl(f"drop table `tab{DOCTYPE}`")
	for link_doctype, field in (("Workspace Link", "link_to"), ("Workspace Shortcut", "link_to"), ("Number Card", "document_type")):
		frappe.db.delete(link_doctype, {field: DOCTYPE})


def keep_on_parent(letter):
	for doctype, name in (("BF Contract", letter.contract), ("BF Tender", letter.tender), ("Project", letter.project)):
		if name and frappe.db.exists(doctype, name):
			break
	else:
		return

	if letter.attachment and not frappe.db.exists("File", {"attached_to_doctype": doctype, "attached_to_name": name, "file_url": letter.attachment}):
		frappe.get_doc({
			"doctype": "File",
			"file_url": letter.attachment,
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"is_private": 1 if letter.attachment.startswith("/private/") else 0,
		}).insert(ignore_permissions=True)

	summary = " - ".join(part for part in (
		f"{letter.direction or ''} {letter.correspondence_type or ''} {letter.reference_no or ''}".strip(),
		str(letter.date or ""),
		letter.subject or "",
		strip_html(letter.details or "")[:500],
	) if part)
	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Comment",
		"reference_doctype": doctype,
		"reference_name": name,
		"content": f"Letter {letter.name}: {summary}",
	}).insert(ignore_permissions=True)
