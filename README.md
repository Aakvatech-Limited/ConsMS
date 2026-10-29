# ConsMS: Construction Management for ERPNext

ConsMS is a Frappe app for construction contractors. It runs on top of ERPNext.

It follows a contract from the Bill of Quantities to the payment certificate and the invoice. Money and stock stay in ERPNext. ConsMS adds the construction documents and links them to the ERPNext documents.

---

## Contents

1. [How the app works](#how-the-app-works)
2. [Installation](#installation)
3. [First setup](#first-setup)
4. [Bill of Quantities](#bill-of-quantities)
5. [Tender](#tender)
6. [Contract](#contract)
7. [Budget and Rate Analysis](#budget-and-rate-analysis)
8. [Buying against the budget](#buying-against-the-budget)
9. [Site work and measurements](#site-work-and-measurements)
10. [Variation Orders](#variation-orders)
11. [Payment certificates (IPC)](#payment-certificates-ipc)
12. [Certificate Templates: how to configure them](#certificate-templates-how-to-configure-them)
13. [Invoices](#invoices)
14. [Tasks and costs](#tasks-and-costs)
15. [Reports](#reports)
16. [Reminders](#reminders)
17. [Troubleshooting](#troubleshooting)
18. [For developers](#for-developers)

---

## How the app works

A contract moves through these documents:

```text
Bill of Quantities (BOQ)
    ↓
Tender
    ↓
Contract  ──→  Budget  ──→  Material Request / Purchase Order
    ↓
Site Measurement Log  ──→  Variation Order (when the work goes beyond the BOQ)
    ↓
Progress Claim (the payment certificate, IPC)
    ↓
Sales Invoice (client) or Purchase Invoice (subcontractor)
```

All ConsMS documents start with "BF". All of them are in the **Construction MS** workspace.

---

## Installation

You need a Frappe bench with ERPNext version 15 or 16.

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Aakvatech-Limited/ConsMS.git --branch master
bench --site <site-name> install-app consms
bench --site <site-name> migrate
```

After each update, always run `bench --site <site-name> migrate`. The migrate adds the custom fields, the starter templates and the document types.

---

## First setup

Do these steps once, before the first contract.

1. Open **BF Construction Settings**.
2. Set **VAT Rate**, for example 18. The system adds VAT to certificates with this rate.
3. Set **Default Progress Claim Item**. This is a service Item. The Sales Invoice of a certificate uses it.
4. Set **Default Certificate Template**, for example "TANROADS".
5. Set **Default BOQ Summary Template**, for example "Tender Summary A-I".
6. Set **When a Purchase Is Over the Budget Quantity**: Warn, Stop, or Stop unless approved.
7. Optional: set the **AI BOQ Import** provider and API key, to read BOQs from PDF or Excel files.
8. In ERPNext, make sure the company has a default **Sales Taxes and Charges Template** with the VAT account. The certificate invoice uses its VAT account.

The migrate also adds these starter records. You can change them or add your own:

| Record | Starter values |
| --- | --- |
| Certificate Templates | Ministry of Water (SEUWASA), TANROADS, FIDIC (Price Adjustment, VAT on Net), Tender Summary A-I, Bills + VAT 18%, Budget Overheads (Sengerema) |
| BF Document Type | Tender documents (BRELA, CRB, TRA, Bid Security...), contract submittals (CAR Insurance, HSE Plan...), certificate documents (Taking-Over Certificate, Final Account...) |
| BF Bid Security Type | Bank guarantee, insurance bond, Bid Securing Declaration... |

---

## Bill of Quantities

The **BF Bill of Quantities** holds the work items. Each line has a bill, an item number, a description, a unit, a quantity and a rate.

- **Import**: type the lines, or use **Import with AI** to read a PDF or Excel file.
- **VAT-exempt bills**: use **Actions → VAT Exempt Bills** to mark bills with no VAT, for example Preliminaries. Certificates do not charge VAT on these lines.
- **Tender Summary**: choose a **Summary Template**. The summary lines calculate the **Bid Price**, for example total of bills, contingency, variation of prices and VAT. Type amounts only on "Typed Amount" lines.
- **Revisions**: approved Variation Orders change the quantities. The BOQ shows the original quantity, the variation and the revised quantity.

Submit the BOQ before you make a contract from it.

Print formats:

- **BOQ Client Layout**: the bills, the bill totals, and the summary page with the bid price.
- **Revised BOQ**: original quantity, variation and revised quantity for each line.

---

## Tender

The **BF Tender** records the bid.

- **Documents**: the papers the bid needs. The list shows only document types with "Applies To" = Tender or Both.
- **Bid Securities**: one row for each guarantee or bond. Record the bank, the amount and the expiry date. "Total Bid Security" adds up the rows that are "Held by Client". A reminder goes out 14 days before a guarantee expires.
- **Tender costs**: book costs such as bid fees with a Purchase Invoice, Journal Entry or Expense Claim on the tender's Project.

The bid security rows are a register only. They do not post to the accounts. Record a cash deposit or a bank commission with a normal Journal Entry on the Project.

One tender can have only one contract.

---

## Contract

The **BF Contract** holds the agreement. Make it from the tender or from the BOQ with **Create → BF Contract**.

**Contract Type**:

- **Main Contract**: the agreement with the client (Customer).
- **Subcontract**: the agreement with a subcontractor (Supplier). Link it to its main contract.

**Contract value**:

| Field | Meaning |
| --- | --- |
| Contract Amount | From the BOQ. The bid price without VAT when the BOQ has a tender summary. Otherwise the total of bills. |
| Contingency (%) / Contingency Amount | Extra money added on the contract. |
| Total Contract Value | Contract Amount + Contingency Amount. |
| Contract Sum (incl. VAT) | The bid price on the Form of Tender, plus the contingency with its VAT. |
| Revised Contract Value | Total Contract Value + approved variations. |

**Payment Terms** (the certificates use these):

| Field | Used for |
| --- | --- |
| Advance Payment (%) / Amount | The advance. Use **Create → Advance Payment Invoice** to bill it. Certificates recover it. |
| Certificate Template | The client's rules for the certificates. See [Certificate Templates](#certificate-templates-how-to-configure-them). |
| VAT Status | Standard Rated: VAT on every certificate. Exempt or Zero Rated: no VAT. |
| VAT Basis | Gross Work: VAT on the work. Net after Deductions: VAT after retention and advance recovery. |
| Liquidated Damages per Day | Suggests the delay penalty on certificates after the completion date. |
| Payment Period (Days) | The client must pay this many days after the certified date. |
| Late Payment Interest (% per Year) | Suggests interest on late payments on the next certificate. |
| Measurement Tolerance (%) | How far a BOQ line can be measured above its quantity before a Variation Order is needed. |

**Required Submittals**: the documents the contractor hands in, for example insurance and the work schedule. The list shows only document types with "Applies To" = Contract or Both. A reminder goes out 30 days before a submittal expires.

**Balances to Date**: the system fills these from the submitted certificates: advance recovered, advance balance, retention held, retention released, liquidated damages.

**Extension of Time**: use **Create → Extension of Time**. Send the request to the consultant by email from the form. The system then makes a follow-up ToDo for 28 days later. Approved days move the revised completion date.

**Communication**: use the form's timeline (email, comments), attachments and ToDos.

---

## Budget and Rate Analysis

The **BF Budget** shows the planned cost of each BOQ line. Make it from the contract.

Each BOQ line has four amounts: materials, labour, plant and other. Fill them in one of two ways:

- Type the four amounts.
- Choose a **BF Rate Analysis** (a recipe for one unit, for example 1 m³ of concrete). The budget multiplies it by the BOQ quantity.

The **Overheads Template** adds lines such as contingency and supervision fee to the direct cost.

---

## Buying against the budget

Make purchases from the budget, so each row keeps its BOQ line.

1. Open the submitted budget.
2. Click **Create → Material Request**.
3. Remove the rows you do not need now, change the quantities, then save.

The Material Request rows carry the **BOQ Line** and the **Budget**. The Request for Quotation, Supplier Quotation, Purchase Order, Purchase Receipt and Purchase Invoice made from it keep the same links.

On save, the system checks each row against the budget quantity. The setting **When a Purchase Is Over the Budget Quantity** decides what happens:

- **Warn**: a message. The document can still be submitted.
- **Stop**: the document cannot be submitted. Revise the budget first.
- **Stop unless approved**: only the approver role can submit it.

---

## Site work and measurements

- **BF Works Execution**: the work plan, linked to the project tasks.
- **BF Site Measurement Log**: the quantities measured on site for each BOQ line. Attach the measurement sheet as proof.

A measurement cannot go beyond the revised BOQ quantity (plus the contract's tolerance). When it does, the system stops the submit. Then:

1. On the measurement, click **Actions → Create Variation Order**. The system makes a draft Variation Order with the extra quantity.
2. Get the Variation Order approved and submit it. The BOQ quantity goes up.
3. Go back to the measurement and submit it. The system does not submit it for you.

---

## Variation Orders

The **BF Variation Order** changes the contract. Each line has one of three types:

| Line type | Example | How it is paid |
| --- | --- | --- |
| Change to BOQ Line | Slab goes from 300 m² to 350 m² | By measurement, on the certificate's Claim Items |
| New Item | New item: paving blocks, 200 m² | By measurement, on the certificate's Claim Items |
| Lump Sum | Move the power line, 5,000,000 fixed | By amount, on the certificate's Claimed Variations |

Record the client's instruction number, approval date and approval letter. On submit, the BOQ gets a new revision.

---

## Payment certificates (IPC)

The **BF Progress Claim** is the payment certificate. It is called IPC (Interim Payment Certificate) on the print.

### Kinds of certificate

| Claim Type | Contract | Makes |
| --- | --- | --- |
| Client Claim | Main Contract | Sales Invoice |
| Subcontractor Claim | Subcontract | Purchase Invoice |

| Certificate Type | When |
| --- | --- |
| Interim | Every normal monthly certificate |
| Substantial Completion | When the works are taken over |
| Final | At the end of the defects liability period |

The certificate type decides which template lines apply. For example, a retention release line can apply to the Final certificate only.

### How to make a certificate

1. Open the submitted contract.
2. Click **Create → Progress Claim (IPC)**.
3. Set **Period From** and **Period To**. Periods of one contract cannot overlap.
4. Set **Certificate Type**.
5. Save.
6. Click **Actions → Fetch Measurements**.
7. Check the **Claim Items**, the **Claimed Variations** and the **Certificate Lines**.
8. Type the amounts on the "Typed Amount" lines, for example materials on site.
9. Save. The system calculates the certificate again.
10. In **Supporting Documents**, attach each document and set its status to "Ready".
11. Submit.
12. Click **Create → Sales Invoice** (or **Purchase Invoice** for a subcontractor).

### What Fetch Measurements does

- **Claim Items**: one row for each BOQ line. "This Period" is the total of the submitted measurements dated in the certificate period. "Previous" comes from the earlier certificates.
- **Claimed Variations**: one row for each approved Variation Order with a lump sum. "Claimed This Period" starts at the amount not yet claimed. You can lower it when only part of the work is done.
- **Liquidated Damages**: when the template has a typed Liquidated Damages line, it gets the suggested amount.
- **Late Payment Interest**: when the template has a typed Late Payment Interest line, it gets the suggested interest.

Claimed Variations stays empty when the contract has no lump-sum Variation Order. Extra quantities from a "Change to BOQ Line" variation are in the Claim Items, not in Claimed Variations.

### How the amount is calculated

1. **Work This Certificate** = value of Claim Items this period + Claimed Variations this period.
2. The **Certificate Lines** run from top to bottom. Each line adds to or takes from a running total. The lines come from the Certificate Template.
3. **Amount Due (Excl. VAT)** = the last running total.
4. The system adds **VAT** from the contract's VAT Status and VAT Basis. VAT is not a template line.
5. **Amount Due** = Amount Due (Excl. VAT) + VAT.

Example with the "Ministry of Water (SEUWASA)" template. Work this certificate is 1,000,000. The advance not yet recovered is more than 200,000. VAT Status is Standard Rated, VAT Basis is Gross Work, and the VAT rate is 18%.

| Line | Amount | Running total |
| --- | --- | --- |
| Completed execution of the works | 1,000,000 | 1,000,000 |
| Less: Retention 5% | 50,000 | 950,000 |
| Less: Advance recovery 20% | 200,000 | 750,000 |
| Add: Value of materials on site | 0 | 750,000 |
| Less: Liquidated damages | 0 | 750,000 |
| **Amount Due (Excl. VAT)** | | **750,000** |
| VAT 18% of the work | 180,000 | |
| **Amount Due** | | **930,000** |

### Print formats

| Print format | Contents |
| --- | --- |
| IPC Payment Certificate | The certificate page with the lines and the amount due |
| IPC Valuation Sheet | Each BOQ line: revised quantity, previous, this certificate, to date |
| IPC Summary by Bill | Each bill: original, revised, previous, this certificate, to date |
| IPC Full Set | All of the above together |

Other print formats: **Variation Order Client** (for the client's approval) and **Extension of Time Request**.

---

## Certificate Templates: how to configure them

A **BF Certificate Template** holds the client's payment rules. The rules are not in the code. You set them as lines in a template. Each client can have its own template.

### Where templates are used

The **Used For** field says where a template can be chosen:

| Used For | Chosen on | Calculates |
| --- | --- | --- |
| Payment Certificate | Contract, Progress Claim, Settings (default) | The amount due on a certificate |
| BOQ Summary | BOQ, Settings (default) | The bid price of a BOQ |
| Budget Overheads | Budget | The overheads on top of the direct cost |

Each dropdown lists only the templates for that form.

### Which template a certificate uses

1. The template on the certificate, when you choose one.
2. Otherwise, the template on the contract.
3. Otherwise, the **Default Certificate Template** in Settings.

When you change the template or the certificate type, the system loads the lines again on the next save.

### How a template works

The lines run from top to bottom. A running total starts at 0. Each line:

- **Add**: adds its amount to the running total.
- **Less**: takes its amount from the running total.
- **Subtotal**: shows the running total at this point. It does not change it.

The last running total is the amount due before VAT.

### The fields of a line

| Field | What to put |
| --- | --- |
| **Line** | The text printed on the certificate, for example "Less: Retention 10%". |
| **Add / Less** | Add, Less or Subtotal. Always type a positive amount. This field gives the sign. |
| **Amount From** | Where the amount comes from. See the next table. |
| **Rate (%)** | For "Percentage" lines: the percentage, for example 10. |
| **% Of** | For "Percentage" lines: what the percentage is of. See the table below. |
| **Line No.** | For "% Of" = "Total at Line": the number of a line above. The system uses the running total after that line. |
| **Less Earlier Certificates** | Takes off what this line took on earlier certificates. Use it with "Work to Date". |
| **Limit** | A ceiling over all certificates together. See [Limits](#limits). |
| **Limit (%)** | For "Limit" = "% of Contract Value": the percentage. |
| **Applies To** | Which certificate types use the line. See [Applies To](#applies-to). |
| **Role** | What the line means for the rest of the system. See [Roles](#roles). |
| **For Calculation Only** | The line changes the running total for the lines below, but is not in the final amount. |

### Amount From

| Amount From | The amount is | Templates |
| --- | --- | --- |
| Work This Certificate | The value of the work this certificate | Payment Certificate |
| Percentage | Rate (%) of the "% Of" value | All |
| Typed Amount | The amount the user types on the certificate | All |
| Total of Bills | The total of the BOQ | BOQ Summary |
| Provisional Sums | The total of the BOQ lines marked as provisional sums | BOQ Summary |
| Direct Cost | The direct cost of the budget | Budget Overheads |

### % Of

| % Of | Means |
| --- | --- |
| Work This Certificate | The work this certificate, with variations |
| Work This Certificate (excl. VAT-Exempt) | The same, without the VAT-exempt bills |
| Work to Date | All work certified up to this certificate |
| Running Total | The running total just above this line |
| Total at Line | The running total after the line in "Line No." |
| Retention Held | Retention taken so far, less retention released |
| Advance Balance | The advance not yet recovered |
| Contract Value | The contract's Total Contract Value |
| Total of Bills | The BOQ total (BOQ Summary only) |
| Direct Cost | The budget direct cost (Budget Overheads only) |

### Roles

The role tells the system what a line is. The contract balances, the invoice and the reports read the roles, not the line text. Give the role to each line that has one of these meanings:

| Role | Use it on | The system uses it for |
| --- | --- | --- |
| Work | The work line | Reports |
| Retention | The retention deduction | "Retention Held" on the contract and the certificate |
| Retention Release | The line that pays retention back | Takes it off "Retention Held" |
| Advance Payment | A line that pays an advance on the certificate | The advance balance |
| Advance Recovery | The advance recovery | "Advance Recovered" and "Advance Balance" |
| Materials on Site | Materials delivered but not used | The certificate total for materials |
| Liquidated Damages | The delay penalty | Gets the suggested amount. "Liquidated Damages to Date" on the contract |
| Late Payment Interest | Interest on late payments | Gets the suggested interest |
| VAT | BOQ Summary templates only | Payment Certificate templates cannot have a VAT line |

### Applies To

| Applies To | The line is on |
| --- | --- |
| All Certificates | Every certificate |
| Interim Only | Interim certificates only |
| Substantial Completion | The Substantial Completion certificate only |
| Final | The Final certificate only |
| Substantial Completion and Final | Both of these |

### Limits

A limit stops a line from going too far over all certificates together. When the limit is reached, the line gives 0.

| Limit | The line stops at |
| --- | --- |
| % of Contract Value | Limit (%) of the contract value. Example: retention up to 5% of the contract. |
| Advance Payment | The advance not yet recovered. Use it on advance recovery. |
| Retention Held | The retention held. Use it on a typed retention release. |

When the line has a role, the limit counts all lines with the same role.

### Common rules and how to set them

**Retention of 10% on each certificate**

| Line | Add / Less | Amount From | Rate | % Of | Role |
| --- | --- | --- | --- | --- | --- |
| Less: Retention 10% | Less | Percentage | 10 | Work This Certificate | Retention |

**Retention of 5%, up to 5% of the contract**

Use the line above with Rate 5. Then set **Limit** = "% of Contract Value" and **Limit (%)** = 5.

**Half the retention back at completion, the rest at the final certificate**

| Line | Add / Less | Amount From | Rate | % Of | Applies To | Role |
| --- | --- | --- | --- | --- | --- | --- |
| Add: Release of 50% retention | Add | Percentage | 50 | Retention Held | Substantial Completion | Retention Release |
| Add: Release of the remaining retention | Add | Percentage | 100 | Retention Held | Final | Retention Release |

**Advance recovered as 20% of each certificate**

| Line | Add / Less | Amount From | Rate | % Of | Limit | Role |
| --- | --- | --- | --- | --- | --- | --- |
| Less: Advance recovery 20% | Less | Percentage | 20 | Work This Certificate | Advance Payment | Advance Recovery |

The limit stops the recovery when the advance is fully back.

**Advance recovered as 30% of the work to date**

Use % Of = "Work to Date" and tick **Less Earlier Certificates**. Each certificate then takes 30% of all work so far, less what earlier certificates took.

**The rest of the advance at completion**

| Line | Add / Less | Amount From | Rate | % Of | Applies To | Role |
| --- | --- | --- | --- | --- | --- | --- |
| Less: Recovery of the remaining advance | Less | Percentage | 100 | Advance Balance | Substantial Completion and Final | Advance Recovery |

**Amounts the user types**

Use Amount From = "Typed Amount" for materials on site, price adjustment, liquidated damages and late payment interest. Give each line its role.

**Retention on a subtotal (FIDIC style)**

1. Add the work line and the typed lines, for example price adjustment.
2. Add a **Subtotal** line.
3. Add the retention line with % Of = "Running Total".

### Make a template for a new client

1. Open an existing template that is close to the client's rules.
2. Click **... → Duplicate**.
3. Give it a new **Template Name**, for example the client's name.
4. Change the lines to match the client's certificate. Use a real certificate from the client as the guide.
5. Save. The system checks the lines and shows what is wrong.
6. Set the template on the client's contract.
7. Make a test certificate. Compare the result with the client's certificate.

### VAT on certificates

VAT is not a template line. The system adds it from the contract:

| Contract setting | VAT |
| --- | --- |
| VAT Status = Standard Rated, VAT Basis = Gross Work | VAT Rate × the taxable work this certificate |
| VAT Status = Standard Rated, VAT Basis = Net after Deductions | VAT Rate × (taxable work − retention − advance recovery) |
| VAT Status = Exempt or Zero Rated | No VAT. The certificate prints the exemption reference. |

Taxable work does not include the bills marked as VAT exempt on the BOQ.

### Supporting documents

The **Supporting Documents** table fills itself from the BF Document Types with "Applies To" = Payment Certificate. The "Certificate Types" field of the document type decides on which certificates it shows.

When a document type is **Mandatory**, the certificate cannot be submitted until that row has an attachment and its status is "Ready".

### Due date and late payment interest

- **Certified Date**: the date the engineer certified the certificate. It defaults to the posting date. You can set it after submit.
- **Payment Due Date** = Certified Date + the contract's Payment Period.
- The **Late Payment Interest** report shows each certificate against its due date, the payments from the books, the days late and the interest.
- On the next certificate, Fetch Measurements puts the interest not yet claimed on the typed "Late Payment Interest" line.

---

## Invoices

- **Client Claim → Sales Invoice**: one line with the Default Progress Claim Item and the Amount Due (Excl. VAT). The VAT row has the certificate's exact VAT. The due date is the certificate's due date.
- **Subcontractor Claim → Purchase Invoice**: the same, for the subcontractor.
- **Advance payment**: from the contract, **Create → Advance Payment Invoice**.

The invoice total is always equal to the certificate to the cent. Rounding is off on these invoices.

---

## Tasks and costs

**Task** is an accounting dimension. Record site costs on the task:

- **Materials**: issue them from the site store with a Stock Entry (Material Issue). Set the Project and the Task.
- **Labour gangs and hired machines**: they are Suppliers. Put the Project and the Task on their Purchase Invoice.
- **Other costs**: put the Task on the Journal Entry.

Then:

- The Task form shows a **Costs** section: materials, other costs and total.
- The **Task Activity** report shows the same for all tasks of a project.

---

## Reports

| Report | Shows |
| --- | --- |
| BOQ Progress | Each BOQ line: original, variation and revised quantity, done to date, remaining |
| Budget Materials Summary | Each resource over the budget: needed, requested, received |
| Running Cost vs Budget | Each BOQ line: budget, actual cost, open purchase orders, variance |
| Contract Profitability | Each main contract: expected profit and profit so far |
| Contract Status Summary | Each contract: value, variations, certified, % complete, retention held, invoiced |
| Contract Time Tracker | Each contract: start, completion, extensions, days remaining, % time used against % work done |
| Late Payment Interest | Each certificate: due date, paid, days late, interest |
| VAT on IPCs | Each certificate: certified, taxable, VAT, invoice |
| Task Activity | Each task: % done, materials cost, other costs, total |

---

## Reminders

A daily job sends reminders for:

- Contract submittals that expire in 30 days.
- Bid securities that expire in 14 days.
- Advance payment guarantees that expire in 30 days.

---

## Troubleshooting

**"Cumulative Claimed amount cannot exceed the Approved Amount" on a certificate**

The Variation Order in the Claimed Variations row has no lump sum. It is a "Change to BOQ Line" or "New Item" variation. Delete the row. The extra quantity comes in the Claim Items through the measurement.

**The certificate does not show the extra quantity of a Variation Order**

The measurement is still a draft. Submit the measurement, then click **Fetch Measurements** again.

**A measurement cannot be submitted: the quantity is beyond the BOQ**

Click **Actions → Create Variation Order** on the measurement. Submit the Variation Order. Then submit the measurement.

**"Attach these documents and mark them Ready before submitting the certificate"**

A mandatory supporting document is missing. Attach it and set its status to "Ready".

**"Set a default Sales Taxes and Charges Template with the VAT account"**

The company has no default sales tax template. Make one with the VAT account and set it as default.

**The Connections tab of a BOQ is empty**

No document is linked to that BOQ yet. A contract, budget or certificate made from the BOQ shows there.

**"Line X: VAT is added to every certificate by the system"**

A Payment Certificate template has a line with role VAT. Remove the line. The contract's VAT settings add VAT.

---

## For developers

### Code layout

```text
consms/
├── hooks.py                          Events, daily job, dashboard overrides
├── setup.py                          After-migrate setup (custom fields, starter records, Task dimension)
├── budget_control.py                 Budget check on Material Request and Purchase Order
├── construction_management/
│   ├── ipc.py                        Certificate engine: template lines, VAT, balances, late interest
│   ├── certificate_templates.py      Starter templates and certificate document types
│   ├── variations.py                 Variation Orders and measurement limits
│   ├── budget.py, progress.py        Budget amounts and progress against the BOQ
│   ├── boq_ai_import.py              AI import of BOQ files
│   ├── reminders.py                  Daily expiry reminders
│   ├── doctype/                      All BF DocTypes
│   ├── report/                       Script reports
│   └── print_format/                 BOQ and IPC print formats
├── templates/print/                  Shared IPC print parts
└── patches/                          Data patches
```

### Tests

The tests are in `consms/tests/`.

Run the tests only on a test site. ERPNext's test setup deletes data, for example all Item Prices. Do not run `bench run-tests` on a site with real data.

### Code quality

```bash
cd apps/consms
pre-commit install
```

The hooks run Ruff, ESLint, Prettier and Pyupgrade.

### Contributing

1. Make a branch from `master`.
2. Use a conventional commit prefix: `feat:`, `fix:`, `docs:` or `chore:`.
3. Add a test when you change a calculation.
4. Open a pull request to `master`.

---

## License

MIT. See `license.txt`.

Repository: https://github.com/Aakvatech-Limited/ConsMS
