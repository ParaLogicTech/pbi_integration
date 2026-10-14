app_name = "pbi_integration"
app_title = "PowerBI Integration"
app_publisher = "ParaLogic"
app_description = "PowerBI Connector APIs and Tools"
app_email = "info@paralogic.io"
app_license = "gpl-3.0"

after_install = "pbi_integration.install.after_install"

scheduler_events = {
	"all": [
		"pbi_integration.powerbi_integration.doctype.powerbi_report_source.powerbi_report_source.enqueue_auto_refresh_report_sources",
	]
}

permission_query_conditions = {
	"PowerBI Report Source": "pbi_integration.powerbi_integration.doctype.powerbi_report_source.powerbi_report_source.get_permission_query_conditions",
}

has_permission = {
	"PowerBI Report Source": "pbi_integration.powerbi_integration.doctype.powerbi_report_source.powerbi_report_source.has_permission",
}
