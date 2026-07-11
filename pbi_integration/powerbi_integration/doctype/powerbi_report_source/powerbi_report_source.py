# Copyright (c) 2026, ParaLogic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	today,
	add_to_date,
	get_first_day_of_week,
	get_first_day,
	get_quarter_start,
	get_year_start,
	getdate,
	cint,
)
import datetime


class PowerBIReportSource(Document):
	def get_report_content(self, limit=None, user_filters=None):
		report = frappe.get_doc("Report", self.report)

		limit = cint(limit)
		self.prepare_filters(user_filters)

		columns, data = report.get_data(
			limit=limit,
			user=self.user,
			filters=self.parsed_filters,
			as_dict=True,
			ignore_prepared_report=True,
			are_default_filters=False,
		)
		if limit and self.report_type != "Report Builder":
			data = data[:limit]

		if self.report_type == "Script Report":
			from frappe.desk.query_report import flatten_grouped_report_data
			data = flatten_grouped_report_data(data)

		return columns, data

	def prepare_filters(self, user_filters=None):
		self.parsed_filters = frappe.parse_json(self.filters) if self.filters else {}

		filters = frappe.parse_json(user_filters) if user_filters else {}
		if filters:
			self.parsed_filters.update(filters)

		if self.report_type != "Report Builder" and self.dynamic_date_filters_set():
			self.prepare_dynamic_filters()

	def dynamic_date_filters_set(self):
		return self.dynamic_date_period and self.from_date_field and self.to_date_field

	def prepare_dynamic_filters(self):
		to_date = today()

		if self.use_first_day_of_period:
			from_date = to_date
			if self.dynamic_date_period == "Daily":
				from_date = add_to_date(to_date, days=-1)
			elif self.dynamic_date_period == "Weekly":
				from_date = get_first_day_of_week(from_date, as_str=True)
			elif self.dynamic_date_period == "Monthly":
				from_date = get_first_day(from_date, as_str=True)
			elif self.dynamic_date_period == "Quarterly":
				from_date = get_quarter_start(from_date, as_str=True)
			elif self.dynamic_date_period == "Half Yearly":
				from_date = get_half_year_start(as_str=True)
			elif self.dynamic_date_period == "Yearly":
				from_date = get_year_start(from_date, as_str=True)

			self.set_date_filters(from_date, to_date)
		else:
			from_date_value = {
				"Daily": ("days", -1),
				"Weekly": ("weeks", -1),
				"Monthly": ("months", -1),
				"Quarterly": ("months", -3),
				"Half Yearly": ("months", -6),
				"Yearly": ("years", -1),
			}[self.dynamic_date_period]

			from_date = add_to_date(to_date, **{from_date_value[0]: from_date_value[1]})
			self.set_date_filters(from_date, to_date)

	def set_date_filters(self, from_date, to_date):
		self.parsed_filters[self.from_date_field] = from_date
		self.parsed_filters[self.to_date_field] = to_date


@frappe.whitelist()
def get_parsed_filters(report_source, filters=None):
	doc = frappe.get_doc("PowerBI Report Source", report_source)
	doc.prepare_filters(filters)
	return doc.parsed_filters


def get_half_year_start(as_str=False):
	"""
	Returns the first day of the current half-year based on the current date.
	"""
	today_date = getdate(today())

	half_year = 1 if today_date.month <= 6 else 2

	year = today_date.year if half_year == 1 else today_date.year + 1
	month = 1 if half_year == 1 else 7
	day = 1

	result_date = datetime.date(year, month, day)

	return result_date if not as_str else result_date.strftime("%Y-%m-%d")
