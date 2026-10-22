# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, formatdate, today

LETTER_FORMAT = "Extension of Time Request"
RESPONSE_DAYS = 28  # reply due on the request letter's correspondence; the user can change it there


class BFExtensionofTime(Document):
	def before_insert(self):
		self.status = "Draft"
		self.days_approved = 0

	def validate(self):
		if cint(self.days_requested) <= 0:
			frappe.throw(_("Days Requested must be more than zero."))
		if frappe.db.get_value("BF Contract", self.contract, "docstatus") != 1:
			frappe.throw(_("Extensions of Time can only be requested on a submitted contract."))

	def on_submit(self):
		self.db_set("status", "Requested")

	def on_cancel(self):
		update_contract_extensions(self.contract)


@frappe.whitelist()
def set_decision(name, decision, days_approved=None, decision_date=None, reference=None, remarks=None, letter=None):
	"""Approve (fully or partly) or reject a submitted extension request, with the client's letter."""
	eot = frappe.get_doc("BF Extension of Time", name)
	eot.check_permission("submit")
	if eot.docstatus != 1 or eot.status != "Requested":
		frappe.throw(_("Only a submitted request with status Requested can be decided."))
	if decision not in ("Approved", "Rejected"):
		frappe.throw(_("Decision must be Approved or Rejected."))

	days = cint(days_approved) if decision == "Approved" else 0
	if decision == "Approved" and not 0 < days <= cint(eot.days_requested):
		frappe.throw(_("Days Approved must be between 1 and the {0} days requested.").format(eot.days_requested))
	if decision == "Approved" and not letter:
		frappe.throw(_("Attach the approval letter."))

	eot.update({
		"status": decision,
		"days_approved": days,
		"decision_date": decision_date or today(),
		"decision_reference": reference,
		"decision_remarks": remarks,
	})
	if letter:
		record_decision_letter(eot, letter)
	eot.save(ignore_permissions=True)
	eot.add_comment("Info", _("{0}: {1} of {2} days").format(decision, days, eot.days_requested))
	update_contract_extensions(eot.contract)
	return decision


def record_decision_letter(eot, letter):
	"""The client's letter: an incoming correspondence that answers the request, and a row in Documents."""
	contract = frappe.db.get_value("BF Contract", eot.contract, ["customer", "consultant"], as_dict=True)
	correspondence = frappe.get_doc({
		"doctype": "BF Correspondence",
		"direction": "Incoming",
		"correspondence_type": "Letter",
		"date": eot.decision_date,
		"reference_no": eot.decision_reference,
		"party_type": "Consultant / Engineer" if contract.consultant else "Client",
		"from_party": contract.consultant or contract.customer,
		"project": eot.project,
		"contract": eot.contract,
		"subject": _("Extension of Time {0}: {1}").format(eot.name, _(eot.status)),
		"details": eot.decision_remarks,
		"attachment": letter,
		"reply_to": get_request_correspondence(eot),
	}).insert(ignore_permissions=True)
	eot.append("documents", {
		"document_type": "Approval Letter" if eot.status == "Approved" else "Rejection Letter",
		"document_date": eot.decision_date,
		"reference": eot.decision_reference or correspondence.name,
		"attachment": letter,
	})


def get_request_correspondence(eot):
	"""The outgoing correspondence made when the request was emailed."""
	for row in eot.documents:
		if row.document_type == "Request Letter" and frappe.db.exists("BF Correspondence", row.reference):
			return row.reference


@frappe.whitelist()
def get_eot_request(name, reminder=0):
	"""Email details for sending the request (or a reminder): the request letter as PDF and the supporting files."""
	eot = frappe.get_doc("BF Extension of Time", name)
	eot.check_permission("read")
	if eot.docstatus != 1 or eot.status != "Requested":
		frappe.throw(_("Only a submitted request with status Requested can be sent."))

	contract = frappe.db.get_value("BF Contract", eot.contract, ["customer", "consultant_email"], as_dict=True)
	customer_email = frappe.db.get_value("Customer", contract.customer, "email_id") if contract.customer else None
	recipients = [email for email in (contract.consultant_email, customer_email) if email]

	letter = get_or_create_letter_pdf(eot)
	urls = [eot.attachment] + [row.attachment for row in eot.documents if row.document_type != "Request Letter"]
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "BF Extension of Time", "attached_to_name": eot.name, "file_url": ["in", [u for u in urls if u] or [""]]},
		fields=["name", "file_name", "file_url"],
	)
	if eot.correspondence and eot.correspondence != get_request_correspondence(eot):
		files += frappe.get_all(
			"File",
			filters={"attached_to_doctype": "BF Correspondence", "attached_to_name": eot.correspondence},
			fields=["name", "file_name", "file_url"],
		)
	files = list({f.file_url: f for f in files}.values())
	if letter:
		files.insert(0, {"name": letter.name, "file_name": letter.file_name, "file_url": letter.file_url})

	subject = _("Request for Extension of Time: Contract {0} ({1})").format(eot.contract, eot.name)
	if cint(reminder):
		subject = _("Reminder: {0}").format(subject)
		message = _("Dear Sir/Madam,<br><br>We refer to our request for an extension of time of <b>{0} days</b> on contract <b>{1}</b>, sent on {2}, and kindly ask for your decision. The letter is attached again.<br><br>Kind regards,").format(
			eot.days_requested, eot.contract, formatdate(get_request_date(eot)))
	else:
		message = get_request_message(eot)
	return {
		"files": files,
		"recipients": ", ".join(recipients),
		"subject": subject,
		"message": message,
		"warnings": [] if letter else [_("The request letter PDF could not be generated; attach it manually.")],
	}


def get_request_message(eot):
	contract = frappe.db.get_value("BF Contract", eot.contract, ["original_completion_date", "revised_completion_date"], as_dict=True)
	current_end = contract.revised_completion_date or contract.original_completion_date
	facts = [
		(_("Original completion date"), formatdate(contract.original_completion_date)),
		(_("Current completion date"), formatdate(current_end)),
		(_("Extension requested"), _("{0} days").format(eot.days_requested)),
		(_("Requested completion date"), formatdate(add_days(current_end, eot.days_requested)) if current_end else "-"),
	]
	return _("Dear Sir/Madam,<br><br>Please find attached our request for an extension of time on contract <b>{0}</b>, with the supporting documents.<br><br>{1}<br><b>Reason:</b>&nbsp;{2}<br>Kind regards,").format(
		eot.contract, "<br>".join(f"{label}: <b>{value}</b>" for label, value in facts), eot.reason or "")


def get_request_date(eot):
	return next((row.document_date for row in eot.documents if row.document_type == "Request Letter"), eot.request_date)


def get_or_create_letter_pdf(eot):
	"""One request letter PDF per extension; it is made again until the request is first sent."""
	existing = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "BF Extension of Time", "attached_to_name": eot.name, "file_name": ["like", f"EOT Request {eot.name}%.pdf"]},
		pluck="name",
		order_by="creation asc",
	)
	if existing and get_request_correspondence(eot):
		return frappe.get_doc("File", existing[0])
	for old in existing:
		frappe.delete_doc("File", old, ignore_permissions=True)

	try:
		pdf = frappe.get_print("BF Extension of Time", eot.name, print_format=LETTER_FORMAT, as_pdf=True)
		return frappe.get_doc({
			"doctype": "File",
			"file_name": f"EOT Request {eot.name}.pdf",
			"content": pdf,
			"attached_to_doctype": "BF Extension of Time",
			"attached_to_name": eot.name,
			"is_private": 1,
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title=f"EOT request letter for {eot.name}")
		return None


def record_sent_request(communication, method=None):
	"""An email sent from an extension of time: the first one is the request, later ones are reminders."""
	if communication.reference_doctype != "BF Extension of Time" or communication.sent_or_received != "Sent":
		return
	eot = frappe.get_doc("BF Extension of Time", communication.reference_name)
	if eot.docstatus != 1 or eot.status != "Requested":
		return
	if get_request_correspondence(eot):
		eot.add_comment("Info", _("Reminder sent to {0}").format(communication.recipients))
		return

	contract = frappe.db.get_value("BF Contract", eot.contract, ["customer", "consultant"], as_dict=True)
	letter = frappe.db.get_value(
		"File", {"attached_to_doctype": "BF Extension of Time", "attached_to_name": eot.name, "file_name": f"EOT Request {eot.name}.pdf"}, "file_url"
	)
	correspondence = frappe.get_doc({
		"doctype": "BF Correspondence",
		"direction": "Outgoing",
		"correspondence_type": "Email",
		"date": today(),
		"reference_no": eot.reference_no or eot.name,
		"party_type": "Consultant / Engineer" if contract.consultant else "Client",
		"to_party": contract.consultant or contract.customer,
		"from_party": frappe.db.get_value("Project", eot.project, "company") if eot.project else None,
		"project": eot.project,
		"contract": eot.contract,
		"subject": communication.subject,
		"details": communication.content,
		"attachment": letter,
		"response_required": 1,
		"response_due_date": add_days(today(), RESPONSE_DAYS),
	}).insert(ignore_permissions=True)

	if not eot.correspondence:
		eot.correspondence = correspondence.name
	eot.append("documents", {
		"document_type": "Request Letter",
		"document_date": today(),
		"reference": correspondence.name,
		"attachment": letter,
	})
	eot.save(ignore_permissions=True)


def update_contract_extensions(contract_name):
	"""Contract revised completion = original completion + days approved on approved extensions."""
	contract = frappe.get_doc("BF Contract", contract_name)
	contract.calculate_period()
	contract.db_set({
		"approved_extension_days": contract.approved_extension_days,
		"revised_completion_date": contract.revised_completion_date,
	})
	contract.sync_project_dates()
