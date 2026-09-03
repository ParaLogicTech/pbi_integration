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
