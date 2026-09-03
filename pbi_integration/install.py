import frappe
from frappe.permissions import SYSTEM_USER_ROLE


def after_install():
	setup_oauth_client()


def setup_oauth_client():
	existing_client = frappe.get_single_value("PowerBI Integration Settings", "oauth_client")
	if existing_client:
		return

	oauth_client = frappe.new_doc("OAuth Client")
	oauth_client.app_name = "PowerBI Connector"
	oauth_client.append("allowed_roles", {"role": SYSTEM_USER_ROLE})
	oauth_client.scopes = "all openid"
	oauth_client.redirect_uris = "https://oauth.powerbi.com/views/oauthredirect.html"
	oauth_client.default_redirect_uri = "https://oauth.powerbi.com/views/oauthredirect.html"
	oauth_client.grant_type = "Authorization Code"
	oauth_client.response_type = "Code"
	oauth_client.insert(ignore_permissions=True)

	frappe.db.set_single_value("PowerBI Integration Settings", "oauth_client", oauth_client.name)
