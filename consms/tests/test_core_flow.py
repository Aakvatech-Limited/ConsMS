"""The money path of ConsMS, end to end: Tender -> BOQ -> Contract -> Measurement -> IPC -> Sales Invoice.

Everything a test creates is rolled back when the test class ends (FrappeTestCase).
Run with: bench --site <site> run-tests --module consms.tests.test_core_flow --skip-test-records
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, today

from consms.construction_management.certificate_templates import ensure_certificate_templates
from consms.construction_management.doctype.bf_progress_claim.bf_progress_claim import (
	fetch_measurements,
	make_sales_invoice,
)
from consms.construction_management.doctype.bf_tender.bf_tender import make_bf_contract
from consms.construction_management.ipc import LineHolder, build_lines, money, run_lines

SEUWASA = "Ministry of Water (SEUWASA)"


class TestCertificateEngine(FrappeTestCase):
	"""The certificate template reproduces the client's own Excel certificate."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_certificate_templates()

	def test_money_rounds_half_up_like_excel(self):
		self.assertEqual(money(116334289.925), 116334289.93)
		self.assertEqual(money(66464490.09775), 66464490.10)

	def test_seuwasa_ipc_02(self):
		# IPC No. 02 Seuwasa: work 1,329,289,801.955 of which 8,875,000 is P&G (no VAT)
		lines = LineHolder()
		build_lines(lines, "certificate_lines", SEUWASA, "Interim")
		bases = {
			"Work This Certificate": money(1329289801.955),
			"Work This Certificate (excl. VAT-Exempt)": money(1320414801.955),
		}
		total, roles = run_lines(lines.get("certificate_lines"), bases, contract_value=13742895491.14, advance=2748579098.23)

		self.assertEqual(roles["Retention"], 66464490.10)
		self.assertEqual(roles["Advance Recovery"], 265857960.39)
		self.assertEqual(roles["VAT"], 237674664.35)
		self.assertEqual(total, 1234642015.82)  # amount due on the signed certificate

	def test_retention_stops_at_its_limit(self):
		# 5% retention may not pass 5% of the contract value in total
		lines = LineHolder()
		build_lines(lines, "certificate_lines", SEUWASA, "Interim")
		_total, roles = run_lines(
			lines.get("certificate_lines"),
			{"Work This Certificate": 1_000_000, "Work This Certificate (excl. VAT-Exempt)": 1_000_000},
			previous_by_role={"Retention": 48_000},
			contract_value=1_000_000,
			advance=0,
		)
		self.assertEqual(roles["Retention"], 2_000)  # 50,000 limit less 48,000 already held
		self.assertEqual(roles["Advance Recovery"], 0)  # no advance paid, nothing to recover


class TestCoreFlow(FrappeTestCase):
	"""Real documents through the whole flow, with figures small enough to check by hand.

	BOQ 89,200,000: P&G 10,000,000 (no VAT), excavation 1,000 m3 x 9,200, concrete 200 m3 x 350,000.
	Certificate template SEUWASA: retention 5%, advance recovery 20%, VAT 18% excluding P&G.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_certificate_templates()
		cls.company = frappe.db.get_value("Company", {}, "name")
		cls.project = frappe.get_doc(
			{"doctype": "Project", "project_name": "ConsMS core flow test", "company": cls.company}
		).insert()
		cls.customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "ConsMS Test Client", "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
			 "territory": frappe.db.get_value("Territory", {"is_group": 0})}
		).insert()

		cls.tender = frappe.get_doc(
			{"doctype": "BF Tender", "tender_no": "TEST/CORE/001", "tender_name": "Core flow test", "project": cls.project.name}
		).insert()

		cls.boq = frappe.get_doc({
			"doctype": "BF Bill of Quantities",
			"project": cls.project.name,
			"tender": cls.tender.name,
			"summary_template": None,
			"items": [
				{"item_no": "1.1", "bill": "Bill 1: Preliminaries", "description": "Preliminaries and general", "uom": "Nos",
				 "erp_uom": "Nos", "quantity": 1, "unit_rate": 10_000_000, "vat_exempt": 1},
				{"item_no": "2.1", "bill": "Bill 2: Earthworks", "description": "Excavation", "uom": "Cubic Meter",
				 "erp_uom": "Cubic Meter", "quantity": 1000, "unit_rate": 9_200},
				{"item_no": "2.2", "bill": "Bill 2: Earthworks", "description": "Concrete C25", "uom": "Cubic Meter",
				 "erp_uom": "Cubic Meter", "quantity": 200, "unit_rate": 350_000},
			],
		}).insert()
		cls.boq.submit()
		cls.items = {row.item_no: row.name for row in cls.boq.items}

		contract = make_bf_contract(cls.tender.name)
		contract.update({
			"customer": cls.customer.name,
			"boq": cls.boq.name,
			"contingency_percentage": 0,
			"advance_payment_percentage": 20,
			"certificate_template": SEUWASA,
			"start_date": add_days(today(), -60),
			"original_completion_date": add_days(today(), 300),
		})
		contract.insert()
		contract.submit()
		cls.contract = contract

	def measure(self, quantities, date=None):
		log = frappe.get_doc({
			"doctype": "BF Site Measurement Log",
			"contract": self.contract.name,
			"project": self.project.name,
			"boq": self.boq.name,
			"date": date or today(),
			"location_grid": "Test site",
			"measurements": [
				{"boq_item": self.items[item_no], "total_quantity": qty, "drawing": "/files/test-proof.pdf"}
				for item_no, qty in quantities.items()
			],
		}).insert()
		log.submit()
		return log

	def make_claim(self, title, period_from, period_to):
		claim = frappe.get_doc({
			"doctype": "BF Progress Claim",
			"contract": self.contract.name,
			"project": self.project.name,
			"claim_title": title,
			"period_from": period_from,
			"period_to": period_to,
		}).insert()
		fetch_measurements(claim.name, self.contract.name, period_from, period_to)
		return frappe.get_doc("BF Progress Claim", claim.name)

	def test_1_contract_takes_its_value_from_the_boq(self):
		self.assertEqual(flt(self.contract.contract_amount), 89_200_000)
		self.assertEqual(flt(self.contract.advance_payment_amount), 17_840_000)
		self.assertEqual(self.contract.tender, "TEST/CORE/001")

	def test_2_first_ipc_and_invoice(self):
		self.measure({"1.1": 0.5, "2.1": 500, "2.2": 50}, date=add_days(today(), -20))
		claim = self.make_claim("IPC 01", add_days(today(), -30), add_days(today(), -15))

		self.assertEqual(claim.this_period_work, 27_100_000)
		self.assertEqual(claim.retention_deduction, 1_355_000)
		self.assertEqual(claim.advance_payment_recovery, 5_420_000)
		self.assertEqual(claim.vat_amount, 3_978_000)  # 18% of 22,100,000: P&G has no VAT
		self.assertEqual(claim.amount_due, 24_303_000)
		self.assertEqual(claim.net_amount_due, 20_325_000)
		claim.submit()

		self.contract.reload()
		self.assertEqual(flt(self.contract.advance_recovered), 5_420_000)

		if not frappe.get_all("Sales Taxes and Charges Template", filters={"company": self.company, "disabled": 0}, limit=1):
			self.skipTest("The company has no sales tax template, so the invoice VAT cannot be checked.")
		invoice = make_sales_invoice(claim.name)
		self.assertEqual(invoice.bf_progress_claim, claim.name)
		self.assertEqual(flt(invoice.net_total), 20_325_000)
		self.assertEqual(flt(invoice.total_taxes_and_charges), 3_978_000)
		self.assertEqual(flt(invoice.grand_total), 24_303_000)  # the invoice equals the certificate

	def test_3_second_ipc_counts_the_first(self):
		self.measure({"2.2": 50}, date=add_days(today(), -5))
		claim = self.make_claim("IPC 02", add_days(today(), -14), today())

		concrete = next(row for row in claim.claim_items if row.item_no == "2.2")
		self.assertEqual(flt(concrete.previous_qty), 50)
		self.assertEqual(flt(concrete.this_period_qty), 50)
		self.assertEqual(claim.this_period_work, 17_500_000)
		self.assertEqual(claim.previous_certified_amount, 20_325_000)
		self.assertEqual(claim.amount_due, 17_500_000 - 875_000 - 3_500_000 + 3_150_000)

	def test_4_measuring_more_than_the_boq_is_blocked(self):
		# 1,000 m3 in the BOQ; 500 already measured
		with self.assertRaises(frappe.ValidationError):
			self.measure({"2.1": 600})
