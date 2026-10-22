"""Contracts are now named by their Contract No.: existing contracts keep their name as their number."""

import frappe


def execute():
	frappe.db.sql("update `tabBF Contract` set contract_no = name where ifnull(contract_no, '') = ''")
