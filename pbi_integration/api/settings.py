import frappe
from frappe import _


@frappe.whitelist()
def get_oauth_client_id():
	oauth_client = frappe.get_cached_value("PowerBI Integration Settings", None, "oauth_client")
	client_id = frappe.get_cached_value("OAuth Client", oauth_client, "client_id")

	if not client_id:
		frappe.throw(_("PowerBI Connector OAuth Client is not configured"))

	return client_id
