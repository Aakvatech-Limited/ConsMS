# ConsMS: Construction Management for ERPNext

ConsMS is a Frappe app for construction contractors. It runs on top of ERPNext.

It follows a contract from the Bill of Quantities to the payment certificate and the invoice. Money and stock stay in ERPNext. ConsMS adds the construction documents and links them to the ERPNext documents.

---

## Contents

1. [How the app works](#how-the-app-works)
2. [Where to find things](#where-to-find-things)
3. [Installation](#installation)
4. [First setup](#first-setup)
5. [Bill of Quantities](#bill-of-quantities)
6. [Tender](#tender)
7. [Contract](#contract)
8. [Budget and Rate Analysis](#budget-and-rate-analysis)
9. [Buying against the budget](#buying-against-the-budget)
10. [Works Execution and tasks](#works-execution-and-tasks)
11. [Site measurements](#site-measurements)
12. [Variation Orders](#variation-orders)
13. [Payment certificates (IPC)](#payment-certificates-ipc)
14. [Certificate Templates: full guide](#certificate-templates-full-guide)
15. [Invoices](#invoices)
16. [Reports](#reports)
17. [Reminders](#reminders)
18. [Troubleshooting](#troubleshooting)
19. [For developers](#for-developers)

---

## How the app works

A contract moves through these steps:

```text
1. Bill of Quantities (BOQ) ─── priced, with its Tender Summary (bid price)
        ↓
2. Tender ─── bid documents and bid securities
        ↓
3. Contract ─── value, payment terms, Certificate Template, submittals
        ↓
        ├──→ Budget ──→ Material Request ──→ Purchase Order ──→ Purchase Receipt / Invoice
        │
4. Works Execution: Mobilization ─── creates the project Tasks. Complete it first.
        ↓
5. Site Measurement Log ─── quantities done, per BOQ line
        │
        └──→ Variation Order ─── when the work goes beyond the BOQ
        ↓
6. Progress Claim (IPC) ─── the payment certificate, calculated by the Certificate Template
        ↓
7. Sales Invoice (client) or Purchase Invoice (subcontractor)
```

Site costs are recorded on the project **Tasks**: materials issued, labour gangs, hired machines and other costs. See [Works Execution and tasks](#works-execution-and-tasks).

All ConsMS documents start with "BF".

---

## Where to find things

Open the **Construction MS** workspace. It has these sections:

| Section | Shortcuts | Numbers |
| --- | --- | --- |
| Pre-Construction | Tenders, Bill of Quantities, Contracts, Import BOQ | Open Tenders, Total Contract Value, Monthly Contract Awards chart |
| Budget & Procurement | Budgets, Material Requests, Running Cost vs Budget, Rate Analysis | |
| Works Execution | Works Execution, Measurement Logs, Variation Orders | |
| Project Tasks | Project Tasks, Projects | Overdue Tasks, Tasks by Status chart |
| Billing | Progress Claims (IPC), Contract Status Summary, Sales Invoices, Payments Received | Certified to Date, Retention Held, Claims Not Yet Invoiced, Certified per Month chart |
| Contract Administration | Contract Time Tracker, BOQ Progress, Extensions of Time | Pending Submittals, Expiring Documents |
| Reports & Setup | All reports. Setup: Construction Settings, UOM Mapping, Document Types, Bid Security Types, Activity Types, **Certificate Templates**, Project Templates | |

---

## Installation

You need a Frappe bench with ERPNext version 15 or 16.

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Aakvatech-Limited/ConsMS.git --branch master
bench --site <site-name> install-app consms
bench --site <site-name> migrate
```

After each update, always run `bench --site <site-name> migrate`. The migrate adds the custom fields, the starter templates and the document types. It also runs the data patches.

---

## First setup

Do these steps once, before the first contract.

**In BF Construction Settings:**

1. Set **VAT Rate**, for example 18. The system adds VAT to certificates with this rate.
2. Set **Default Progress Claim Item**. This is a service Item. The Sales Invoice of a certificate uses it.
3. Set **Default Certificate Template**, for example "TANROADS". A contract with no template uses it.
4. Set **Default BOQ Summary Template**, for example "Tender Summary A-I".
5. Set **When a Purchase Is Over the Budget Quantity**: Warn, Stop, or Stop unless approved.
6. Optional: set the **AI BOQ Import** provider and API key, to read BOQs from PDF or Excel files.

**In the other setup records:**

7. **Activity Types**: make sure one type has **Is Mobilization** ticked, for example "Mobilization". Give it a **Default Project Template** with the mobilization tasks.
8. **Certificate Templates**: check that a template matches each client's payment certificate. Make new ones where needed. See [Certificate Templates: full guide](#certificate-templates-full-guide).
9. **UOM Mapping**: map the units the clients write in their BOQs (m³, Nr, Ls) to ERPNext units. The common ones are already there.

**In ERPNext:**

10. Make sure the company has a default **Sales Taxes and Charges Template** with the VAT account. The certificate invoice uses its VAT account.

The migrate adds these starter records. You can change them or add your own:

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
- **Provisional sums**: tick **Provisional Sum** on those lines. The Tender Summary can take them off.
- **Tender Summary**: choose a **Summary Template**. The summary lines calculate the **Bid Price**. See [BOQ Summary templates](#boq-summary-templates).
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
| Total Contract Value | Contract Amount + Contingency Amount. Certificate limits such as "5% of the contract" use this value. |
| Contract Sum (incl. VAT) | The bid price on the Form of Tender, plus the contingency with its VAT. |
| Revised Contract Value | Total Contract Value + approved variations. |

**Payment Terms** (the certificates use these):

| Field | Used for |
| --- | --- |
| Advance Payment (%) / Amount | The advance. Use **Create → Advance Payment Invoice** to bill it. Certificates recover it. |
| Certificate Template | The client's rules for the certificates. See [Certificate Templates: full guide](#certificate-templates-full-guide). |
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

The **BF Budget** shows the planned cost of each BOQ line. Make it from the contract with **Create → Budget**.

Each BOQ line has four amounts: materials, labour, plant and other. Fill them in one of two ways:

- Type the four amounts.
- Choose a **BF Rate Analysis** (a recipe for one unit, for example 1 m³ of concrete). The budget multiplies it by the BOQ quantity.

The **Overheads Template** adds lines such as contingency and supervision fee to the direct cost. See [Budget Overheads templates](#budget-overheads-templates).

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

## Works Execution and tasks

The **BF Works Execution** plans a part of the work as project Tasks.

1. On the submitted contract, click **Create → Works Execution**.
2. The first one is of the type with **Is Mobilization** ticked. Its Project Template makes the mobilization tasks.
3. Update the task statuses as the work goes on.
4. When all its tasks are "Completed", submit the Works Execution.

Measurements can start only after a Mobilization Works Execution is submitted for the contract.

**Task** is an accounting dimension. Record site costs on the task:

- **Materials**: issue them from the site store with a Stock Entry (Material Issue). Set the Project and the Task.
- **Labour gangs and hired machines**: they are Suppliers. Put the Project and the Task on their Purchase Invoice.
- **Other costs**: put the Task on the Journal Entry.

Then:

- The Task form shows a **Costs** section: materials, other costs and total.
- The **Task Activity** report shows the same for all tasks of a project.

---

## Site measurements

The **BF Site Measurement Log** records the quantities done on site for each BOQ line. Make it from the contract with **Create → Site Measurement Log**. Attach the measurement sheet as proof.

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

The next chapter explains the template lines in full.

### Supporting documents

The **Supporting Documents** table fills itself from the BF Document Types with "Applies To" = Payment Certificate. The "Certificate Types" field of the document type decides on which certificates it shows.

When a document type is **Mandatory**, the certificate cannot be submitted until that row has an attachment and its status is "Ready".

### Due date and late payment interest

- **Certified Date**: the date the engineer certified the certificate. It defaults to the posting date. You can set it after submit.
- **Payment Due Date** = Certified Date + the contract's Payment Period.
- The **Late Payment Interest** report shows each certificate against its due date, the payments from the books, the days late and the interest.
- On the next certificate, Fetch Measurements puts the interest not yet claimed on the typed "Late Payment Interest" line.

### Print formats

| Print format | Contents |
| --- | --- |
| IPC Payment Certificate | The certificate page with the lines and the amount due |
| IPC Valuation Sheet | Each BOQ line: revised quantity, previous, this certificate, to date |
| IPC Summary by Bill | Each bill: original, revised, previous, this certificate, to date |
| IPC Full Set | All of the above together |

Other print formats: **Variation Order Client** (for the client's approval) and **Extension of Time Request**.

---

## Certificate Templates: full guide

This is the most important setup in ConsMS. Read it before the first certificate of a new client.

### What a template is

Each client calculates its payment certificate in its own way. One client takes 10% retention. Another takes 5% up to a limit. One recovers the advance at 20% of each certificate, another at 30% of the work to date.

ConsMS does not hold these rules in its code. A **BF Certificate Template** holds them. The template is a list of lines, in the same order as the lines on the client's paper certificate. Each line says where its amount comes from and whether it is added or taken off.

When you make a certificate, the system copies the template lines onto it. Then it calculates each line from top to bottom.

### The three kinds of template

The same engine calculates three things. The **Used For** field says which one a template is for:

| Used For | Chosen on | Calculates | Starter templates |
| --- | --- | --- | --- |
| Payment Certificate | Contract, Progress Claim, Settings (default) | The amount due on a certificate | Ministry of Water (SEUWASA), TANROADS, FIDIC (Price Adjustment, VAT on Net) |
| BOQ Summary | BOQ, Settings (default) | The bid price of a BOQ | Tender Summary A-I, Bills + VAT 18% |
| Budget Overheads | Budget | The overheads on top of the direct cost | Budget Overheads (Sengerema) |

Each form lists only the templates made for it. A BOQ shows only BOQ Summary templates, for example.

### Which template a certificate uses

1. The template on the certificate, when you choose one.
2. Otherwise, the template on the contract.
3. Otherwise, the **Default Certificate Template** in Settings.

The usual way: set the template once on the contract. All certificates of the contract then use it.

### Step 1: Read the client's certificate

Get a real payment certificate from the client, or the payment clauses of the contract. Write down each line in order. For each line, answer five questions:

| Question | Example answer | Goes in field |
| --- | --- | --- |
| Is the amount added, taken off, or a subtotal? | Taken off | **Add / Less** |
| Where does the amount come from? | 10% of the work this certificate | **Amount From**, **Rate (%)**, **% Of** |
| Does it stop at a ceiling over the whole contract? | Yes, at 5% of the contract value | **Limit**, **Limit (%)** |
| On which certificates does it appear? | All of them | **Applies To** |
| What is it? | Retention | **Role** |

### Step 2: Make the template

1. Open the **Construction MS** workspace.
2. In **Setup**, click **Certificate Templates**.
3. Click **+ Add BF Certificate Template**.
4. Type the **Template Name**, for example the client's name.
5. Set **Used For** = "Payment Certificate".
6. In **Description**, write the rules in words, for example "Retention 10% up to 5%, advance recovered 20% per certificate".
7. In the **Lines** table, add one row for each line of the client's certificate, in the same order.
8. For each row, fill in the fields from your answers in step 1.
9. Save. The system checks the lines. Correct any line it names.

The form shows only the fields that the line needs:

- **Amount From** shows when Add / Less is not "Subtotal".
- **Rate (%)** and **% Of** show when Amount From is "Percentage".
- **Line No.** shows when % Of is "Total at Line".
- **Limit (%)** shows when Limit is "% of Contract Value".

To start from a starter template instead: open it, click **... → Duplicate**, give it a new name, and change the lines.

### Step 3: Fill in each line

#### Line (the text)

The text printed on the certificate, for example "Less: Retention 10%". Make each line text different in the template.

The system matches lines between certificates by this text. "Previous certificates" amounts and typed amounts are found by the line text. Do not change the text of a line after the contract has certificates. See [Changing a template later](#changing-a-template-later).

#### Add / Less

| Value | What the line does |
| --- | --- |
| Add | Adds its amount to the running total |
| Less | Takes its amount from the running total |
| Subtotal | Shows the running total at this point. It does not change it. |

Always type positive amounts. This field gives the sign.

#### Amount From

| Amount From | The amount is | Templates |
| --- | --- | --- |
| Work This Certificate | The value of the work this certificate (measured work + claimed lump-sum variations) | Payment Certificate |
| Percentage | Rate (%) of the "% Of" value | All |
| Typed Amount | The amount the user types on the certificate | All |
| Total of Bills | The total of the BOQ | BOQ Summary |
| Provisional Sums | The total of the BOQ lines marked as provisional sums | BOQ Summary |
| Direct Cost | The direct cost of the budget | Budget Overheads |

#### % Of (for Percentage lines)

| % Of | Means |
| --- | --- |
| Work This Certificate | The work this certificate, with variations |
| Work This Certificate (excl. VAT-Exempt) | The same, without the VAT-exempt bills |
| Work to Date | All work certified up to and including this certificate |
| Running Total | The running total just above this line |
| Total at Line | The running total after the line in **Line No.** (the row number in the template) |
| Retention Held | Retention taken on earlier certificates and on the lines above, less retention released |
| Advance Balance | The contract's advance, less the recovery on earlier certificates and on the lines above |
| Contract Value | The contract's Total Contract Value |
| Total of Bills | The BOQ total (BOQ Summary only) |
| Direct Cost | The budget direct cost (Budget Overheads only) |
| BOQ Value | The contract value (Budget Overheads only) |

**The order of the lines matters.** "Running Total", "Retention Held" and "Advance Balance" include the lines above, on the same certificate. Put the retention line above the retention release line. Put the advance recovery above a line that recovers "the rest of the advance".

#### Less Earlier Certificates

Tick it to take off what this same line took on the earlier certificates. Use it with % Of = "Work to Date".

Example: "Advance recovery 30% of the work to date". Work to date is 10,000,000 and earlier certificates already recovered 2,000,000. The line gives 30% × 10,000,000 − 2,000,000 = 1,000,000.

#### Limit and Limit (%)

A limit is a ceiling over all certificates of the contract together. When the ceiling is reached, the line gives 0. When only part of the room is left, the line gives that part.

| Limit | The line stops at |
| --- | --- |
| % of Contract Value | Limit (%) of the Total Contract Value. Example: retention up to 5% of the contract. |
| Advance Payment | The advance not yet recovered. Use it on advance recovery. |
| Retention Held | The retention held. Use it on a typed retention release. |

When the line has a role, the limit counts all lines with the same role, on all certificates.

#### Applies To

| Applies To | The line is on |
| --- | --- |
| All Certificates | Every certificate |
| Interim Only | Interim certificates only |
| Substantial Completion | The Substantial Completion certificate only |
| Final | The Final certificate only |
| Substantial Completion and Final | Both of these |

A line that does not apply is left off the certificate.

#### Role

The role tells the system what a line is. The contract balances, the invoice and the reports read the role, not the line text. Give a role to each line that has one of these meanings:

| Role | Use it on | What the system does with it |
| --- | --- | --- |
| Work | The work line | Nothing extra. It marks the line for the reader. |
| Retention | The retention deduction | Adds it to "Retention Held" on the certificate and the contract. VAT on Net takes it off. |
| Retention Release | The line that pays retention back | Takes it off "Retention Held". Adds it to "Retention Released" on the contract. |
| Advance Recovery | The advance recovery | Adds it to "Advance Recovered" and lowers "Advance Balance". VAT on Net takes it off. |
| Advance Payment | A line that pays an advance on the certificate (FIDIC) | Nothing extra. It marks the line. The contract advance comes from the contract. |
| Materials on Site | Materials delivered but not used yet | Shows in "Materials on Site" on the certificate |
| Liquidated Damages | The delay penalty | Fetch Measurements puts the suggested amount on a typed line. Adds to "Liquidated Damages to Date" on the contract. |
| Late Payment Interest | Interest on late payments | Fetch Measurements puts the suggested interest on a typed line |
| VAT | BOQ Summary templates only | The contract takes this VAT off the bid price. A Payment Certificate template cannot have a VAT line. |

Use each role on the lines that really have that meaning. Without the role, the contract balances stay at 0.

#### For Calculation Only

The line changes the running total for the lines below, but the final amount leaves it out.

Example: a tender summary takes the provisional sums off to calculate a contingency, but the bid price still includes them. See [BOQ Summary templates](#boq-summary-templates).

### What the system checks when you save

| Check | Message |
| --- | --- |
| Amount From must suit the template kind. Example: "Total of Bills" on a Payment Certificate template. | Line X: '...' cannot be used on a ... template. |
| % Of must suit the template kind. Example: "Direct Cost" on a Payment Certificate template. | Line X: '...' cannot be used on a ... template. |
| A Percentage line needs a % Of. | Line X: choose what the percentage is of. |
| "Total at Line" must point to a line above. | Line X: Line No. must be one of the lines above. |
| "% of Contract Value" needs a Limit (%). | Line X: enter the Limit (%). |
| A Payment Certificate template cannot have a VAT line. | Line X: VAT is added to every certificate by the system... |

### Worked example: build a template and follow it over a contract

The client's contract says:

- Retention 10% of each certificate, up to 5% of the contract value.
- Advance payment 15% of the contract, recovered at 25% of each certificate.
- Half the retention back at Substantial Completion, the rest with the Final certificate.
- Liquidated damages taken off when the work is late.

**The template:**

| No. | Line | Add / Less | Amount From | Rate | % Of | Limit | Applies To | Role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Work done (this certificate) | Add | Work This Certificate | | | | All Certificates | Work |
| 2 | Less: Retention 10% (max 5% of contract) | Less | Percentage | 10 | Work This Certificate | % of Contract Value, 5% | All Certificates | Retention |
| 3 | Less: Advance recovery 25% | Less | Percentage | 25 | Work This Certificate | Advance Payment | All Certificates | Advance Recovery |
| 4 | Add: Release of 50% retention | Add | Percentage | 50 | Retention Held | | Substantial Completion | Retention Release |
| 5 | Add: Release of the remaining retention | Add | Percentage | 100 | Retention Held | | Final | Retention Release |
| 6 | Less: Liquidated damages | Less | Typed Amount | | | | All Certificates | Liquidated Damages |

**The contract:** Total Contract Value 10,000,000. Advance 1,500,000. VAT Status Exempt, so no VAT is added.

**What the certificates show:**

| Certificate | Work | Retention (line 2) | Advance recovery (line 3) | Release (line 4 or 5) | Amount due |
| --- | --- | --- | --- | --- | --- |
| IPC 1 (Interim) | 3,000,000 | 300,000 | 750,000 | not on this certificate | 1,950,000 |
| IPC 2 (Interim) | 4,000,000 | 200,000 (the 5% ceiling of 500,000 is reached) | 750,000 (the advance is fully recovered) | not on this certificate | 3,050,000 |
| IPC 3 (Interim) | 2,000,000 | 0 (ceiling reached) | 0 (nothing left to recover) | not on this certificate | 2,000,000 |
| Substantial Completion | 1,000,000 | 0 | 0 | 250,000 (50% of 500,000 held) | 1,250,000 |
| Final | 0 | 0 | 0 | 250,000 (100% of 250,000 still held) | 250,000 |

After the Final certificate, the contract shows Retention Held 0, Retention Released 500,000, Advance Recovered 1,500,000 and Advance Balance 0.

### Common rules and how to set them

**Retention of 10% on each certificate**

| Line | Add / Less | Amount From | Rate | % Of | Role |
| --- | --- | --- | --- | --- | --- |
| Less: Retention 10% | Less | Percentage | 10 | Work This Certificate | Retention |

**Retention of 5%, up to 5% of the contract**

Use the line above with Rate 5. Then set **Limit** = "% of Contract Value" and **Limit (%)** = 5.

**Retention not taken on VAT-exempt bills**

Use % Of = "Work This Certificate (excl. VAT-Exempt)".

**Half the retention back at completion, the rest at the final certificate**

| Line | Add / Less | Amount From | Rate | % Of | Applies To | Role |
| --- | --- | --- | --- | --- | --- | --- |
| Add: Release of 50% retention | Add | Percentage | 50 | Retention Held | Substantial Completion | Retention Release |
| Add: Release of the remaining retention | Add | Percentage | 100 | Retention Held | Final | Retention Release |

**Retention released against a bank guarantee (a typed amount)**

| Line | Add / Less | Amount From | Limit | Role |
| --- | --- | --- | --- | --- |
| Add: Release of retention | Add | Typed Amount | Retention Held | Retention Release |

The limit stops the user from releasing more than is held.

**Advance recovered as 20% of each certificate**

| Line | Add / Less | Amount From | Rate | % Of | Limit | Role |
| --- | --- | --- | --- | --- | --- | --- |
| Less: Advance recovery 20% | Less | Percentage | 20 | Work This Certificate | Advance Payment | Advance Recovery |

The limit stops the recovery when the advance is fully back.

**Advance recovered as 30% of the work to date**

| Line | Add / Less | Amount From | Rate | % Of | Less Earlier Certificates | Applies To | Role |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Less: Advance recovery 30% of work to date | Less | Percentage | 30 | Work to Date | Ticked | Interim Only | Advance Recovery |

**The rest of the advance at completion**

| Line | Add / Less | Amount From | Rate | % Of | Applies To | Role |
| --- | --- | --- | --- | --- | --- | --- |
| Less: Recovery of the remaining advance | Less | Percentage | 100 | Advance Balance | Substantial Completion and Final | Advance Recovery |

**Amounts the user types on each certificate**

Use Amount From = "Typed Amount" for materials on site, price adjustment, liquidated damages and late payment interest. Give each line its role. The typed amount stays on the line when you save again.

**Liquidated damages up to 10% of the contract**

| Line | Add / Less | Amount From | Limit | Limit (%) | Role |
| --- | --- | --- | --- | --- | --- |
| Less: Liquidated damages | Less | Typed Amount | % of Contract Value | 10 | Liquidated Damages |

**Retention on a subtotal (FIDIC style)**

1. Add the work line and the typed lines, for example price adjustment.
2. Add a **Subtotal** line.
3. Add the retention line with % Of = "Running Total".

**A percentage of the total after a given line**

Use % Of = "Total at Line" and type the template row number in **Line No.** The FIDIC starter template uses this: "Repayment of advance 15%" is 15% of the total after line 7.

### Test a new template

1. Set the template on a test contract with the same payment terms as the real one.
2. Make a certificate with the same work amount as a real certificate of the client.
3. Save, and compare each line with the client's paper certificate.
4. Correct the template, then change the certificate's template and save again to reload the lines.
5. Delete the test certificate. Do not submit it.

### Changing a template later

The lines are copied onto each certificate when it is made. So:

- **Submitted certificates** never change.
- **New certificates** use the changed template.
- **A draft certificate** keeps its old lines. To reload them, choose the template again or change the certificate type, then save.

Two rules keep the totals right after a change:

- **Do not change the text of a line** that earlier certificates used. The "Previous certificates" amount of a line comes from the earlier lines with the same text. Changed text starts again from 0. A limit on a line with no role also counts by the text.
- **Do not change the rules of a running contract** without the client's agreement. If the rules really change, duplicate the template, change the copy, and set the copy on the contract.

### VAT on certificates

VAT is not a template line. The system adds it from the contract:

| Contract setting | VAT |
| --- | --- |
| VAT Status = Standard Rated, VAT Basis = Gross Work | VAT Rate × the taxable work this certificate |
| VAT Status = Standard Rated, VAT Basis = Net after Deductions | VAT Rate × (taxable work − retention − advance recovery) |
| VAT Status = Exempt or Zero Rated | No VAT. The certificate prints the exemption reference. |

Taxable work does not include the bills marked as VAT exempt on the BOQ. The retention and advance recovery come from the lines with those roles.

### BOQ Summary templates

A BOQ Summary template calculates the **Bid Price** at the end of the BOQ, as on the Form of Tender. It uses the same fields as a payment template. Its amounts come from "Total of Bills", "Provisional Sums", "Percentage" and "Typed Amount".

The starter template "Tender Summary A-I":

| Line | Add / Less | Amount From | Rate | % Of | Options |
| --- | --- | --- | --- | --- | --- |
| A. Total of Bills | Add | Total of Bills | | | |
| B. Less specified provisional sums | Less | Provisional Sums | | | For Calculation Only |
| C. Sub-total (A - B) | Subtotal | | | | |
| D. Add provisional sum of physical contingency 10% | Add | Percentage | 10 | Running Total | |
| E. Sub-total (C + D) | Subtotal | | | | |
| F. Add provisional sum of variation of prices | Add | Typed Amount | | | |
| G. Sub-total (E + F) | Subtotal | | | | |
| H. Add VAT 18% of G | Add | Percentage | 18 | Running Total | Role: VAT |

Line B takes the provisional sums off only to calculate the contingency on line D. Because it is "For Calculation Only", the bid price still includes them: Bid Price = A + D + F + H.

Give the VAT line the role **VAT**. The contract then takes the VAT off the bid price to get the Contract Amount.

### Budget Overheads templates

A Budget Overheads template adds the overheads to the budget's direct cost. Its amounts come from "Direct Cost", "Percentage" (of Direct Cost, BOQ Value or Running Total) and "Typed Amount".

The starter template "Budget Overheads (Sengerema)":

| Line | Add / Less | Amount From | Rate | % Of |
| --- | --- | --- | --- | --- |
| Direct cost (resources) | Add | Direct Cost | | |
| Add: Contingency 10% | Add | Percentage | 10 | Direct Cost |
| Total + contingency | Subtotal | | | |
| Add: Supervision fee 14.13% | Add | Percentage | 14.13 | Direct Cost |
| Add: Equipment wear and tear | Add | Typed Amount | | |

---

## Invoices

- **Client Claim → Sales Invoice**: one line with the Default Progress Claim Item and the Amount Due (Excl. VAT). The VAT row has the certificate's exact VAT. The due date is the certificate's due date.
- **Subcontractor Claim → Purchase Invoice**: the same, for the subcontractor.
- **Advance payment**: from the contract, **Create → Advance Payment Invoice**.

The invoice total is always equal to the certificate to the cent. Rounding is off on these invoices.

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

**"Submit a Works Execution of type Mobilization for this contract before recording measurements"**

Make a Works Execution with the mobilization Activity Type. Complete its tasks and submit it.

**"Attach these documents and mark them Ready before submitting the certificate"**

A mandatory supporting document is missing. Attach it and set its status to "Ready".

**"Set a default Sales Taxes and Charges Template with the VAT account"**

The company has no default sales tax template. Make one with the VAT account and set it as default.

**A certificate line shows 0 when it should not**

Check the line's limit. The ceiling over the contract may be reached, for example retention up to 5%, or the advance is fully recovered. Also check **Applies To** and the certificate type.

**The contract's Retention Held or Advance Recovered stays at 0**

The template lines have no role. Give the retention line the role "Retention" and the recovery line the role "Advance Recovery".

**"Previous certificates" on a line shows 0, but earlier certificates had it**

The line text changed between certificates. Use the same text as on the earlier certificates.

**"Line X: VAT is added to every certificate by the system"**

A Payment Certificate template has a line with role VAT. Remove the line. The contract's VAT settings add VAT.

**The Connections tab of a BOQ is empty**

No document is linked to that BOQ yet. A contract, budget or certificate made from the BOQ shows there.

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
│   ├── task_activity.py              Task costs from the books
│   ├── boq_ai_import.py              AI import of BOQ files
│   ├── reminders.py                  Daily expiry reminders
│   ├── doctype/                      All BF DocTypes
│   ├── report/                       Script reports
│   └── print_format/                 BOQ and IPC print formats
├── templates/print/                  Shared IPC print parts
└── patches/                          Data patches
```

The certificate engine is `run_lines()` in `ipc.py`. The BOQ summary and the budget overheads use the same function.

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
