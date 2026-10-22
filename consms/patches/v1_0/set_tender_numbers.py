"""Tenders are now named by their Tender No.: existing tenders keep their name as their number."""

import frappe


def execute():
	frappe.db.sql("update `tabBF Tender` set tender_no = name where ifnull(tender_no, '') = ''")
