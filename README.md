## Frappe PowerBI Integration

PowerBI Integration is a [Frappe Framework](https://github.com/frappe/frappe) App
that provides APIs and Tools that enable the
[Frappe PowerBI Connector](https://github.com/ParaLogicTech/frappe_pbi_connector)
to get metadata, document data and report data.

## Features 🎁

- Provides APIs to get Frappe DocType Meta and Document data
- Provides APIs to get Frappe Report data source metadata and Report data
- Creates an OAuth Client for Power BI to enable OAuth authentication between Power BI and Frappe
- Allows defining "PowerBI Report Source"s with predefined static and dynamic filters
- Supports both on-demand report generation and scheduled/periodic refresh report generation of Report Sources
- Applies role and user permissions to all data exposed to Power BI

## Authentication

Frappe PowerBI Connector can authenticate with a Frappe site using the following methods:

- OAuth2
- API Key/Secret (not recommended as the API Key/Secret is exposed to the client)

Frappe Framework and Power BI natively support OAuth and the integration is seamless.
This app only creates the OAuth Client configuration automatically with the relevant redirect URIs, scope and allowed roles.
The OAuth Client can be modified by the System Manager for fine-tuning scopes and permissions.

Additionally, this app provides a public API `pbi_integration.api.settings.get_oauth_client_id`
for the Power BI Connector to get the OAuth Client ID since each site will have a
different client id and cannot be hardcoded in the Power BI Connector.

## DocType and Document Data APIs

This app provides 2 APIs to get DocType Meta:

- `pbi_integration.api.documents.get_doctypes` - Lists all non-single DocTypes that the user has read permissions for
- `pbi_integration.api.documents.get_doctype_meta` - Gets the DocType meta for a given DocType with relevant permission checks

The Power BI Connector uses Frappe's built-in REST APIs to get the Document list data therefore no additional APIs are required.

## PowerBI Report Source

This app enables the Power BI Connector to get Frappe Report data through a new DocType called "PowerBI Report Source".

Users can create PowerBI Report Source documents to define the reports available to the Power BI Connector.
PowerBI Report Source document defines the following:

- Which Report to get data from
- Which static filters to apply
- Which dynamic filters to apply
- Whether to generate the report on every request or periodically refresh and store generated reports
- Refresh frequency and schedule (similar to Power BI refresh schedule options)
- Grace duration so that the updated data is available before the scheduled Power BI refresh is triggered

### PowerBI Report Source APIs

- `pbi_integration.api.reports.get_report_sources` - Lists all PowerBI Report Sources permitted to the user
- `pbi_integration.api.reports.get_report_source_content` - Serve the report data from the PowerBI Report Source, generate data if On-Demand, otherwise serve from pre-generated JSON file

### Report Filter Issue

Frappe Reports store the filter meta purely on the client side and do not expose the filter meta to the backend,
therefore, selecting filters within the Power BI client is not technically possible.
PowerBI Report Source solves the problem by allowing the user to define static and dynamic filters in
PowerBI Report Source document within Frappe Desk View.

### Large Data Issue

For large datasets and/or long-running reports, generating the report on demand is not feasible
as the backend can run into timeout and resource exhaustion issues.

PowerBI Report Source solves this problem by allowing the periodic refresh option to generate the report
and store it as a temporary, private and uncompressed JSON file on the server.

Frappe can then allow NGINX to serve this file as a streaming file response to the Power BI Connector without blocking the Gunicorn/Web worker.

PowerBI Report Source may also be used as a replacement to Frappe Documents API when the dataset is large enough.

Users can create custom reports based on Report Builder, Query Report or Script Report
and use that custom report in a PowerBI Report Source with periodic refresh enabled.

## Roadmap & Wishlist ✨
- Support for Vanilla Frappe Framework (waiting for [PR #44433](https://github.com/frappe/frappe/pull/44433))
- Screenshots in documentation
- Release on Frappe Cloud Marketplace
- Option to easily create Desk Pages to show embedded PowerBI Reports

## Support 🤗
Please contact us for any support or other inquiries via our website https://paralogic.io.

## Contributing 🤝
You can fork this repository and create a pull request to contribute code.
By contributing to PowerBI Integration App, you agree that your contributions will be licensed under its GNU General Public License (v3). 

## License
The PowerBI Intergration code is licensed as GNU General Public License (v3), and the copyright is owned by ParaLogic and Contributors (see license.txt).
