# Copyright (c) 2026, ParaLogic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe import sbool, cint
from frappe.desk.reportview import validate_args


@frappe.whitelist()
def get_report_sources(
	fields=None,
	filters=None,
	order_by=None,
	limit_start=None,
	limit_page_length=None,
	**kwargs,
):
	if frappe.session.data.user_type != "System User":
		raise frappe.PermissionError

	user_permissions = frappe.get_user()
	permitted_reports = user_permissions.get_all_reports()
	if not permitted_reports:
		return []

	filters = frappe.parse_json(filters)
	if not filters:
		filters = frappe._dict()

	# Filter by permitted reports permissions
	if isinstance(filters, list):
		filters.append(["PowerBI Report Source", "enabled", "=", 1])
		filters.append(["PowerBI Report Source", "report", "in", permitted_reports])
	elif isinstance(filters, dict):
		filters["enabled"] = 1
		if filters.get("report"):
			if filters.get("report") not in permitted_reports:
				return []
		else:
			filters["report"] = ["in", permitted_reports]

	args = frappe._dict(
		doctype="PowerBI Report Source",
		fields=fields,
		filters=filters,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	validate_args(args)
	return frappe.get_all(**args)


@frappe.whitelist()
def get_report_source_content(
	report_source,
	for_preview=False,
	filters=None,
):
	for_preview = cint(sbool(for_preview))
	filters = frappe.parse_json(filters) or None

	if filters and not isinstance(filters, dict):
		frappe.throw(_("filters must be a JSON object"))

	doc = frappe.get_doc("PowerBI Report Source", report_source)
	columns, result = doc.get_report_content(
		limit=20 if for_preview else None,
		user_filters=filters,
	)

	return frappe._dict({
		"columns": columns,
		"result": result,
	})
