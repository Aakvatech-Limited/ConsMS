# ConsMS — Construction Management Solution

ConsMS is a Frappe-based construction management application by Aakvatech. It extends project operations with structured site-progress recording, labour/material/equipment usage, plant operation logs, repair requisitions, and handover records.

## Business Summary

Construction teams often manage daily site progress, labour deployment, equipment usage, material consumption, breakdowns, and project handovers in separate spreadsheets or paper registers. ConsMS brings those operational records into Frappe so they can be linked to projects, tasks, employees, items, and project roles.

The current repository focuses on field-operational control rather than a full construction ERP stack. It is designed to complement the broader Frappe/ERPNext project, item, employee, and maintenance ecosystem.

## Business Problems This App Solves

| Business problem | ConsMS capability |
| --- | --- |
| Daily site progress is recorded informally | Daily Work Progress documents standardize project, date, shift, weather, site condition, task progress, labour, material, and equipment usage |
| Site costs are difficult to trace back to activities | Task, material, labour, and equipment rows include quantity/rate/cost fields |
| Equipment operation is poorly documented | Plant and Equipment Operation Log Sheet records operating hours, standby, breakdown time, fuel, oil, rate, amount, supervisor, and remarks |
| Repair needs are communicated informally | Equipment Repair Requisition captures equipment, requester, required materials/services, and estimated values |
| Handover records are inconsistent | Handing Over records formalize parties, supervising officer, witness, date, location, items, quantities, and status remarks |
| Project information is disconnected | Core records link to standard Project, Task, Item, Employee, UOM and related master data |

## Who This App Is For

ConsMS is suitable for organizations that operate projects with site-based work and want structured operational records inside Frappe, including:

- Construction contractors
- Civil works companies
- Engineering and infrastructure project teams
- Project managers and site supervisors
- Equipment and maintenance teams
- Organizations already using Frappe/ERPNext project and item masters

## Who This App Is Not For

The current repository does not, by itself, provide a complete construction accounting, estimating, BOQ, procurement, subcontractor billing, retention, variation-order, or contract-management suite.

Those capabilities may be implemented separately through ERPNext or other custom applications.

## Key Business Benefits

- Creates a single operational record of daily site activity
- Improves traceability of labour, materials, tasks, and equipment against projects
- Captures weather and site-condition context for daily work
- Records plant utilization, standby time, breakdown hours, fuel, and operating cost
- Formalizes equipment repair requests
- Provides auditable handover documentation
- Uses Frappe permissions, submission workflow behavior, print/export/report capabilities, and change tracking
- Reuses standard Frappe/ERPNext-linked masters instead of duplicating them

## Before and After

| Before | With ConsMS |
| --- | --- |
| Daily progress captured in notebooks or spreadsheets | Daily Work Progress is stored as a project-linked Frappe document |
| Equipment hours and fuel usage tracked separately | Operating hours, standby, breakdown, fuel, oil, and cost are recorded together |
| Repair requirements shared by calls or messages | Equipment Repair Requisitions provide a formal record |
| Labour/material usage is difficult to reconcile | Usage rows are attached directly to daily work records |
| Handover details depend on ad-hoc documents | Handover records use structured parties, items, quantities, and status remarks |
| Site records lack role-based access | Frappe roles control create, read, write, submit, cancel, print, export, and reporting rights |

## Typical Use Cases

### 1. Daily site progress recording

A project team creates a Daily Work Progress document for a project, date, and work shift. The document can capture:

- Weather
- Site condition
- Task progress
- Equipment used
- Materials utilized
- Labour utilized
- Task, equipment, material, labour, and overall cost values

### 2. Plant and equipment operation logging

A site or equipment team records:

- Project
- Plant/equipment item
- Hirer
- Operator
- Supervisor
- Start and end times
- Standby hours
- Breakdown hours
- Total hours
- Rate and amount
- Fuel type
- Fuel quantity
- Oil quantity
- Weather
- Task/section
- Remarks

### 3. Equipment repair requisition

Maintenance users can raise repair requisitions containing:

- Equipment
- Requesting employee
- Date
- Required materials/services
- Quantity
- Rate
- Amount
- Total amount

### 4. Project/site handover

A handover document can capture:

- Location
- Person handing over
- Person receiving
- Supervising officer
- Witness
- Date
- Items
- UOM
- Quantity
- Status or remarks

## Example Business Workflow

1. Create or maintain the Project and Task structure.
2. Maintain Item, Employee and UOM masters as required.
3. Record Daily Work Progress for each project shift/day.
4. Capture task activity, material use, labour use, and equipment use.
5. Record plant/equipment operating hours separately where detailed utilization tracking is needed.
6. Raise Equipment Repair Requisitions when maintenance is required.
7. Record site or asset handovers using Handing Over documents.
8. Use Frappe list views, reports, exports, print formats, permissions, and audit trail for operational review.

## Key Features

### Daily Work Progress

The Daily Work Progress DocType is a submittable transaction linked to a Project.

It includes:

- Project
- Date
- Work shift
- Weather
- Site condition
- Task Progress child table
- Equipment Record child table
- Material Utilised child table
- Labour Utilised child table
- Cost totals
- Amendment support
- Change tracking

The document naming pattern is based on project, date, and work shift.

### Task Progress

The DWP Task child table supports:

- Task
- Work section
- Unit
- Quantity
- Rate
- Amount

### Equipment Usage

The DWP Equipment child table supports:

- Equipment/item
- Activity
- Maintenance remarks
- Fuel type
- Fuel quantity
- Oil quantity
- Start/end time
- Standby hours
- Effective hours
- Rate
- Amount

### Material Usage

The DWP Material child table supports:

- Item
- UOM
- Quantity
- Rate
- Amount

### Labour Usage

The DWP Labour child table supports:

- Labour/item reference
- Activity
- Number of staff
- Daily cost
- Effective time
- Staff difficulties/inconveniences
- Remarks

### Equipment Repair Requisition

The Equipment Repair Requisition DocType supports:

- Equipment Item
- Requested By Employee
- Date
- Material and Service Required child table
- Total amount
- Submit/cancel lifecycle
- Maintenance Manager and Maintenance User permissions

### Plant and Equipment Operation Log Sheet

The operation log supports:

- Project
- Equipment/item
- Hirer
- Operator
- Supervisor
- Start/end time
- Standby hours
- Breakdown hours
- Total operating hours
- Rate and amount
- Fuel and oil usage
- Weather
- Task/section
- Remarks

### Handing Over

The Handing Over DocType supports:

- Location
- Handing-over employee
- Receiving employee
- Supervising officer
- Witness
- Date
- Item-level handover detail
- Quantity
- UOM
- Status/remarks
- Submit/cancel lifecycle

## Frappe / ERPNext Integration

ConsMS is built as a Frappe app but several DocTypes reference standard business objects commonly provided by ERPNext or related Frappe apps.

Current links include:

| ConsMS area | Standard linked DocType |
| --- | --- |
| Daily Work Progress | Project |
| Task progress | Task |
| Equipment/material | Item |
| Material and handover details | UOM |
| Plant operation | Employee |
| Handover | Employee |
| Equipment repair | Employee |

Because these links are used throughout the application, deployments should confirm that the required linked DocTypes exist in the target site.

## App Mode

**Frappe application with ERPNext-style project/master-data dependencies.**

The Python requirements file declares Frappe. However, the repository also references standard DocTypes such as Project, Task, Item, Employee, Supplier and UOM. In most practical deployments this means the app is expected to run alongside ERPNext or another installed application providing those DocTypes.

## Compatibility

### Current repository evidence

- App version: `0.0.1`
- Framework dependency declared: `frappe`
- Packaging style: legacy `setup.py`
- Primary module: `Construction`
- License: GPL
- Original DocType metadata dates from 2020

### Version caution

The repository does not currently declare modern Frappe version constraints in a `pyproject.toml`.

Before deploying to a current Frappe/ERPNext version, validate:

- Frappe compatibility
- ERPNext compatibility
- linked standard DocTypes
- role availability
- schema migration
- client-side behavior
- automated tests

## Installation

From your bench directory:

```bash
bench get-app https://github.com/Aakvatech-Limited/ConsMS.git
bench --site <your-site> install-app consms
bench --site <your-site> migrate
```

For production use, install from the branch that your deployment team has validated for your Frappe version.

## Configuration

The repository currently has no dedicated Settings DocType.

Configuration is primarily driven by:

- standard Frappe users and roles
- linked Project, Task, Item, Employee, Supplier and UOM data
- DocType permissions
- normal Frappe print/export/report facilities

## Permissions

The repository defines role-based permissions directly on its DocTypes.

Examples include:

- System Manager
- Projects Manager
- Projects User
- Maintenance Manager
- Maintenance User
- Stock Manager
- Stock User

Submittable transactions support standard Frappe draft, submit, cancel and amend behavior according to their configured permissions.

## Reports and Dashboards

The current repository does not contain dedicated Script Reports, Query Reports, dashboards, or dashboard charts.

Operational data can still be accessed through standard Frappe list views, Report Builder, exports, print views, and API access.

## APIs

No custom whitelisted API endpoints are currently defined in the repository.

Frappe's standard document APIs remain available according to site permissions.

## Hooks and Events

The current `hooks.py` contains standard app metadata and commented examples, but no active custom:

- document event hooks
- scheduler events
- permission query hooks
- method overrides
- page assets
- installation hooks

This means most current functionality is driven by DocType metadata and Frappe's standard document behavior.

## Background Jobs

No active scheduler jobs are configured in `hooks.py`.

## Project Structure

```text
ConsMS/
├── README.md
├── setup.py
├── requirements.txt
├── license.txt
└── consms/
    ├── __init__.py
    ├── hooks.py
    ├── modules.txt
    ├── config/
    ├── construction/
    │   └── doctype/
    │       ├── daily_work_progress/
    │       ├── dwp_task/
    │       ├── dwp_equipment/
    │       ├── dwp_material/
    │       ├── dwp_labour/
    │       ├── equipment_repair_requisition/
    │       ├── equipment_repair_requisition_detail/
    │       ├── handing_over/
    │       ├── handing_over_detail/
    │       ├── plant_and_equipment_operation_log_sheet/
    │       └── task_detail/
    └── templates/
```

## Developer Setup

A typical development setup is:

```bash
bench get-app https://github.com/Aakvatech-Limited/ConsMS.git
bench --site <site-name> install-app consms
bench --site <site-name> migrate
bench start
```

Run tests using the Frappe bench test runner appropriate for the target framework version.

## Migration Notes

The repository currently contains an empty `patches.txt`.

No explicit migration patches are defined.

For upgrades across major Frappe versions, review:

- deprecated DocType metadata keys
- role names
- framework API changes
- packaging format
- frontend compatibility
- standard DocType availability

## Upgrade Guide

Before upgrading ConsMS or the underlying Frappe/ERPNext stack:

1. Back up the site.
2. Review changes between the installed app commit and target commit.
3. Confirm framework compatibility.
4. Run `bench --site <site> migrate`.
5. Test creation, submit, cancel, amend, print and reporting for all ConsMS DocTypes.
6. Verify linked Project, Task, Item, Employee, Supplier and UOM records.
7. Validate permissions for project, maintenance and stock users.

## Uninstallation

Use the standard Frappe uninstall process only after taking a full backup and evaluating whether ConsMS DocType data must be retained.

```bash
bench --site <site-name> uninstall-app consms
```

## Security

ConsMS relies primarily on Frappe's standard authentication, role permissions, document permissions and audit trail.

Deployers should review:

- role assignments
- submit/cancel rights
- data export permissions
- write access to cost/rate fields
- access to Employee and Project data
- API access
- backup and retention policy

## Troubleshooting

### App installs but linked fields fail

Confirm that the target site contains the referenced standard DocTypes, especially:

- Project
- Task
- Item
- Employee
- Supplier
- UOM

### Roles are missing

Some permissions reference ERPNext-style roles such as Projects Manager, Projects User, Maintenance Manager, Maintenance User, Stock Manager and Stock User. Confirm those roles exist on the site.

### Installation fails on newer Frappe releases

The repository uses legacy packaging and does not currently declare modern Frappe dependency constraints. Validate the branch against your target Frappe version before production installation.

## Decision Guide

ConsMS is a useful fit when your organization needs structured construction-site operational records inside Frappe and already manages or intends to manage projects, tasks, employees, items and equipment in the same ecosystem.

Consider additional development if you require:

- BOQ management
- tendering
- subcontractor management
- certifications
- retention
- progress billing
- variation orders
- construction-specific procurement controls
- budget vs actual dashboards
- mobile-first field capture
- geo-tagged records
- photo attachments and site evidence workflows
- advanced construction analytics

## Expected Business Outcomes

With suitable configuration and user adoption, ConsMS can help organizations improve:

- site activity traceability
- daily progress discipline
- equipment utilization records
- maintenance request visibility
- material usage visibility
- labour utilization visibility
- handover accountability
- operational auditability

## Implementation Effort

Implementation effort depends heavily on the target Frappe/ERPNext version and how closely the existing DocTypes match the customer's processes.

A typical implementation review should cover:

1. Framework compatibility
2. Existing Project/Task structure
3. Item and equipment master design
4. Employee setup
5. Role mapping
6. Daily site reporting process
7. Cost/rate ownership
8. Print formats
9. Reporting requirements
10. Required enhancements

## What Needs to Be Ready Before Implementation

- Frappe/ERPNext site
- Project master data
- Task structure
- Item/equipment masters
- Employee records
- UOM data
- Project, maintenance and stock user roles
- Site reporting SOP
- Ownership of rate/cost maintenance
- Backup and deployment process

## Risks and Considerations

- The codebase is relatively small and appears to originate from an older Frappe generation.
- Modern Frappe version compatibility is not declared.
- There are no repository-level business dashboards or dedicated reports.
- There are no active scheduler jobs or custom APIs.
- Some linked DocTypes imply ERPNext or equivalent applications even though only Frappe is declared in `requirements.txt`.
- Automated test files exist for several DocTypes, but the current repository should be validated against the target framework version before production use.

## Frequently Asked Business Questions

### Does ConsMS replace ERPNext Projects?

No. The current app links to Project and Task rather than replacing them. Its main value is adding construction-site operational records.

### Can it track daily labour, material and equipment usage?

Yes. Daily Work Progress includes child tables for tasks, labour, materials and equipment.

### Can it track equipment operating hours and fuel?

Yes. The Plant and Equipment Operation Log Sheet includes operating time, standby, breakdown, fuel, oil, rate and amount fields.

### Can maintenance teams raise equipment repair requirements?

Yes. Equipment Repair Requisition captures equipment, requester, required material/service lines and cost fields.

### Does it support project handover documentation?

Yes. Handing Over captures responsible employees, witness, supervisor, location, date and item-level details.

### Does it include BOQ and construction billing?

Not in the current repository.

### Does it have dashboards?

No dedicated dashboards are currently included.

## Repository Evidence Reviewed

This README was prepared from the repository structure and code, including:

- `README.md`
- `setup.py`
- `requirements.txt`
- `license.txt`
- `consms/__init__.py`
- `consms/hooks.py`
- `consms/modules.txt`
- `consms/config/consms.py`
- Daily Work Progress DocType
- DWP Task child table
- DWP Equipment child table
- DWP Material child table
- DWP Labour child table
- Equipment Repair Requisition DocType and child table
- Plant and Equipment Operation Log Sheet DocType
- Handing Over DocType and child table

## To Confirm Before Production Deployment

- Supported Frappe version
- Supported ERPNext version
- Whether ERPNext should be declared as an explicit dependency
- Whether a `pyproject.toml` should be added
- Whether existing role names are still correct for the target release
- Whether additional reports or dashboards are required
- Whether cost fields should be editable by site users
- Whether dedicated print formats are required
- Whether the app should support mobile-first site data capture

## Contributing

Contributions should be made through a feature or fix branch and submitted through a pull request.

Before submitting changes:

- keep changes scoped
- include migration notes where relevant
- add or update tests
- validate against the supported Frappe version
- avoid introducing undocumented dependencies

## Versioning

Current application version in the repository:

```text
0.0.1
```

A formal versioning and release policy is not currently documented in the repository.

## License

GPL, as declared in the repository.

## Maintainer

**Aakvatech**

- Email: info@aakvatech.com
- Repository: https://github.com/Aakvatech-Limited/ConsMS
