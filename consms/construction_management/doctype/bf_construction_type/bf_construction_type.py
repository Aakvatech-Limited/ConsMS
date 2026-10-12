# Copyright (c) 2026, Sydney Kibanga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BFConstructionType(Document):
	def validate(self):
		if self.measurement_method == "Custom" and self.custom_method not in frappe.get_hooks(
			"consms_measurement_methods"
		):
			frappe.throw(
				_("No app provides the measurement method {0}. Add it under consms_measurement_methods in hooks.py.").format(
					frappe.bold(self.custom_method)
				)
			)
