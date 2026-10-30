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
from consms.construction_management.ipc import LineHolder, build_lines, calculate, get_vat, get_vat_summary, money, run_lines

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
		frappe.db.set_single_value("BF Construction Settings", "vat_rate", 18)

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
		# VAT is added by the system from the contract: Standard Rated, on the gross work without P&G
		_base, vat = get_vat(bases["Work This Certificate (excl. VAT-Exempt)"], 0, frappe._dict(vat_status="Standard Rated", vat_basis="Gross Work"))

		self.assertEqual(roles["Retention"], 66464490.10)
		self.assertEqual(roles["Advance Recovery"], 265857960.39)
		self.assertEqual(vat, 237674664.35)
		self.assertEqual(money(total + vat), 1234642015.82)  # amount due on the signed certificate

	def test_vat_follows_the_contract(self):
		net = frappe._dict(vat_status="Standard Rated", vat_basis="Net after Deductions")
		self.assertEqual(get_vat(1_000_000, 300_000, net), (700_000, 126_000))  # 18% after retention and advance
		self.assertEqual(get_vat(1_000_000, 300_000, frappe._dict(vat_status="Exempt")), (0, 0))
		self.assertEqual(get_vat(1_000_000, 300_000, frappe._dict(vat_status="Zero Rated")), (0, 0))

	def test_payment_templates_cannot_define_vat(self):
		template = frappe.get_doc("BF Certificate Template", SEUWASA)
		self.assertFalse([l for l in template.lines if l.role == "VAT"])
		template.append("lines", {"label": "Add: VAT 18%", "line_type": "Add", "calculation": "Percentage", "rate": 18,
			"percentage_of": "Work This Certificate", "role": "VAT"})
		with self.assertRaises(frappe.ValidationError):
			template.save()

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


class TestTenderStage(FrappeTestCase):
	"""Before the award the BOQ can still be corrected: the tender must not hold it."""

	def test_boq_of_a_submitted_tender_can_be_cancelled(self):
		from consms.construction_management.doctype.bf_tender.bf_tender import get_tender_boq

		company = frappe.db.get_value("Company", {}, "name")
		project = frappe.get_doc({"doctype": "Project", "project_name": "ConsMS tender stage test", "company": company}).insert()
		tender = frappe.get_doc(
			{"doctype": "BF Tender", "tender_no": "TEST/TENDER/001", "tender_name": "Tender stage test", "project": project.name}
		).insert()
		boq = frappe.get_doc({
			"doctype": "BF Bill of Quantities", "project": project.name, "tender": tender.name, "summary_template": None,
			"items": [{"item_no": "1", "description": "Excavation", "uom": "Cubic Meter", "erp_uom": "Cubic Meter", "quantity": 10, "unit_rate": 1000}],
		}).insert()
		boq.submit()

		tender.reload()
		for row in tender.documents:
			row.status, row.attachment = "Ready", "/files/test-proof.pdf"
		tender.save()
		tender.submit()  # needs the submitted BOQ, found through the lookup
		self.assertEqual(get_tender_boq(tender.name), boq.name)

		boq.reload()
		boq.cancel()  # used to fail: "linked with BF Tender"
		self.assertIsNone(get_tender_boq(tender.name))


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
		invoice.insert()
		invoice.submit()

		from consms.construction_management.report.vat_on_ipcs.vat_on_ipcs import execute

		row = execute({"contract": self.contract.name})[1][0]
		self.assertEqual((row["work"], row["exempt"], row["taxable"], row["vat"]), (27_100_000, 5_000_000, 22_100_000, 3_978_000))
		self.assertEqual(row["invoice"], invoice.name)

	def test_3_second_ipc_counts_the_first(self):
		self.measure({"2.2": 50}, date=add_days(today(), -5))
		claim = self.make_claim("IPC 02", add_days(today(), -14), today())

		concrete = next(row for row in claim.claim_items if row.item_no == "2.2")
		self.assertEqual(flt(concrete.previous_qty), 50)
		self.assertEqual(flt(concrete.this_period_qty), 50)
		self.assertEqual(claim.this_period_work, 17_500_000)
		self.assertEqual(claim.previous_certified_amount, 20_325_000)
		self.assertEqual(claim.amount_due, 17_500_000 - 875_000 - 3_500_000 + 3_150_000)

		# the VAT summary on the certificate: previous (IPC 01) / this / to date
		rows = {r.label: r for r in get_vat_summary(claim, frappe.get_doc("BF Contract", self.contract.name)).rows}
		self.assertEqual((rows["Work done (all bills)"].previous, rows["Work done (all bills)"].this), (27_100_000, 17_500_000))
		self.assertEqual(rows["Less: VAT-exempt work"].to_date, 5_000_000)  # P&G of IPC 01
		self.assertEqual(rows["VAT 18%"].to_date, 3_978_000 + 3_150_000)
		self.assertEqual(rows["Amount due incl. VAT"].previous, 24_303_000)

		# once IPC 02 is submitted, IPC 01 recalculated still counts only what came before it (nothing)
		claim.submit()
		first = frappe.get_doc("BF Progress Claim", {"contract": self.contract.name, "claim_title": "IPC 01"})
		calculate(first)
		self.assertEqual((first.advance_payment_recovery, first.advance_recovered_to_date), (5_420_000, 5_420_000))
		self.assertEqual(first.amount_due, 24_303_000)
		rows = {r.label: r for r in get_vat_summary(first, frappe.get_doc("BF Contract", self.contract.name)).rows}
		self.assertEqual(rows["Work done (all bills)"].previous, 0)
		claim.cancel()  # later tests measure against IPC 01 only

	def test_4_measuring_more_than_the_boq_is_blocked(self):
		# 1,000 m3 in the BOQ; 500 already measured
		with self.assertRaises(frappe.ValidationError):
			self.measure({"2.1": 600})

	def test_6_materials_and_labour_are_in_the_books_per_task(self):
		from consms.construction_management.progress import get_actual_cost

		task = frappe.get_doc({"doctype": "Task", "subject": "Concrete lining", "project": self.project.name}).insert()
		cement = make_item("ConsMS Test Cement", stock=True)
		store = self.contract.site_warehouse
		receipt = frappe.get_doc({
			"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": self.company,
			"items": [{"item_code": cement, "qty": 100, "t_warehouse": store, "basic_rate": 20_000}],
		}).insert()
		receipt.submit()

		# materials used on the task leave the site store through a Stock Issue with the project and task
		issue = frappe.get_doc({
			"doctype": "Stock Entry", "stock_entry_type": "Material Issue", "company": self.company,
			"project": self.project.name, "task": task.name, "from_warehouse": store,
			"items": [{"item_code": cement, "qty": 10, "s_warehouse": store, "project": self.project.name,
				"task": task.name, "bf_boq_item": self.items["2.2"]}],
		}).insert()
		issue.submit()
		self.assertEqual((issue.task, issue.items[0].task), (task.name, task.name))  # Task is an accounting dimension
		self.assertEqual(flt(issue.items[0].amount), 200_000)  # 10 bags at stock value 20,000

		# a labour gang is a Supplier: its invoice carries the project and the task
		gang = frappe.get_doc({
			"doctype": "Supplier", "supplier_name": "ConsMS Test Masons Gang",
			"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}),
		}).insert()
		invoice = frappe.get_doc({
			"doctype": "Purchase Invoice", "supplier": gang.name, "company": self.company, "project": self.project.name, "task": task.name,
			"items": [{
				"item_code": make_item("ConsMS Test Masonry Labour", stock=False), "qty": 6, "rate": 25_000,
				"project": self.project.name, "task": task.name,
				"expense_account": frappe.db.get_value("Account", {"company": self.company, "root_type": "Expense", "is_group": 0}),
			}],
		}).insert()
		invoice.set("taxes", [])
		invoice.save()
		invoice.submit()

		# Running Cost vs Budget: concrete's actual cost is the stock issue, and the total is the books' total
		cost = get_actual_cost(self.contract.name)
		self.assertEqual(cost[self.items["2.2"]], 200_000)
		booked = frappe.db.sql(
			"""select sum(gle.debit - gle.credit) from `tabGL Entry` gle join `tabAccount` a on a.name = gle.account
			where gle.project = %s and gle.is_cancelled = 0 and a.root_type = 'Expense'""",
			self.project.name,
		)[0][0]
		self.assertEqual(round(sum(cost.values()), 2), round(flt(booked), 2))

	def test_7_task_shows_its_costs(self):
		from frappe.desk.notifications import _get_linked_document_counts

		from consms.construction_management.report.task_activity.task_activity import execute
		from consms.construction_management.task_activity import get_task_site_activity

		# test 6: 10 bags of cement at 20,000 issued to the task, and the masons gang's invoice of 150,000
		task = frappe.db.get_value("Task", {"project": self.project.name, "subject": "Concrete lining"})
		activity = get_task_site_activity(task)
		self.assertEqual((activity["materials_cost"], activity["other_cost"], activity["total_cost"]), (200_000, 150_000, 350_000))

		row = next(r for r in execute({"project": self.project.name})[1] if r["task"] == task)
		self.assertEqual((row["materials_cost"], row["other_cost"], row["total_cost"]), (200_000, 150_000, 350_000))

		# the Task's Connections list the Stock Issue and the supplier invoice charged to it
		counts = {c["doctype"]: c["count"] for c in _get_linked_document_counts("Task", task)["count"]["external_links_found"]}
		self.assertEqual((counts.get("Stock Entry"), counts.get("Purchase Invoice")), (1, 1))

	def test_8_recipe_must_be_in_the_boq_line_unit(self):
		from consms.construction_management.doctype.bf_budget.bf_budget import make_bf_budget

		cement = make_item("ConsMS Test Cement", stock=True)

		def recipe(unit):
			ra = frappe.get_doc({
				"doctype": "BF Rate Analysis", "rate_analysis_name": f"Concrete C25 test per {unit}", "uom": unit,
				"items": [{"resource_type": "Material", "item_code": cement, "qty": 7, "rate": 20_000}],
			}).insert()
			ra.submit()
			return ra.name

		per_km, per_m3 = recipe("Kilometer"), recipe("Cubic Meter")
		budget = make_bf_budget(self.contract.name)
		line = next(l for l in budget.boq_lines if l.boq_item == self.items["2.2"])  # concrete, in m3

		line.rate_analysis = per_km
		with self.assertRaises(frappe.ValidationError):
			budget.insert()  # a per-kilometre recipe on a m3 line is refused

		line.rate_analysis = per_m3
		budget.insert()
		self.assertEqual(budget.get_unit_mismatches(), [])

		from consms.construction_management.progress import get_baseline_cost

		self.assertEqual(get_baseline_cost(self.contract.name), {})  # a draft budget is not a baseline
		self.assertEqual(flt(line.budget_cost), 200 * 7 * 20_000)  # 200 m3 x 7 bags x 20,000

		# a budget that already holds a wrong-unit recipe (saved before this check) is flagged
		frappe.db.set_value("BF Budget BOQ Line", line.name, "rate_analysis", per_km)
		flagged = frappe.get_doc("BF Budget", budget.name).get_unit_mismatches()
		self.assertEqual([(m["boq_unit"], m["recipe_unit"]) for m in flagged], [("Cubic Meter", "Kilometer")])

	def test_9_advance_on_the_contract_sum_incl_vat(self):
		# a second tender of the project, priced with a summary: bills + VAT 18% = the contract sum
		tender = frappe.get_doc(
			{"doctype": "BF Tender", "tender_no": "TEST/CORE/002", "tender_name": "With VAT", "project": self.project.name}
		).insert()
		boq = frappe.get_doc({
			"doctype": "BF Bill of Quantities", "project": self.project.name, "tender": tender.name,
			"summary_template": "Bills + VAT 18%",
			"items": [{"item_no": "1", "description": "Bridge deck", "uom": "Cubic Meter", "erp_uom": "Cubic Meter", "quantity": 100, "unit_rate": 1_000_000}],
		}).insert()
		boq.submit()
		frappe.db.set_value("Project", self.project.name, "construction_type", "Bridge")

		contract = make_bf_contract(tender.name)
		contract.update({"customer": self.customer.name, "advance_payment_percentage": 20, "certificate_template": SEUWASA})
		contract.insert()
		self.assertEqual(flt(contract.contract_amount), 100_000_000)  # without VAT
		self.assertEqual(flt(contract.contract_sum_incl_vat), 118_000_000)
		self.assertEqual(flt(contract.advance_payment_amount), 23_600_000)  # 20% of the sum incl. VAT
		self.assertEqual(contract.construction_type, "Bridge")  # from the project
		contract.submit()

		# after submit, an unrelated edit keeps the advance; changing the % recalculates it
		contract.advance_guarantee_no = "AG-001"
		contract.save()
		self.assertEqual(flt(contract.advance_payment_amount), 23_600_000)
		contract.advance_payment_percentage = 10
		contract.save()
		self.assertEqual(flt(contract.advance_payment_amount), 11_800_000)

	def test_10_eot_request_by_email_and_the_decision_letter(self):
		from consms.construction_management.doctype.bf_extension_of_time.bf_extension_of_time import get_eot_request, set_decision

		self.contract.db_set({"consultant": "Test Engineer Ltd", "consultant_email": "engineer@example.com"})
		eot = frappe.get_doc({
			"doctype": "BF Extension of Time", "contract": self.contract.name, "request_date": today(),
			"days_requested": 30, "reason": "Heavy rains", "reference_no": "TEST/EOT/01",
		}).insert()
		eot.submit()

		request = get_eot_request(eot.name)
		self.assertEqual(request["recipients"], "engineer@example.com")
		self.assertIn(self.contract.name, request["subject"])
		self.assertIn("Heavy rains", request["message"])
		self.assertIn(frappe.utils.formatdate(add_days(today(), 330)), request["message"])  # completion + 30 days
		self.assertEqual(request["files"][0]["file_name"], f"EOT Request {eot.name}.pdf")

		def email(subject):
			# what the email dialog saves; inserting it does not send anything
			frappe.get_doc({
				"doctype": "Communication", "communication_medium": "Email", "sent_or_received": "Sent", "subject": subject,
				"content": "Request", "recipients": request["recipients"],
				"reference_doctype": "BF Extension of Time", "reference_name": eot.name,
			}).insert(ignore_permissions=True)

		# the email stays on the EOT's timeline; the request letter is filed and a follow-up ToDo is set
		email(request["subject"])
		eot.reload()
		self.assertEqual([(row.document_type, row.reference) for row in eot.documents], [("Request Letter", "TEST/EOT/01")])
		follow_up = {"reference_type": "BF Extension of Time", "reference_name": eot.name, "status": "Open"}
		self.assertEqual(str(frappe.db.get_value("ToDo", follow_up, "date")), add_days(today(), 28))
		self.assertEqual(frappe.db.count("Communication", {"reference_doctype": "BF Extension of Time", "reference_name": eot.name}), 1)

		# a reminder is another email on the timeline, not a new request
		email(get_eot_request(eot.name, reminder=1)["subject"])
		eot.reload()
		self.assertEqual([row.document_type for row in eot.documents], ["Request Letter"])
		self.assertEqual(frappe.db.count("ToDo", follow_up), 1)

		with self.assertRaises(frappe.ValidationError):
			set_decision(eot.name, "Approved", days_approved=20)  # no approval letter
		set_decision(eot.name, "Approved", days_approved=20, reference="ENG/EOT/07", letter="/files/test-approval.pdf")
		eot.reload()
		self.assertEqual(eot.status, "Approved")
		self.assertEqual([(row.document_type, row.attachment) for row in eot.documents],
			[("Request Letter", f"/private/files/EOT Request {eot.name}.pdf"), ("Approval Letter", "/files/test-approval.pdf")])
		self.assertFalse(frappe.db.exists("ToDo", follow_up))  # the client answered: follow-up closed
		self.assertEqual(frappe.db.get_value("BF Contract", self.contract.name, "approved_extension_days"), 20)

	def test_9b_late_payment_interest(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		from consms.construction_management.ipc import suggest_late_payment_interest
		from consms.construction_management.report.late_payment_interest.late_payment_interest import execute

		invoice = frappe.db.get_value("Sales Invoice", {"bf_contract": self.contract.name, "docstatus": 1}, "name")
		if not invoice:
			self.skipTest("IPC 01 has no invoice (no sales tax template), so payments cannot be read.")

		# pay within 28 days of certification, 16% a year on late payments
		self.contract.db_set({"payment_period_days": 28, "late_payment_interest_rate": 16, "interest_clause": "Clause 55 of GCC"})
		first = frappe.get_doc("BF Progress Claim", {"contract": self.contract.name, "claim_title": "IPC 01"})
		first.certified_date = add_days(today(), -60)  # certified after it was submitted
		first.save()
		self.assertEqual(str(first.due_date), add_days(today(), -32))

		# 10,000,000 of the 24,303,000 paid today: 32 days late; the rest still unpaid 10 days from now
		payment = get_payment_entry("Sales Invoice", invoice)
		payment.update({"paid_amount": 10_000_000, "received_amount": 10_000_000, "reference_no": "TEST-LATE", "reference_date": today()})
		payment.references[0].allocated_amount = 10_000_000
		payment.insert()
		payment.submit()

		as_at = add_days(today(), 10)
		expected = money(10_000_000 * 0.16 * 32 / 365 + 14_303_000 * 0.16 * 42 / 365)
		row = next(r for r in execute({"contract": self.contract.name, "as_at": as_at})[1] if r.claim == first.name)
		self.assertEqual((row.paid, row.unpaid, row.days_late), (10_000_000, 14_303_000, 42))
		self.assertEqual(row.interest, expected)

		# the next certificate is offered that interest (nothing was claimed before)
		next_claim = frappe._dict(contract=self.contract.name, claim_type="Client Claim", name="", posting_date=as_at, period_to=as_at)
		self.assertEqual(suggest_late_payment_interest(next_claim), expected)

	def test_9c_contract_profitability(self):
		from consms.construction_management.progress import get_actual_cost
		from consms.construction_management.report.contract_profitability.contract_profitability import execute

		row = next(r for r in execute({"project": self.project.name})[1] if r["contract"] == self.contract.name)
		cost = sum(get_actual_cost(self.contract.name).values())
		self.assertEqual(row["contract_value"], 89_200_000)
		self.assertEqual(round(row["cost_to_date"], 2), round(cost, 2))  # every project expense, as in Running Cost vs Budget
		if frappe.db.exists("Sales Invoice", {"bf_contract": self.contract.name, "docstatus": 1}):
			self.assertEqual(row["billed"], 20_325_000)  # IPC 01 without VAT
			self.assertEqual(round(row["profit_to_date"], 2), round(20_325_000 - cost, 2))

	def test_9d_contingency_added_on_the_contract_is_in_the_contract_sum(self):
		# a BOQ priced as bills + VAT 18%, with no contingency in its summary
		tender = frappe.get_doc(
			{"doctype": "BF Tender", "tender_no": "TEST/CORE/004", "tender_name": "Contingency on contract", "project": self.project.name}
		).insert()
		boq = frappe.get_doc({
			"doctype": "BF Bill of Quantities", "project": self.project.name, "tender": tender.name, "summary_template": "Bills + VAT 18%",
			"items": [{"item_no": "1", "description": "Culvert", "uom": "Nos", "erp_uom": "Nos", "quantity": 1, "unit_rate": 100_000_000}],
		}).insert()
		boq.submit()
		contract = make_bf_contract(tender.name)
		contract.update({"customer": self.customer.name, "advance_payment_percentage": 20, "certificate_template": SEUWASA})
		contract.insert()
		self.assertEqual(flt(contract.contract_sum_incl_vat), 118_000_000)  # the bid price

		# 10% contingency added on the contract: it is part of the contract sum, with its VAT
		contract.contingency_percentage = 10
		contract.save()
		self.assertEqual(flt(contract.total_contract_amount), 110_000_000)
		self.assertEqual(flt(contract.contract_sum_incl_vat), 118_000_000 + 11_800_000)
		self.assertEqual(flt(contract.advance_payment_amount), 25_960_000)  # 20% of 129,800,000

		# an exempt contract adds the contingency without VAT
		contract.vat_status = "Exempt"
		contract.save()
		self.assertEqual(flt(contract.contract_sum_incl_vat), 128_000_000)

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

		# the subcontract and its IPC list the invoice under Connections
		from frappe.desk.notifications import _get_linked_document_counts

		invoice.supplier = supplier.name
		invoice.insert()
		for doctype, name in (("BF Contract", subcontract.name), ("BF Progress Claim", claim.name)):
			counts = _get_linked_document_counts(doctype, name)["count"]["external_links_found"]
			self.assertEqual(next(c["count"] for c in counts if c["doctype"] == "Purchase Invoice"), 1, doctype)


class TestBudgetControl(FrappeTestCase):
	"""Budget of 700 bags of cement (100 m3 x 7 bags); Material Requests and Purchase Orders against it."""

	@classmethod
	def setUpClass(cls):
		from consms.construction_management.doctype.bf_budget.bf_budget import make_bf_budget

		super().setUpClass()
		company = frappe.db.get_value("Company", {}, "name")
		project = frappe.get_doc({"doctype": "Project", "project_name": "ConsMS budget control test", "company": company}).insert()
		tender = frappe.get_doc(
			{"doctype": "BF Tender", "tender_no": "TEST/BUDGET/001", "tender_name": "Budget control test", "project": project.name}
		).insert()
		boq = frappe.get_doc({
			"doctype": "BF Bill of Quantities", "project": project.name, "tender": tender.name, "summary_template": None,
			"items": [{"item_no": "1", "description": "Concrete C25", "uom": "Cubic Meter", "erp_uom": "Cubic Meter", "quantity": 100, "unit_rate": 450_000}],
		}).insert()
		boq.submit()
		customer = frappe.db.get_value("Customer", {}, "name")
		contract = make_bf_contract(tender.name)
		contract.update({"customer": customer, "contingency_percentage": 0, "certificate_template": SEUWASA})
		contract.insert()
		contract.submit()

		cls.cement = make_item("ConsMS Test Cement", stock=True)
		recipe = frappe.get_doc({
			"doctype": "BF Rate Analysis", "rate_analysis_name": "Concrete C25 budget control test", "uom": "Cubic Meter",
			"items": [{"resource_type": "Material", "item_code": cls.cement, "qty": 7, "rate": 22_000}],
		}).insert()
		recipe.submit()
		budget = make_bf_budget(contract.name)
		budget.boq_lines[0].rate_analysis = recipe.name
		budget.insert()
		budget.submit()
		cls.budget, cls.contract, cls.project = budget, contract.reload(), project
		cls.line = budget.items[0].name
		cls.supplier = frappe.get_doc({
			"doctype": "Supplier", "supplier_name": "ConsMS Test Cement Supplier",
			"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}),
		}).insert().name

	def setting(self, action, role=None):
		frappe.db.set_single_value("BF Construction Settings", {"over_budget_action": action, "over_budget_approver_role": role})

	def request(self, qty):
		"""A Material Request row on the budget line (typed, since Get Items From only offers what is left)."""
		return frappe.get_doc({
			"doctype": "Material Request", "material_request_type": "Purchase", "schedule_date": today(),
			"company": frappe.db.get_value("Project", self.project.name, "company"),
			"items": [{"item_code": self.cement, "qty": qty, "schedule_date": today(), "project": self.project.name,
				"warehouse": self.contract.site_warehouse, "bf_budget": self.budget.name, "bf_budget_item": self.line,
				"bf_boq": self.budget.boq, "bf_boq_item": self.budget.items[0].boq_item}],
		}).insert()

	def order(self, qty):
		return frappe.get_doc({
			"doctype": "Purchase Order", "supplier": self.supplier, "company": frappe.db.get_value("Project", self.project.name, "company"),
			"project": self.project.name, "schedule_date": today(),
			"items": [{"item_code": self.cement, "qty": qty, "rate": 22_000, "schedule_date": today(), "project": self.project.name,
				"warehouse": self.contract.site_warehouse, "bf_budget": self.budget.name, "bf_budget_item": self.line,
				"bf_boq": self.budget.boq, "bf_boq_item": self.budget.items[0].boq_item}],
		}).insert()

	def test_1_within_the_budget_always_passes(self):
		from consms.construction_management.doctype.bf_budget.bf_budget import get_items_for_material_request

		self.assertEqual(flt(self.budget.items[0].qty), 700)
		self.setting("Stop")
		mr = get_items_for_material_request(self.budget.name)  # Get Items From > Budget offers the 700 left
		self.assertEqual(flt(mr.items[0].qty), 700)
		mr.items[0].qty = 300
		mr.insert().submit()  # 300 of 700

	def test_2_stop_blocks_submit_but_keeps_the_draft(self):
		self.setting("Stop")
		mr = self.request(500)  # 300 already requested: only 400 left; saving the draft is allowed
		with self.assertRaises(frappe.ValidationError):
			mr.submit()

	def test_3_warn_lets_it_through(self):
		self.setting("Warn")
		self.request(500).submit()  # 800 requested of 700, with a warning only

	def test_4_stop_unless_approved(self):
		from consms.budget_control import enforce

		self.setting("Stop unless approved", "Projects Manager")
		mr = self.request(100)  # already 800 of 700

		# someone without the approver role is stopped (Guest: creating a test user would commit the database)
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.ValidationError):
				enforce(mr)
		finally:
			frappe.set_user("Administrator")

		mr.submit()  # the approver can submit; the approval is recorded on the document
		comment = frappe.db.get_value("Comment", {"reference_doctype": "Material Request", "reference_name": mr.name,
			"content": ["like", "Submitted over the budget, approved by Administrator%"]})
		self.assertTrue(comment)

	def test_5_purchase_orders_are_counted_separately(self):
		self.setting("Stop")
		self.order(400).submit()  # requests already passed 700, but nothing has been ordered yet
		with self.assertRaises(frappe.ValidationError):
			self.order(400).submit()  # 800 ordered of 700

	def test_6_open_orders_show_as_committed(self):
		from consms.construction_management.progress import get_committed_cost
		from consms.construction_management.report.running_cost_vs_budget.running_cost_vs_budget import execute

		committed = get_committed_cost(self.contract.name)
		self.assertEqual(committed[self.budget.items[0].boq_item], 400 * 22_000)  # test 5's order, nothing received

		row = next(r for r in execute({"contract": self.contract.name})[1] if r["description"] == "Concrete C25")
		self.assertEqual(row["budget"], 700 * 22_000)
		self.assertEqual(row["committed"], 400 * 22_000)
		self.assertEqual(row["remaining"], 300 * 22_000)

	def test_7_purchase_orders_are_checked_against_the_line_budget_amount(self):
		from consms.budget_control import boq_line_query, enforce, over_budget_messages

		self.setting("Stop")
		boq_line = self.budget.items[0].boq_item

		def order_by_hand(rate):
			"""A row with only the BOQ Line picked (no recipe material): only the money check applies."""
			return frappe.get_doc({
				"doctype": "Purchase Order", "supplier": self.supplier, "company": frappe.db.get_value("Project", self.project.name, "company"),
				"project": self.project.name, "schedule_date": today(),
				"items": [{"item_code": self.cement, "qty": 100, "rate": rate, "schedule_date": today(), "project": self.project.name,
					"warehouse": self.contract.site_warehouse, "bf_boq_item": boq_line}],
			}).insert()

		# budget 15,400,000 (700 bags x 22,000); test 5 ordered 8,800,000
		over = order_by_hand(70_000)  # + 7,000,000 = 15,800,000
		self.assertIn("15,800,000", over_budget_messages(over))
		with self.assertRaises(frappe.ValidationError):
			enforce(over)

		order_by_hand(60_000).submit()  # + 6,000,000 = 14,800,000, within the budget

		# the BOQ Line picker shows the project's lines by Item No. and description
		rows = boq_line_query("BF BOQ Item", "Concrete", "name", 0, 20, {"project": self.project.name})
		self.assertEqual([(r[0], r[1]) for r in rows], [(boq_line, "1 - Concrete C25")])


class TestBudgetAmounts(FrappeTestCase):
	"""A budget typed as amounts per BOQ line, like a costing sheet, with a recipe made from one line."""

	@classmethod
	def setUpClass(cls):
		from consms.construction_management.doctype.bf_budget.bf_budget import make_bf_budget

		super().setUpClass()
		company = frappe.db.get_value("Company", {}, "name")
		project = frappe.get_doc({"doctype": "Project", "project_name": "ConsMS budget amounts test", "company": company}).insert()
		tender = frappe.get_doc(
			{"doctype": "BF Tender", "tender_no": "TEST/BUDGET/002", "tender_name": "Budget amounts test", "project": project.name}
		).insert()
		# stored out of bill order, as some imported BOQs are
		boq = frappe.get_doc({
			"doctype": "BF Bill of Quantities", "project": project.name, "tender": tender.name, "summary_template": None,
			"items": [
				{"item_no": "10.1", "bill": "Bill No. 10 - Concrete", "description": "Concrete C25", "uom": "m3", "erp_uom": "Cubic Meter",
				 "quantity": 200, "unit_rate": 350_000},
				{"item_no": "2.1", "bill": "Bill No. 2 - Earthworks", "description": "Excavation", "uom": "m3", "erp_uom": "Cubic Meter",
				 "quantity": 1000, "unit_rate": 9_200},
				{"item_no": "1.1", "bill": "Bill No. 1 - Preliminaries", "description": "Preliminaries and general", "uom": "Sum",
				 "erp_uom": "Nos", "quantity": 1, "unit_rate": 10_000_000},
			],
		}).insert()
		boq.submit()
		contract = make_bf_contract(tender.name)
		contract.update({"customer": frappe.db.get_value("Customer", {}, "name"), "contingency_percentage": 0, "certificate_template": SEUWASA})
		contract.insert()
		contract.submit()
		cls.contract = contract
		cls.budget = make_bf_budget(contract.name).insert()
		cls.cement = make_item("ConsMS Test Cement", stock=True)

	def line(self, item_no):
		return next(line for line in self.budget.boq_lines if line.item_no == item_no)

	def test_1_lines_in_bill_order(self):
		self.assertEqual([line.item_no for line in self.budget.boq_lines], ["1.1", "2.1", "10.1"])

	def test_2_amounts_typed_for_the_whole_line(self):
		self.line("1.1").other_amount = 8_000_000  # P&G as a lump sum
		self.line("2.1").update({"labour_amount": 4_000_000, "plant_amount": 3_500_000})
		self.budget.save()

		pg, excavation = self.line("1.1"), self.line("2.1")
		self.assertEqual((pg.budget_cost, pg.margin_percent), (8_000_000, 20))
		self.assertEqual((excavation.budget_cost, excavation.budget_rate), (7_500_000, 7_500))
		self.assertEqual(self.budget.total_budget_cost, 15_500_000)
		self.assertNotIn("Excavation", self.budget.missing_rate_analysis)
		self.assertIn("Concrete C25", self.budget.missing_rate_analysis)

	def test_2b_unplanned_site_costs(self):
		self.budget.unplanned_percent = 10
		self.budget.save()
		self.assertEqual(self.budget.unplanned_amount, 1_550_000)  # 10% of 15,500,000
		self.assertEqual(self.budget.expected_margin, 89_200_000 - 15_500_000 - 1_550_000)

	def test_3_recipe_made_from_a_line(self):
		from consms.construction_management.doctype.bf_budget.bf_budget import make_recipe
		from consms.construction_management.progress import get_budget_cost

		# typed for the whole line: 1,400 bags for 200 m3, labour 9,000,000
		name = make_recipe(self.budget.name, self.line("10.1").name, "Concrete C25 amounts test",
			materials=[{"item_code": self.cement, "qty": 1400, "rate": 20_000}], labour=9_000_000)
		recipe = frappe.get_doc("BF Rate Analysis", name)
		self.assertEqual((recipe.docstatus, recipe.uom), (1, "Cubic Meter"))  # the BOQ line's unit
		self.assertEqual([(r.resource_type, r.item_code, flt(r.qty), flt(r.rate)) for r in recipe.items],
			[("Material", self.cement, 7, 20_000), ("Labour", None, 1, 45_000)])  # kept per 1 m3

		self.budget.reload()
		concrete = self.line("10.1")
		self.assertEqual((concrete.rate_analysis, concrete.materials_amount, concrete.labour_amount), (name, 28_000_000, 9_000_000))
		self.assertEqual((concrete.budget_cost, concrete.budget_rate), (37_000_000, 185_000))
		self.assertEqual(self.budget.total_budget_cost, 52_500_000)

		# Running Cost vs Budget counts typed lines and recipe lines alike
		self.budget.submit()
		_budget, cost = get_budget_cost(self.contract.name)
		self.assertEqual((cost[self.line("1.1").boq_item], cost[self.line("10.1").boq_item]), (8_000_000, 37_000_000))

	def test_4_costs_on_no_boq_line_use_the_unplanned_budget(self):
		from consms.construction_management.report.running_cost_vs_budget.running_cost_vs_budget import get_data

		# an excavator repair: on the project, on no BOQ line
		supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "ConsMS Test Mechanic",
			"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0})}).insert()
		company = frappe.db.get_value("Project", self.budget.project, "company")
		invoice = frappe.get_doc({
			"doctype": "Purchase Invoice", "supplier": supplier.name, "company": company, "project": self.budget.project,
			"items": [{"item_code": make_item("ConsMS Test Repair", stock=False), "qty": 1, "rate": 2_000_000, "project": self.budget.project,
				"expense_account": frappe.db.get_value("Account", {"company": company, "root_type": "Expense", "is_group": 0})}],
		}).insert()
		invoice.set("taxes", [])
		invoice.save()
		invoice.submit()

		data, _budget = get_data(self.contract.name)
		row = next(r for r in data if r.get("bill") == "Unplanned")
		self.assertEqual((row["budget"], row["actual"], row["variance"]), (5_250_000, 2_000_000, 0))  # 10% of 52,500,000
		self.assertEqual(row["status"], "Within the unplanned budget")
