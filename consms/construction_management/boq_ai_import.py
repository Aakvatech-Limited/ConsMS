"""Import a client's BOQ Excel, as received, into a BOQ.

The AI only works out the layout: which columns hold the item no., description, unit,
quantity and rate, and what each row is (item, bill heading, section, subtotal, summary).
Quantities and rates are always copied by this code from the Excel cells, so the AI
can never change a price. Totals are checked against the file before anything is saved.

Any OpenAI-compatible provider works (Google Gemini, Groq...), with Gemen's own key from
BF Construction Settings. Without a key, or when the provider fails, a built-in reader is used.
"""

import json
import re

import frappe
import requests
from frappe import _
from frappe.utils import cstr, flt

PROVIDERS = {
	"Google Gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-flash-lite-latest"),
	"Groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
}
FIELDS = ("item_no", "description", "unit", "quantity", "rate", "amount")
ROW_TYPES = ("item", "bill", "section", "subtotal", "summary", "blank", "other")
CHUNK_ROWS = 250
LAYOUT_ROWS = 40
MAX_COLUMNS = 14
CACHE_TTL = 3600


class AIUnavailable(Exception):
	pass


# ---------------------------------------------------------------- whitelisted API

@frappe.whitelist()
def preview_import(boq, file_url):
	"""Start reading the Excel in the background; returns a token to poll with get_preview."""
	frappe.get_doc("BF Bill of Quantities", boq).check_permission("write")
	token = frappe.generate_hash(length=12)
	set_state(token, {"status": "queued"})
	frappe.enqueue(run_preview, queue="long", timeout=900, token=token, file_url=file_url, user=frappe.session.user)
	return token


@frappe.whitelist()
def get_preview(token):
	return frappe.cache.get_value(cache_key(token)) or {"status": "expired"}


@frappe.whitelist()
def insert_into_boq(boq, token, replace=0):
	doc = frappe.get_doc("BF Bill of Quantities", boq)
	doc.check_permission("write")
	if doc.docstatus != 0:
		frappe.throw(_("Lines can only be imported into a draft BOQ."))
	state = get_preview(token)
	if state.get("status") != "done":
		frappe.throw(_("The preview is no longer available. Run Import with AI again."))
	if frappe.utils.cint(replace):
		doc.set("items", [])
	for item in state["result"]["items"]:
		doc.append("items", {
			"item_no": item["item_no"],
			"description": item["description"],
			"bill": item["bill"],
			"uom": item["unit"],
			"quantity": item["quantity"],
			"unit_rate": item["rate"],
		})
	doc.save()
	return {"count": len(state["result"]["items"]), "total": doc.total_amount}


@frappe.whitelist()
def test_connection():
	frappe.only_for(("System Manager", "Projects Manager"))
	config = get_ai_config()
	if not config:
		frappe.throw(_("Enter the API Key first."))
	answer = call_ai(config, "Reply with JSON only.", 'Return {"ok": true}.')
	return {"ok": bool(answer.get("ok")), "model": config["model"]}


# ---------------------------------------------------------------- background job

def run_preview(token, file_url, user):
	frappe.set_user(user)
	try:
		set_state(token, {"status": "running"})
		set_state(token, {"status": "done", "result": build_preview(file_url)})
	except Exception as e:
		frappe.log_error(title="BOQ AI import failed")
		set_state(token, {"status": "error", "message": cstr(e)[:500]})


def cache_key(token):
	return f"consms:boq_ai_import:{token}"


def set_state(token, state):
	frappe.cache.set_value(cache_key(token), state, expires_in_sec=CACHE_TTL)


# ---------------------------------------------------------------- reading the file

def read_sheets(file_url):
	"""Visible sheets as rows of cell values (first MAX_COLUMNS columns), empty rows kept as blanks."""
	import openpyxl

	path = frappe.get_doc("File", {"file_url": file_url}).get_full_path()
	workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
	sheets = []
	for ws in workbook.worksheets:
		if ws.sheet_state != "visible":
			continue
		rows = []
		for number, values in enumerate(ws.iter_rows(max_col=MAX_COLUMNS, values_only=True), 1):
			cells = [clean(v) for v in values]
			if any(c != "" for c in cells):
				rows.append({"r": number, "cells": cells})
		if rows:
			sheets.append({"name": ws.title, "rows": rows})
	return sheets


def clean(value):
	if value is None:
		return ""
	if isinstance(value, float) and value.is_integer():
		return int(value)
	if isinstance(value, (int, float)):
		return value
	return " ".join(cstr(value).split())


def number(value):
	if isinstance(value, (int, float)) and not isinstance(value, bool):
		return float(value)
	text = cstr(value).replace(",", "").strip()
	try:
		return float(text) if text else None
	except ValueError:
		return None


# ---------------------------------------------------------------- the AI

def get_ai_config():
	settings = frappe.get_cached_doc("BF Construction Settings")
	key = settings.get_password("ai_api_key", raise_exception=False)
	if not key:
		return None
	base, model = PROVIDERS.get(settings.ai_provider, (None, None))
	base = (settings.ai_base_url or base or "").rstrip("/")
	if not base:
		return None
	return {"base": base, "model": settings.ai_model or model, "key": key, "provider": settings.ai_provider}


def call_ai(config, system, user):
	try:
		response = requests.post(
			f"{config['base']}/chat/completions",
			headers={"Authorization": f"Bearer {config['key']}", "Content-Type": "application/json"},
			json={
				"model": config["model"],
				"temperature": 0,
				"response_format": {"type": "json_object"},
				"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
			},
			timeout=120,
		)
	except requests.RequestException as e:
		raise AIUnavailable(_("Could not reach the AI provider: {0}").format(e))
	if response.status_code == 429:
		raise AIUnavailable(_("The AI provider's free limit is used up for now."))
	if response.status_code >= 400:
		raise AIUnavailable(_("AI provider error {0}: {1}").format(response.status_code, response.text[:300]))
	text = response.json()["choices"][0]["message"]["content"] or ""
	text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
	try:
		return json.loads(text)
	except ValueError:
		raise AIUnavailable(_("The AI answer was not valid JSON."))


LAYOUT_PROMPT = """You read construction Bills of Quantities (BOQ) from Excel sheets (Tanzania: PPRA, NeST, TANROADS, Ministry of Water).
Columns are numbered from 0. Find the columns of: item_no (item code such as 5.2.1), description, unit (m3, m2, Nr, LS, PS...), quantity, rate (unit rate), amount.
Return JSON: {"is_boq": true|false, "header_row": <row number or null>, "columns": {"item_no": i, "description": i, "unit": i, "quantity": i, "rate": i, "amount": i}}.
Use null for a column that does not exist. Use is_boq=false for sheets that are not a priced item list (cover pages, notes, summaries only)."""

ROWS_PROMPT = """You classify the heading and total rows of a construction Bill of Quantities (the priced items are already known and not sent). Each row is [row, item_no, description, unit, quantity, rate, amount].
Types: "item" (a priced work item: has a unit and a rate or quantity), "bill" (a bill heading such as "BILL NO. 5 CANAL WORKS" or "1000 GENERAL"),
"section" (a sub-heading inside a bill, such as "5.2 Main Canal" or "Earthworks"), "subtotal" (sub total / total carried forward / page total),
"summary" (the final summary block: total of bills, provisional sums, contingency, VAT, bid price), "blank", "other" (notes, column headers).
For "bill" and "section" rows give a clean title, e.g. "Bill No. 5 - Canal Works" or "Main Canal (MC)".
Return JSON: {"rows": [{"r": <row>, "type": "<type>", "title": "<title for bill/section, else empty>"}]} with one entry per row given."""


def ai_layout(config, sheet):
	sample = [[r["r"]] + r["cells"] for r in sheet["rows"][:LAYOUT_ROWS]]
	answer = call_ai(config, LAYOUT_PROMPT, f"Sheet '{sheet['name']}' (first rows, [row, col0, col1, ...]):\n{json.dumps(sample, default=str)}")
	columns = {f: answer.get("columns", {}).get(f) for f in FIELDS}
	return bool(answer.get("is_boq")), answer.get("header_row"), columns


def ai_row_types(config, rows):
	types = {}
	for start in range(0, len(rows), CHUNK_ROWS):
		chunk = rows[start:start + CHUNK_ROWS]
		answer = call_ai(config, ROWS_PROMPT, json.dumps(chunk, default=str))
		for row in answer.get("rows") or []:
			if row.get("type") in ROW_TYPES:
				types[frappe.utils.cint(row.get("r"))] = (row["type"], cstr(row.get("title")).strip())
	return types


# ---------------------------------------------------------------- built-in reader (no AI)

HEADER_WORDS = {
	"item_no": ("item no", "item", "code", "s n", "sn", "ref", "no"),
	"description": ("description", "discription", "particulars", "work item"),
	"unit": ("unit of measure", "unit", "uom"),
	"quantity": ("quantity", "qty"),
	"rate": ("rate", "unit rate", "unit price"),
	"amount": ("amount", "total"),
}


def words(value):
	return " ".join(re.findall(r"[a-z0-9]+", cstr(value).lower()))


def match_columns(texts):
	"""Exact or leading header words first ('Amount (Tshs)'), then words inside ('TSP Amount')."""
	columns = {}
	for strict in (True, False):
		for field, candidates in HEADER_WORDS.items():
			if field in columns:
				continue
			for j, text in enumerate(texts):
				if j in columns.values() or (field == "unit" and "rate" in text):
					continue
				hit = any(text == w or text.startswith(w + " ") if strict else f" {w} " in f" {text} " for w in candidates)
				if hit:
					columns[field] = j
					break
	return columns


def rule_layout(sheet):
	"""Find the header row by its words; a header may run over two rows (Qty / Rate under 'Bill of Quantities')."""
	rows = sheet["rows"][:LAYOUT_ROWS]
	for two_rows in (False, True):
		for i, row in enumerate(rows):
			below = rows[i + 1]["cells"] if two_rows and i + 1 < len(rows) else []
			texts = [
				" ".join(filter(None, [words(c), words(below[j]) if j < len(below) else ""]))
				for j, c in enumerate(row["cells"])
			]
			columns = match_columns(texts)
			if {"description", "unit", "rate"} <= set(columns):
				header_row = rows[i + 1]["r"] if below else row["r"]
				return True, header_row, {f: columns.get(f) for f in FIELDS}
	return False, None, {f: None for f in FIELDS}


def rule_row_type(values):
	item_no, description, unit, quantity, rate, amount = values
	text = f"{item_no} {description}".strip()
	lower = text.lower()
	if not text and amount is None:
		return "blank", ""
	if lower.startswith("summary") or "bid price" in lower or "total of bills" in lower:
		return "summary", ""
	if "total" in lower and not unit:
		return "subtotal", ""
	if unit and (number(rate) is not None or number(quantity) is not None):
		return "item", ""
	match = re.match(r"bill\s*no\.?\s*(\d+)", lower)
	if match:
		name = cstr(description) or re.sub(r"(?i)bill\s*no\.?\s*\d+", "", cstr(item_no))
		return "bill", f"Bill No. {match.group(1)} - {name.strip().title()}"
	if re.fullmatch(r"\d+", cstr(item_no).strip()) and description:
		return "bill", f"Bill No. {cstr(item_no).strip()} - {cstr(description).strip().title()}"
	if re.fullmatch(r"\d+(\.\d+)+", cstr(item_no).strip()) and description:
		return "section", cstr(description).strip()
	return "other", ""


# ---------------------------------------------------------------- putting it together

def layout_fits(sheet, columns, header_row):
	"""An AI-proposed layout is only used when the numbers agree with it: Qty x Rate = Amount on most priced rows."""
	if None in (columns.get("description"), columns.get("unit"), columns.get("quantity"), columns.get("rate")):
		return False
	priced = agree = 0
	for row in sheet["rows"]:
		if header_row and row["r"] <= frappe.utils.cint(header_row):
			continue
		cells = row["cells"]
		def get(f):
			i = columns.get(f)
			return cells[i] if i is not None and i < len(cells) else ""
		quantity, rate, amount = number(get("quantity")), number(get("rate")), number(get("amount"))
		if get("unit") and quantity is not None and rate is not None:
			priced += 1
			if amount is None or abs(quantity * rate - amount) <= max(1, abs(amount) * 0.001):
				agree += 1
	return priced >= 5 and agree >= 0.8 * priced


def build_preview(file_url):
	"""Columns and item rows come from the file (header words; a row is an item only with a unit and a number),
	so quantities and rates are always the Excel's own. The AI names bills and sections and reads odd headings,
	and proposes columns only for a workbook whose headers the built-in reader cannot find (checked against the numbers)."""
	config = get_ai_config()
	source = f"AI ({config['provider']}, {config['model']})" if config else _("Built-in reader (no AI key)")
	notes, items, counts, file_totals = [], [], {}, []

	def ai_failed(e):
		nonlocal config, source
		notes.append(cstr(e) + " " + _("Used the built-in reader instead."))
		config, source = None, _("Built-in reader (AI not available)")

	sheets = read_sheets(file_url)
	layouts = {sheet["name"]: rule_layout(sheet) for sheet in sheets}
	if config and not any(layout[0] for layout in layouts.values()):
		for sheet in sheets:
			try:
				is_boq, header_row, columns = ai_layout(config, sheet)
			except AIUnavailable as e:
				ai_failed(e)
				break
			if is_boq and layout_fits(sheet, columns, header_row):
				layouts[sheet["name"]] = (True, header_row, columns)

	for sheet in sheets:
		is_boq, header_row, columns = layouts[sheet["name"]]
		if not is_boq:
			continue

		def pick(cells, field):
			i = columns.get(field)
			return cells[i] if i is not None and i < len(cells) else ""

		rows = [r for r in sheet["rows"] if not header_row or r["r"] > frappe.utils.cint(header_row)]
		compact = [[r["r"]] + [pick(r["cells"], f) for f in FIELDS] for r in rows]
		classified = [[values[0], values[1:], *rule_row_type(values[1:])] for values in compact]

		# the AI only looks at the rows that are not items: headings, totals, notes
		if config:
			headings = [values for values, row in zip(compact, classified) if row[2] not in ("item", "blank")]
			try:
				types = ai_row_types(config, headings) if headings else {}
			except AIUnavailable as e:
				ai_failed(e)
				types = {}
			for row in classified:
				kind, title = types.get(row[0], (None, ""))
				if row[2] == "other" and kind in ("bill", "section", "subtotal", "summary"):
					row[2], row[3] = kind, title  # a heading the built-in reader could not place
				elif kind == row[2] and kind in ("bill", "section") and title:
					row[3] = title  # same kind, the AI's cleaner name

		bills_by_number = {}
		for _row, cells, kind, title in classified:
			match = re.search(r"bill no\.?\s*(\d+)", (title or "").lower())
			if kind == "bill" and match:
				bills_by_number.setdefault(match.group(1), title)

		bill, section = None, None
		for row_no, cells, kind, title in classified:
			counts[kind] = counts.get(kind, 0) + 1
			if kind == "bill":
				bill, section = title or cstr(cells[1]), None
			elif kind == "section":
				section = title or cstr(cells[1])
			elif kind in ("summary", "subtotal"):
				amount = number(cells[5])
				# the total of the bills only, never a grand total that already includes VAT or contingency
				if amount and re.search(r"total of bills", cstr(cells[1]).lower() + " " + cstr(cells[0]).lower()):
					file_totals.append(amount)
			elif kind == "item":
				# a missing bill heading: the item number says which bill it belongs to (5.2.1 -> Bill 5)
				prefix = cstr(cells[0]).split(".")[0].strip()
				item_bill = bills_by_number.get(prefix) or bill
				item_section = section if item_bill == bill else None
				item = make_item(sheet["name"], row_no, cells, item_bill or _("General Items ({0})").format(sheet["name"]), item_section, notes)
				if item:
					items.append(item)

	total = round(sum(i["quantity"] * i["rate"] for i in items), 2)
	file_total = max(file_totals) if file_totals else None
	if file_total is not None and abs(total - file_total) > 1:
		notes.append(_("The items add up to {0}, but the file's total is {1} (difference {2}).").format(
			frappe.format_value(total, "Currency"), frappe.format_value(file_total, "Currency"),
			frappe.format_value(total - file_total, "Currency")))
	seen = {}
	for i in items:
		seen.setdefault(i["description"].lower(), []).append(i["item_no"])
	repeated = [(d, n) for d, n in seen.items() if len(n) > 1 and d and all(n)]
	for description, numbers in repeated[:10]:
		notes.append(_("Same description on items {0}: check they are not a copy-paste mistake.").format(", ".join(map(cstr, numbers))))
	if len(repeated) > 10:
		notes.append(_("{0} more descriptions repeat on several items.").format(len(repeated) - 10))

	return {"source": source, "items": items, "total": total, "file_total": file_total, "counts": counts, "notes": notes}


def make_item(sheet, row_no, cells, bill, section, notes):
	item_no, description, unit, quantity, rate, amount = cells
	quantity, rate, amount = number(quantity), number(rate), number(amount)
	where = f"{sheet} row {row_no}"
	if not description or not unit:
		notes.append(_("{0}: looks like an item but has no description or unit; skipped.").format(where))
		return None
	if rate is None and amount is not None and quantity:
		rate = amount / quantity
	if rate is None:
		notes.append(_("{0} ({1}): no rate; imported with rate 0.").format(where, item_no))
	if quantity is None:
		notes.append(_("{0} ({1}): no BOQ quantity; imported with quantity 0 (claimed work would need a Variation Order).").format(where, item_no))
	quantity, rate = flt(quantity), flt(rate)
	if amount is not None and abs(quantity * rate - amount) > 1:
		notes.append(_("{0} ({1}): Qty x Rate = {2} but the file's amount is {3}.").format(
			where, item_no, frappe.format_value(quantity * rate, "Currency"), frappe.format_value(amount, "Currency")))
	label = bill or _("General Items")
	return {
		"row": row_no,
		"item_no": cstr(item_no),
		"description": cstr(description),
		"bill": f"{label} / {section}" if section else label,
		"unit": cstr(unit),
		"quantity": quantity,
		"rate": rate,
	}
