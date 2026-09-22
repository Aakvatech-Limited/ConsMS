# ConsMS — Construction Management for Frappe / ERPNext

ConsMS is a construction contract-management application built on the Frappe Framework and designed to work with ERPNext business documents.

The current `master` branch focuses on the commercial and execution lifecycle of construction projects: Bills of Quantities (BOQs), tenders, contracts, mobilization, site measurements, progress claims / IPCs, variation orders, procurement linkage, invoicing linkage, budget tracking, profitability analysis, dashboards, and project workspace navigation.

> This README documents the current `master` branch. It is materially different from the older ConsMS codebase that focused mainly on daily site progress, labour, materials, equipment logs, repairs, and handover records.

---

## Business Summary

Construction projects require commercial, project, procurement, site, and finance teams to work from the same contract quantities and values.

ConsMS is designed to provide that connection inside Frappe/ERPNext.

The application establishes a structured flow from:

```text
Project / BOQ
    ↓
Tender
    ↓
Contract
    ↓
Mobilization
    ↓
Site Measurements
    ↓
Progress Claim / IPC
    ↓
Sales Invoice or Purchase Invoice
```

Variation Orders can adjust the commercial value during execution, while purchasing transactions can be linked to BOQ lines to support budget-versus-expenditure control.

---

## Business Problems This App Addresses

| Business problem | ConsMS capability |
| --- | --- |
| Contract quantities and rates are maintained outside ERP | Structured Bills of Quantities with quantity, rate and amount calculations |
| Tender information is disconnected from awarded contracts | BOQ → Tender → Contract document mapping |
| Multiple contracts may accidentally be created for one tender | Backend validation enforces one active contract per tender |
| Contract mobilization is managed through spreadsheets or checklists | Configurable mobilization templates and site mobilization tracking |
| Site work measurement is difficult to reconcile with contract quantities | Site Measurement Logs reference BOQ items |
| Interim certificates are manually recalculated | Progress Claims calculate previous, current and cumulative quantities and values |
| Variations are disconnected from progress certification | Submitted variation orders are incorporated into progress claim calculations |
| Retention and certification calculations are spreadsheet-based | Progress Claim calculation logic includes retention, previous certification, VAT and net amount due |
| Construction purchasing cannot be compared cleanly to BOQ budgets | Procurement transaction items can carry BOQ and BOQ-line references |
| Management cannot easily see project commercial performance | BOQ Budget vs Expenditure and Contract Profitability reports |
| Construction processes are scattered across menus | Dedicated Construction MS workspace |

---

## Who This App Is For

ConsMS is designed for organizations involved in project and contract-based construction operations, including:

- Main contractors
- Civil and infrastructure contractors
- Building contractors
- Engineering companies
- Quantity surveying teams
- Commercial and contracts departments
- Project managers
- Site engineers
- Procurement teams
- Finance teams handling progress billing
- Organizations already using ERPNext for Projects, Buying, Selling and Accounts

---

## Who This App Is Not For

The current codebase should not automatically be treated as a complete replacement for every specialist construction platform.

Additional development or validation may be required for:

- tender evaluation and bid comparison
- subcontractor tendering
- advanced cost-code structures
- resource scheduling
- daily labour attendance
- plant fleet maintenance
- quality inspections
- HSE management
- document transmittals
- RFIs
- drawings and revision control
- extension-of-time claims
- liquidated damages
- defects liability management
- project cash-flow forecasting
- earned value management
- mobile offline site capture

---

# Core Construction Lifecycle

## 1. Bill of Quantities

**DocType:** `BF Bill of Quantities`

The BOQ provides the commercial baseline for the project.

Supported behavior includes:

- Project linkage
- BOQ line items
- quantity
- UOM
- unit rate
- line amount
- automatic BOQ total calculation
- import support
- submit / cancel / amend lifecycle
- creation of Material Request
- creation of Tender
- lookup of BOQ line items for downstream transactions

The BOQ controller recalculates each line as:

```text
Amount = Quantity × Unit Rate
```

and aggregates the total BOQ value.

---

## 2. Tender Management

**DocType:** `BF Tender`

Tenders can be generated from a BOQ.

The current application supports a controlled BOQ-to-contract path:

```text
BOQ → Tender → Contract
```

### Contract creation control

The backend prevents more than one active contract from being created for the same Tender.

Cancelled contracts are excluded from this restriction.

### Contract submittals

When a Contract is created from a Tender, the application can populate required contract submittals using configured `BF Document Type` records.

This provides a starting checklist for documents required during contract execution.

---

## 3. Contract Management

**DocType:** `BF Contract`

Contracts support both:

- Main Contract
- Subcontract

### Main contracts

A Main Contract can reference:

- Tender
- Project
- Client / Customer
- BOQ
- Contract amount
- Contingency percentage
- Contingency amount
- Retention percentage
- Total contract value
- Required submittals

### Subcontracts

Subcontracts can reference:

- Parent Main Contract
- Supplier / Subcontractor

This provides the basis for relating subcontractor commercial activity to the main contract.

### Contract value calculation

The application calculates:

```text
Contingency Amount = Contract Amount × Contingency %
Total Contract Value = Contract Amount + Contingency Amount
```

If contingency exceeds 15%, the application displays a warning for review.

### Downstream actions

From a Contract, users can create:

- Site Mobilization
- Variation Order
- Progress Claim

---

# Site Mobilization

## BF Site Mobilization

Site mobilization provides a checklist-based mechanism for ensuring the project is ready for execution.

The application supports mobilization statuses such as:

- Not Started
- In Progress
- Completed

The status is calculated from checklist items.

### Submission control

A Site Mobilization document cannot be submitted until **all mobilization tasks are completed**.

This provides a business control preventing formal mobilization closure while outstanding tasks remain.

---

## Mobilization Templates

**DocTypes:**

- `BF Mobilization Template`
- `BF Mobilization Template Task`
- `BF Mobilization Task`

Templates allow organizations to standardize recurring mobilization requirements.

Typical business uses may include:

- site possession
- insurance documentation
- permits
- temporary utilities
- site offices
- safety setup
- equipment mobilization
- statutory documents
- staff deployment

Actual template content is configurable by the organization.

---

# Site Measurement

## BF Site Measurement Log

Site Measurement Logs are used to capture measured work against BOQ items.

The application supports:

- Contract linkage
- BOQ-based item selection
- measurement items
- retrieval of BOQ descriptions and UOM
- controlled BOQ-item lookup

These measurements feed the progress-claim process.

---

# Progress Claims / IPC

## BF Progress Claim

Progress Claims are one of the main commercial controls in ConsMS.

A claim can be generated from a Contract.

The current logic supports:

- Claim period
- BOQ claim items
- Previous quantity
- This-period quantity
- Cumulative quantity
- Unit rate
- This-period value
- Cumulative value
- Materials on site
- Approved variations
- Retention
- Advance payment recovery
- Previous certified amount
- Net amount due
- VAT
- Total amount certified

---

## Measurement-Based Claim Generation

The Progress Claim can fetch submitted Site Measurement Logs for a selected period.

The application:

1. Loads the Contract BOQ.
2. Retrieves BOQ items.
3. Finds submitted Site Measurement Logs for the Contract and claim period.
4. Aggregates measured quantities.
5. Retrieves quantities already claimed in earlier submitted claims.
6. Calculates current and cumulative quantities.
7. Retrieves approved Variation Orders.
8. Calculates previous variation certification.
9. Calculates the resulting claim values.

This creates a direct operational link:

```text
BOQ
  ↓
Site Measurement
  ↓
Progress Claim / IPC
```

---

## Claim Period Control

The application prevents:

- `Period From` being later than `Period To`
- overlapping active Progress Claim periods for the same Contract

This reduces duplicate certification periods.

---

## Variation Claim Control

For each Variation Order:

```text
Cumulative Variation Claim
=
Previously Certified
+
This Period Amount
```

The application prevents cumulative claimed value from exceeding the approved/requested variation amount.

---

## Progress Claim Calculations

The application calculates values approximately as follows:

```text
This Period Work Value
=
This Period Quantity × Unit Rate
```

```text
Cumulative Quantity
=
Previous Quantity + This Period Quantity
```

```text
Cumulative Work Value
=
Cumulative Quantity × Unit Rate
```

```text
Gross Valuation
=
Work Executed
+ Approved Variations
+ Materials on Site
```

```text
Retention Deduction
=
Gross Valuation × Retention %
```

```text
Net Amount Due
=
Gross Valuation
- Retention
- Advance Recovery
- Previous Certified Amount
```

```text
VAT
=
Net Amount Due × VAT %
```

```text
Total Amount Certified
=
Net Amount Due + VAT
```

---

# ERPNext Invoice Integration

The Progress Claim controller includes mappings for:

- Sales Invoice
- Purchase Invoice

### Main-contract billing

A Progress Claim can generate a Sales Invoice conceptually linked to:

- Project
- Construction Contract
- Progress Claim

### Subcontractor claims

A Progress Claim can also generate a Purchase Invoice for subcontractor-side certification.

The default invoice item is read from **BF Construction Settings**.

> Deployment note: the current `master` branch contains intended Sales Invoice custom-field definitions in `consms/custom_fields.py`, but `hooks.py` assigns `after_migrate` twice. In Python, the later assignment takes precedence. The active hook currently points to `consms.setup.after_migrate`. Deployments should verify the intended invoice linkage fields exist before relying on invoice generation.

---

# Variation Orders

## BF Variation Order

Variation Orders provide structured control of additions or changes to contract scope.

They support:

- Project
- Contract
- Variation items
- Quantity
- Unit rate
- Amount
- Requested amount
- Reason / justification
- submit / cancel / amend lifecycle

The requested amount is calculated automatically from the variation lines.

Variation Orders are also incorporated into Progress Claim calculations.

---

# BOQ-Linked Procurement

The application extends ERPNext procurement documents to support BOQ linkage.

The active `consms.setup.after_migrate` routine creates BOQ fields on:

### Parent transactions

- Material Request
- Purchase Order
- Purchase Receipt
- Purchase Invoice

### Child transaction rows

- Material Request Item
- Purchase Order Item
- Purchase Receipt Item
- Purchase Invoice Item

Child rows can reference:

- BF Bill of Quantities
- BF BOQ Item
- BOQ Item ID

This establishes the basis for tracing procurement commitments and expenditures back to individual BOQ lines.

---

## Material Request Integration

The app includes custom JavaScript for Material Request and extends the Material Request dashboard.

A BOQ can generate a Material Request with:

- Purchase request type
- Project
- BOQ reference

The Material Request dashboard also receives a Construction section linking back to the BOQ.

---

# Reporting and Management Visibility

## BOQ Budget vs Expenditure

**Report:** `BOQ Budget vs Expenditure`

The report compares each BOQ line against ERPNext procurement values.

It includes:

- BOQ
- Project
- BOQ Item
- Description
- UOM
- Budget Quantity
- Unit Rate
- Budget Amount
- Committed Cost from submitted Purchase Orders
- Actual Spend from submitted Purchase Invoices
- Remaining Budget
- Utilization %

This provides a construction-specific view of:

```text
BOQ Budget
vs
Purchase Commitment
vs
Actual Purchase Cost
```

---

## Contract Profitability

**Report:** `BF Contract Profitability`

For submitted Main Contracts, the report calculates:

- Base Contract Value
- Submitted Variations
- Revised Contract Value
- Client Billing
- Subcontractor Costs
- Estimated Profit
- Actual Profit to Date
- Actual Margin %

The report derives client billing from submitted Sales Invoices linked to the Contract.

Subcontractor cost is derived from submitted Purchase Invoices linked either to:

- the Main Contract, or
- submitted Subcontracts belonging to that Main Contract

This creates a high-level commercial performance view by Contract.

---

## Variation vs Budget Report

The repository also includes a `Variation vs Budget Report` definition for construction variance visibility.

Review its final business logic against the organization's reporting requirements before production rollout.

---

# Construction Workspace

The app includes a public **Construction MS** workspace.

It groups functionality into:

## Pre-Construction

- Bill of Quantities
- Tenders
- Contracts

## Execution

- Mobilization
- Variation Orders
- Measurement Logs
- Progress Claims (IPC)

## Configuration

- Document Types
- Mobilization Templates
- Construction Settings

The workspace also includes construction dashboard content such as Monthly Contract Awards.

---

# Dashboard Components

The repository contains dashboard resources including:

### Dashboard Charts

- Monthly Contract Awards
- Submittal Approval Rate

### Number Cards

- Active Tenders
- Pending Submittals
- Total Awarded Contracts
- Total Variation Value

These provide management-level visibility directly from the Construction workspace.

---

# Contract Submittals

Contracts contain a submittal table.

Configured `BF Document Type` records can be automatically copied into newly created contracts as required submittals.

This can support tracking of required contract documentation such as:

- insurance documents
- drawings
- method statements
- bonds
- permits
- material approvals
- certificates

The exact document types are organization-configurable.

---

# FIDIC-Oriented Output

The repository includes a print format:

```text
FIDIC IPC Certificate
```

This indicates an intended construction certification workflow aligned with interim payment certificate usage.

The presence of the print format should not be interpreted as legal or contractual compliance with every FIDIC contract form; each deployment should validate terminology, deductions, taxes and certificate format against the actual contract.

---

# Construction Settings

**DocType:** `BF Construction Settings`

The application includes construction-level configuration.

One known use is the default Item used when converting a Progress Claim into an ERPNext invoice.

Review Construction Settings during implementation before users begin generating invoices.

---

# Main DocTypes

| DocType | Purpose |
| --- | --- |
| BF Bill of Quantities | Commercial baseline and BOQ lines |
| BF BOQ Item | BOQ detail row |
| BF Tender | Tender linked to BOQ and Project |
| BF Contract | Main Contract or Subcontract |
| BF Contract Submittal | Required contract documents |
| BF Document Type | Configurable submittal/document categories |
| BF Site Mobilization | Mobilization checklist and completion control |
| BF Site Mobilization Item | Mobilization detail |
| BF Mobilization Template | Standard mobilization template |
| BF Mobilization Template Task | Template detail |
| BF Mobilization Task | Mobilization task definition |
| BF Site Measurement Log | Site measurement transaction |
| BF Measurement Item | BOQ measurement row |
| BF Progress Claim | Interim progress claim / IPC |
| BF Progress Claim Item | BOQ certification detail |
| BF Progress Claim Variation | Variation certification detail |
| BF Variation Order | Contract variation |
| BF Variation Item | Variation detail |
| BF Construction Settings | Construction configuration |

---

# ERPNext Integration

ConsMS relies heavily on standard ERPNext master and transaction DocTypes.

Current references include:

- Project
- Customer
- Supplier
- Item
- UOM
- Material Request
- Material Request Item
- Purchase Order
- Purchase Order Item
- Purchase Receipt
- Purchase Receipt Item
- Purchase Invoice
- Purchase Invoice Item
- Sales Invoice

Because these are core ERPNext objects, this branch should be treated as an **ERPNext-integrated Frappe application**, even though `required_apps` is not currently enforced in `hooks.py`.

---

# App Mode

**ERPNext-integrated Frappe application**

The app technically declares itself as a Frappe package, but its operational workflows depend on ERPNext DocTypes and accounting/procurement transactions.

Production deployment should therefore assume ERPNext is required unless the code is refactored to remove these dependencies.

---

# Compatibility

## Current repository evidence

- Python: `>=3.10`
- Packaging: modern `pyproject.toml` / Flit
- App package: `consms`
- Project package name: `construction_ms`
- Module: `Construction Management`
- License: MIT
- Development tooling:
  - Ruff
  - ESLint
  - Prettier
  - Pyupgrade
  - pre-commit

## Frappe / ERPNext version

The current `pyproject.toml` does not declare an explicit supported Frappe version.

Before production installation, confirm compatibility with the target:

- Frappe version
- ERPNext version
- Python version
- MariaDB version
- Node version

---

# Installation

From a Frappe Bench:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Aakvatech-Limited/ConsMS.git --branch master
bench --site <site-name> install-app consms
bench --site <site-name> migrate
```

For production deployments, pin a tested commit or release rather than installing an unpinned moving branch.

---

# Configuration Checklist

Before using ConsMS:

1. Configure Company and ERPNext accounting.
2. Create Customers and Suppliers.
3. Configure Projects.
4. Create Items and UOMs.
5. Configure the default Progress Claim invoice Item in BF Construction Settings.
6. Configure BF Document Types for required contract submittals.
7. Configure Mobilization Templates where applicable.
8. Review Contract retention and contingency defaults.
9. Validate VAT handling against local tax requirements.
10. Confirm invoice integration custom fields exist.
11. Test permissions for each business role.
12. Validate print formats, especially IPC certification.
13. Validate procurement-to-BOQ linkage before live purchasing.

---

# Permissions

Most construction DocTypes in the current repository expose broad permissions to **System Manager**.

This is suitable for development but is not sufficient as a final production authorization model.

Before go-live, define operational roles such as:

- Quantity Surveyor
- Contracts Manager
- Commercial Manager
- Project Manager
- Site Engineer
- Procurement User
- Procurement Manager
- Finance User
- Finance Manager
- Construction Administrator

Then assign create, write, submit, cancel and amend privileges according to segregation-of-duties requirements.

---

# Business Controls Already Present

The current code includes several useful business controls:

- One active Contract per Tender
- Site Mobilization cannot submit until all tasks are completed
- Progress Claim periods cannot overlap for the same Contract
- Progress Claim date ranges must be valid
- Variation claims cannot exceed approved variation values
- BOQ amounts recalculate from quantity × rate
- Variation Order amounts recalculate from quantity × rate
- Contract contingency is calculated automatically
- High contingency values generate a warning
- Progress Claims derive quantities from submitted Site Measurement Logs
- Previous certified quantities are carried forward into later claims

---

# Reports and Dashboards

| Component | Type |
| --- | --- |
| BF Contract Profitability | Script Report |
| BOQ Budget vs Expenditure | Script Report |
| Variation vs Budget Report | Report definition |
| Monthly Contract Awards | Dashboard Chart |
| Submittal Approval Rate | Dashboard Chart |
| Active Tenders | Number Card |
| Pending Submittals | Number Card |
| Total Awarded Contracts | Number Card |
| Total Variation Value | Number Card |

---

# APIs and Server Methods

The application exposes whitelisted server-side methods supporting mapped-document and transactional workflows, including:

- BOQ → Material Request
- BOQ → Tender
- Tender → Contract
- Contract → Site Mobilization
- Contract → Variation Order
- Contract → Progress Claim
- Progress Claim measurement retrieval
- Progress Claim → Sales Invoice
- Progress Claim → Purchase Invoice
- BOQ item search/filtering

These methods are designed to be called from Frappe client-side forms.

---

# Hooks and Events

Active application hooks currently include:

### Material Request client script

```python
doctype_js = {
    "Material Request": "public/js/material_request.js"
}
```

### Post-migration setup

The effective current hook is:

```python
after_migrate = "consms.setup.after_migrate"
```

### Material Request dashboard override

```python
override_doctype_dashboards = {
    "Material Request": "consms.setup.get_material_request_dashboard"
}
```

### Important implementation note

`hooks.py` currently contains two `after_migrate` assignments.

The later assignment overrides the earlier one.

This should be reviewed before relying on automatic creation of every intended custom field.

---

# Custom Fields

The active setup routine creates BOQ references on standard ERPNext procurement documents.

The repository also contains a separate `consms/custom_fields.py` definition for Sales Invoice fields:

- Construction Contract
- Progress Claim (IPC)

Because of the duplicate `after_migrate` hook assignment described above, deployments should confirm whether these fields are present on the target site.

---

# Background Jobs

No active scheduler events are currently configured in `hooks.py`.

The core application operates primarily through:

- DocType validation
- mapped document actions
- whitelisted server calls
- standard Frappe transactions
- reports
- workspace/dashboard resources

---

# Migrations

`consms/patches.txt` currently contains the standard pre-model-sync and post-model-sync sections but no active migration patches.

Most current setup is performed through DocType synchronization and `after_migrate`.

---

# Developer Setup

Clone/install through Bench, then enable the repository's development tooling.

```bash
cd apps/consms
pre-commit install
```

Configured tooling includes:

- Ruff
- ESLint
- Prettier
- Pyupgrade

Run the relevant Frappe test suite against the target framework version before merging functional changes.

---

# Repository Structure

```text
ConsMS/
├── .github/
│   └── workflows/
├── README.md
├── license.txt
├── pyproject.toml
├── consms/
│   ├── hooks.py
│   ├── setup.py
│   ├── custom_fields.py
│   ├── patches.txt
│   ├── public/
│   │   └── js/
│   │       └── material_request.js
│   └── construction_management/
│       ├── doctype/
│       │   ├── bf_bill_of_quantities/
│       │   ├── bf_boq_item/
│       │   ├── bf_tender/
│       │   ├── bf_contract/
│       │   ├── bf_contract_submittal/
│       │   ├── bf_document_type/
│       │   ├── bf_site_mobilization/
│       │   ├── bf_site_mobilization_item/
│       │   ├── bf_mobilization_template/
│       │   ├── bf_mobilization_template_task/
│       │   ├── bf_mobilization_task/
│       │   ├── bf_site_measurement_log/
│       │   ├── bf_measurement_item/
│       │   ├── bf_progress_claim/
│       │   ├── bf_progress_claim_item/
│       │   ├── bf_progress_claim_variation/
│       │   ├── bf_variation_order/
│       │   ├── bf_variation_item/
│       │   └── bf_construction_settings/
│       ├── report/
│       ├── dashboard_chart/
│       ├── number_card/
│       ├── print_format/
│       └── workspace/
└── ...
```

---

# Before and After

| Traditional process | With ConsMS |
| --- | --- |
| BOQ managed in spreadsheet | BOQ stored in Frappe |
| Tender recreated manually | Tender mapped from BOQ |
| Awarded contract entered separately | Contract mapped from Tender |
| Mobilization checklist maintained externally | Mobilization tracked in dedicated DocType |
| Site measurements kept in books/spreadsheets | Measurement Log linked to BOQ |
| IPC prepared manually | Claim generated from measurements and prior claims |
| Variations managed separately | Variations linked to Contract and IPC |
| Procurement disconnected from BOQ | ERPNext procurement rows linked to BOQ items |
| Budget control calculated manually | BOQ Budget vs Expenditure report |
| Contract profitability assembled offline | Contract Profitability report |

---

# Example End-to-End Business Workflow

### Pre-Construction

1. Create Project.
2. Create BOQ.
3. Add BOQ quantities and unit rates.
4. Submit BOQ.
5. Create Tender from BOQ.
6. Award Tender and create Contract.

### Mobilization

7. Create Site Mobilization from Contract.
8. Load mobilization checklist.
9. Complete all mobilization tasks.
10. Submit Mobilization.

### Procurement

11. Create Material Request from BOQ.
12. Carry BOQ references into purchasing transactions.
13. Track commitments and expenditures against BOQ items.

### Execution and Measurement

14. Record Site Measurement Logs.
15. Select BOQ lines.
16. Enter measured quantities.
17. Submit measurements.

### Certification

18. Create Progress Claim from Contract.
19. Select certification period.
20. Fetch measured quantities.
21. Review previous quantities.
22. Review approved variations.
23. Apply materials on site, retention and recoveries.
24. Submit the Progress Claim.

### Finance

25. Generate Sales Invoice for client claim or Purchase Invoice for subcontractor claim, subject to deployment validation of the required custom fields.
26. Review contract profitability and BOQ budget-versus-expenditure reports.

---

# Expected Business Outcomes

With appropriate implementation and controls, ConsMS can help organizations improve:

- contract traceability
- BOQ control
- procurement budget visibility
- measurement discipline
- progress certification consistency
- variation control
- retention calculation
- commercial reporting
- contract profitability visibility
- integration between site, procurement and finance teams
- auditability of construction commercial records

---

# Implementation Effort

Implementation effort will depend on:

- complexity of BOQs
- number of active contracts
- subcontract structure
- existing ERPNext configuration
- procurement processes
- tax rules
- certification rules
- retention practices
- advance payment terms
- role and approval structure
- reporting requirements
- historical migration needs

A pilot project should be completed before migrating all live construction contracts.

---

# Data Migration Considerations

For existing construction projects, consider migration of:

- Projects
- BOQs
- BOQ line identifiers
- Tenders
- Main Contracts
- Subcontracts
- Approved Variation Orders
- Previous certified quantities
- Previous certified amounts
- retention balances
- advance-payment recovery balances
- procurement commitments
- historic invoices

Opening commercial balances must be designed carefully to avoid double-counting previous certification.

---

# Risks and Considerations

## 1. Explicit ERPNext dependency is not declared

The application depends on multiple ERPNext DocTypes but `required_apps` is not currently configured.

## 2. Duplicate after_migrate declaration

`hooks.py` assigns `after_migrate` twice. Only the latter assignment is effective.

## 3. Invoice linkage must be validated

Progress Claim invoice creation expects construction linkage fields. Confirm these fields exist on Sales Invoice and Purchase Invoice in the target deployment.

## 4. Permissions are currently development-oriented

Many custom DocTypes primarily grant access to System Manager. Production role design is required.

## 5. Tax and contractual formulas require localization

Retention, VAT, advance recovery and certification formulas must be validated against:

- contract conditions
- jurisdiction
- tax treatment
- client requirements

## 6. Frappe version constraints are not declared

Test the app on the intended Frappe/ERPNext release before production use.

## 7. Some report queries use direct SQL

Review reporting code for:

- permission behavior
- SQL safety
- multi-company behavior
- currency handling
- performance on large datasets

---

# Security

ConsMS inherits Frappe's authentication, roles and document permission model.

Production deployment should additionally review:

- who can amend BOQs
- who can submit Contracts
- who can approve Variations
- who can submit Measurements
- who can submit Progress Claims
- who can generate invoices
- who can edit rates
- who can access profitability information
- who can cancel commercial documents

Commercial construction records should use strong segregation of duties.

---

# Upgrade Guide

Before upgrading:

1. Take a database and file backup.
2. Review the target ConsMS commit.
3. Confirm Frappe and ERPNext compatibility.
4. Review schema/custom-field changes.
5. Run migration on a staging site.
6. Validate BOQ mappings.
7. Validate Material Request and procurement links.
8. Test Progress Claim calculations.
9. Test invoice generation.
10. Review reports.
11. Test dashboards/workspace.
12. Run automated and manual regression tests.
13. Upgrade production only after acceptance.

---

# Troubleshooting

## BOQ fields do not appear in procurement documents

Run:

```bash
bench --site <site-name> migrate
```

Then verify the effective `after_migrate` hook and Custom Field records.

## Progress Claim invoice creation fails on missing fields

Confirm the target invoice DocType contains the custom linkage fields expected by the controller.

## Progress Claim has no quantities

Verify:

- Contract has a BOQ
- Site Measurement Logs are submitted
- measurement dates fall within the claim period
- measurement items reference the correct BOQ lines

## Site Mobilization cannot submit

Every checklist row must have status `Completed`.

## Contract cannot be created from Tender

Check whether another non-cancelled Contract already references the Tender.

---

# Decision Guide

ConsMS is a strong candidate for organizations that want construction commercial control directly inside ERPNext and need a connected flow between:

- BOQ
- Tender
- Contract
- Procurement
- Measurement
- Variation
- Progress Claim
- Invoice
- Profitability

It is especially relevant where ERPNext is already being used for accounting, buying, selling and project management.

Before enterprise rollout, complete a functional and technical validation covering:

- contract terms
- tax rules
- user permissions
- workflows
- approval levels
- invoice mapping
- BOQ procurement controls
- performance
- reporting
- localization

---

# Frequently Asked Business Questions

## Can ConsMS manage a BOQ?

Yes. The current `master` branch includes BOQ headers and BOQ items with automatic quantity × rate calculations.

## Can a BOQ create a Tender?

Yes.

## Can a Tender create a Contract?

Yes, and the backend prevents more than one active Contract per Tender.

## Does it support subcontracts?

Yes. `BF Contract` supports both Main Contract and Subcontract types.

## Can we track contract variations?

Yes. Variation Orders are linked to Contracts and are incorporated into Progress Claims.

## Does it support site measurements?

Yes. Site Measurement Logs reference BOQ items and feed claim quantities.

## Does it support IPC / Progress Claims?

Yes. The app includes cumulative measurement, retention, variations, advance recovery, previous certification, VAT and certification calculations.

## Can a claim generate an ERPNext invoice?

The controller includes mappings for Sales Invoice and Purchase Invoice. The required custom invoice fields should be verified during deployment.

## Can procurement be tracked against BOQ lines?

Yes. Custom fields are created on key ERPNext procurement documents and their child rows.

## Can management see budget vs spend?

Yes. The BOQ Budget vs Expenditure report compares BOQ budget, Purchase Orders and Purchase Invoices.

## Can management see contract profitability?

Yes. The Contract Profitability report compares revised contract value, client billing and subcontractor costs.

## Does it include a construction workspace?

Yes.

---

# Repository Evidence Reviewed

This README was prepared from the current `master` branch, including:

- `README.md`
- `pyproject.toml`
- `license.txt`
- `consms/hooks.py`
- `consms/setup.py`
- `consms/custom_fields.py`
- `consms/patches.txt`
- Construction Management workspace
- BOQ DocTypes and controller
- Tender DocType and controller
- Contract DocType and controller
- Contract Submittal structures
- Mobilization DocTypes and controller
- Site Measurement DocTypes and controller
- Progress Claim DocTypes and controller
- Variation Order DocTypes and controller
- Contract Profitability report
- BOQ Budget vs Expenditure report
- dashboard charts
- number cards
- FIDIC IPC Certificate print format
- Material Request integration
- repository automation and developer tooling

---

# Recommended Next Technical Improvements

The following items should be considered before treating the app as production-hardened:

1. Declare supported Frappe/ERPNext dependencies in `pyproject.toml`.
2. Remove the duplicate `after_migrate` assignment and consolidate custom-field setup.
3. Verify/create Contract and Progress Claim linkage fields on both Sales Invoice and Purchase Invoice.
4. Add production business roles and permissions.
5. Add workflow approvals for BOQ, Tender, Contract, Variation and IPC where required.
6. Expand automated tests beyond basic generated DocType tests.
7. Test cumulative IPC calculations using multi-period scenarios.
8. Add negative tests for over-certification and overlapping periods.
9. Review direct SQL reports for security and performance.
10. Add multi-company and multi-currency test coverage.
11. Document the intended supported Frappe/ERPNext release.
12. Add screenshots and an implementation example.

---

# Contributing

This repository uses `pre-commit` for development quality controls.

Install it with:

```bash
cd apps/consms
pre-commit install
```

Configured tools include:

- Ruff
- ESLint
- Prettier
- Pyupgrade

Submit changes through a feature/fix branch and Pull Request.

Changes should include appropriate tests where business logic is modified.

---

# License

MIT License.

See `license.txt`.

---

# Maintainers

ConsMS is maintained within the Aakvatech ecosystem.

Repository:

```text
https://github.com/Aakvatech-Limited/ConsMS
```
