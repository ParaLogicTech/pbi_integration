# Copyright (c) 2026, ParaLogic and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.reportview import validate_args


@frappe.whitelist()
def get_doctypes(
	fields=None,
	filters=None,
	order_by=None,
	limit_start=None,
	limit_page_length=None,
	**kwargs,
):
	user_permissions = frappe.get_user()
	if user_permissions.doc.user_type != "System User":
		raise frappe.PermissionError

	can_read = user_permissions.get_can_read()
	if not can_read:
		return []

	filters = frappe.parse_json(filters)
	if not filters:
		filters = frappe._dict()

	# Filter by DocTypes with read permissions
	if isinstance(filters, list):
		filters.append(["DocType", "issingle", "=", 0])
		filters.append(["DocType", "name", "in", can_read])
	elif isinstance(filters, dict):
		filters["issingle"] = 0
		if filters.get("name"):
			if filters.get("name") not in can_read:
				return []
		else:
			filters["name"] = ["in", can_read]

	args = frappe._dict(
		doctype="DocType",
		fields=fields,
		filters=filters,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	validate_args(args)
	return frappe.get_all(**args)


@frappe.whitelist()
def get_doctype_meta(doctype):
	user_permissions = frappe.get_user()
	if user_permissions.doc.user_type != "System User":
		raise frappe.PermissionError

	frappe.has_permission(doctype, "read", throw=True)

	return frappe.get_meta(doctype)
