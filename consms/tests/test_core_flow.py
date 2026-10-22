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
	make_purchase_invoice,
	make_sales_invoice,
)
from consms.construction_management.doctype.bf_tender.bf_tender import make_bf_contract
from consms.construction_management.ipc import LineHolder, build_lines, money, run_lines

SEUWASA = "Ministry of Water (SEUWASA)"


def make_item(item_code, stock):
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc({
			"doctype": "Item", "item_code": item_code, "item_group": frappe.db.get_value("Item Group", {"is_group": 0}),
			"stock_uom": "Nos", "is_stock_item": int(stock),
		}).insert()
	return item_code


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

	def measure(self, quantities, date=None, contract=None):
		log = frappe.get_doc({
			"doctype": "BF Site Measurement Log",
			"contract": contract or self.contract.name,
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

	def make_claim(self, title, period_from, period_to, contract=None, claim_type="Client Claim"):
		contract = contract or self.contract.name
		claim = frappe.get_doc({
			"doctype": "BF Progress Claim",
			"contract": contract,
			"claim_type": claim_type,
			"project": self.project.name,
			"claim_title": title,
			"period_from": period_from,
			"period_to": period_to,
		}).insert()
		fetch_measurements(claim.name, contract, period_from, period_to)
		return frappe.get_doc("BF Progress Claim", claim.name)

	def test_1_contract_takes_its_value_from_the_boq(self):
		self.assertEqual(flt(self.contract.contract_amount), 89_200_000)
		self.assertEqual(flt(self.contract.advance_payment_amount), 17_840_000)
		self.assertEqual(self.contract.tender, "TEST/CORE/001")
		self.assertEqual(self.contract.name, "TEST/CORE/001")  # named by its Contract No., taken from the Tender No.

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

	def test_6_site_daily_report_puts_materials_in_the_books_per_task(self):
		from consms.construction_management.progress import get_actual_cost

		task = frappe.get_doc({"doctype": "Task", "subject": "Concrete lining", "project": self.project.name}).insert()
		mason = make_item("ConsMS Test Mason", stock=False)
		mixer = make_item("ConsMS Test Mixer Hire", stock=False)
		cement = make_item("ConsMS Test Cement", stock=True)
		store = self.contract.site_warehouse
		receipt = frappe.get_doc({
			"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": self.company,
			"items": [{"item_code": cement, "qty": 100, "t_warehouse": store, "basic_rate": 20_000}],
		}).insert()
		receipt.submit()

		def report(with_task):
			return frappe.get_doc({
				"doctype": "BF Site Daily Report",
				"contract": self.contract.name,
				"project": self.project.name,
				"boq": self.boq.name,
				"date": today(),
				"source_warehouse": store,
				"labour": [{"task": task.name if with_task else None, "item_code": mason, "headcount": 6, "days": 1}],
				"plant": [{"task": task.name if with_task else None, "item_code": mixer, "hours": 5}],
				"materials": [{"task": task.name if with_task else None, "item_code": cement, "qty": 10, "boq_item": self.items["2.2"]}],
			})

		# the project has tasks, so every row must say which task it belongs to
		with self.assertRaises(frappe.ValidationError):
			report(with_task=False).insert()

		daily = report(with_task=True).insert()
		self.assertEqual((daily.total_headcount, daily.man_days, daily.machines_on_site), (6, 6, 1))
		daily.submit()

		issue = frappe.get_doc("Stock Entry", daily.reload().stock_entry)
		self.assertEqual(issue.items[0].bf_task, task.name)
		self.assertEqual(issue.items[0].bf_boq_item, self.items["2.2"])
		self.assertEqual(flt(issue.items[0].amount), 200_000)  # 10 bags at stock value 20,000

		# Running Cost vs Budget: concrete's actual cost is the stock issue, and the total is the books' total
		cost = get_actual_cost(self.contract.name)
		self.assertEqual(cost[self.items["2.2"]], 200_000)
		booked = frappe.db.sql(
			"""select sum(gle.debit - gle.credit) from `tabGL Entry` gle join `tabAccount` a on a.name = gle.account
			where gle.project = %s and gle.is_cancelled = 0 and a.root_type = 'Expense'""",
			self.project.name,
		)[0][0]
		self.assertEqual(round(sum(cost.values()), 2), round(flt(booked), 2))

	def test_5_subcontractor_ipc_becomes_a_purchase_invoice(self):
		supplier = frappe.get_doc({
			"doctype": "Supplier", "supplier_name": "ConsMS Test Subcontractor",
			"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}),
		}).insert()
		subcontract = frappe.get_doc({
			"doctype": "BF Contract",
			"contract_no": "TEST/CORE/SUB-01",
			"tender": self.tender.name,
			"contract_type": "Subcontract",
			"main_contract": self.contract.name,
			"supplier": supplier.name,
			"project": self.project.name,
			"boq": self.boq.name,
			"contingency_percentage": 0,
			"certificate_template": SEUWASA,
		}).insert()
		subcontract.submit()

		self.measure({"2.2": 10}, date=add_days(today(), -3), contract=subcontract.name)
		claim = self.make_claim("Sub IPC 01", add_days(today(), -10), today(), subcontract.name, "Subcontractor Claim")
		self.assertEqual(claim.amount_due, 3_500_000 - 175_000 + 630_000)  # no advance on this subcontract
		claim.submit()

		if not frappe.get_all("Purchase Taxes and Charges Template", filters={"company": self.company, "disabled": 0}, limit=1):
			self.skipTest("The company has no purchase tax template, so the invoice VAT cannot be checked.")
		invoice = make_purchase_invoice(claim.name)
		self.assertEqual(invoice.bf_contract, subcontract.name)
		self.assertEqual(invoice.bf_progress_claim, claim.name)
		self.assertEqual(flt(invoice.grand_total), 3_955_000)
