# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from consms.construction_management.ipc import validate_template


class BFCertificateTemplate(Document):
	def validate(self):
		validate_template(self)
