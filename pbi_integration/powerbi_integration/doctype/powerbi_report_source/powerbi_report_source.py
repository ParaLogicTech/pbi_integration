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
	get_time,
	now_datetime,
	combine_datetime,
	add_days,
	get_datetime,
	format_duration,
)
import datetime


PREVIEW_ROWS = 20
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAY_FIELDS = {wd: f"weekly_{wd.lower()}" for wd in WEEKDAYS}


class PowerBIReportSource(Document):
	def validate(self):
		self.validate_generation_method()
		self.validate_schedule_times()
		self.validate_grace_duration()
		self.set_next_refresh_dt()

	def validate_generation_method(self):
		if not self.generation_method:
			self.generation_method = "On Request"

		if self.generation_method == "Periodic Refresh":
			if not self.refresh_frequency:
				frappe.throw(_("Refresh Frequency is required for Periodic Refresh"))

			if self.refresh_frequency == "Weekly" and all(not self.get(wdf) for wdf in WEEKDAY_FIELDS.values()):
				frappe.throw(_("Please select at least one day of the week for Weekly Refresh"))

	def validate_schedule_times(self):
		if self.generation_method != "Periodic Refresh":
			return

		if not self.refresh_schedule:
			self.append("refresh_schedule", {"refresh_time": get_time("00:00:00")})

		visited = set()
		duplicates = []
		for d in self.refresh_schedule:
			d.refresh_time = get_time(d.refresh_time)
			d.refresh_time = d.refresh_time.replace(second=0, microsecond=0)

			if d.refresh_time in visited:
				duplicates.append(d)

			visited.add(d.refresh_time)

		for d in duplicates:
			self.remove(d)

		self.refresh_schedule = sorted(self.refresh_schedule, key=lambda d: get_time(d.refresh_time))
		for i, d in enumerate(self.refresh_schedule):
			d.idx = i + 1

	def validate_grace_duration(self):
		grace_duration = cint(self.grace_duration)
		if not grace_duration:
			return
		if len(self.refresh_schedule) < 2:
			return

		today_date = getdate()
		prev_refresh_time = self.refresh_schedule[0].refresh_time
		for d in self.refresh_schedule[1:]:
			curr_refresh_dt = combine_datetime(today_date, d.refresh_time)
			prev_refresh_dt = combine_datetime(today_date, prev_refresh_time)

			diff = (curr_refresh_dt - prev_refresh_dt).total_seconds()
			if diff < grace_duration:
				frappe.throw(_("Refresh Schedule must have at least {0} between each refresh time").format(
					frappe.bold(format_duration(grace_duration))
				))

			prev_refresh_time = d.refresh_time

	def set_next_refresh_dt(self):
		self.validate_schedule_times()
		if self.generation_method != "Periodic Refresh" or not self.enabled or self.pause_auto_refresh:
			self.next_refresh_dt = None
			return

		now_dt = now_datetime()
		today_date = getdate(now_dt)
		if self.next_refresh_dt:
			self.next_refresh_dt = get_datetime(self.next_refresh_dt)
		if self.last_refresh_dt:
			self.last_refresh_dt = get_datetime(self.last_refresh_dt)

		# Do not change next refresh if already due to run
		if (
			self.next_refresh_dt
			and now_dt > self.next_refresh_dt
			and (not self.last_refresh_dt or self.last_refresh_dt < self.next_refresh_dt)
		):
			return

		# Determine next refresh date
		if self.refresh_frequency == "Weekly":
			current_refresh_date = None
			next_refresh_date = None
			for days_to_add in range(8):
				cur_date = add_days(today_date, days_to_add)
				cur_weekday = cur_date.strftime("%A")
				cur_weekday_field = WEEKDAY_FIELDS[cur_weekday]
				if not self.get(cur_weekday_field):
					continue

				if not current_refresh_date:
					current_refresh_date = cur_date
				if not next_refresh_date and cur_date > current_refresh_date:
					next_refresh_date = cur_date

			if not current_refresh_date:
				self.next_refresh_dt = None
				return
		else:
			current_refresh_date = today_date
			next_refresh_date = add_days(current_refresh_date, 1)

		refresh_dates = [current_refresh_date, next_refresh_date]
		refresh_dates = [d for d in refresh_dates if d]

		self.next_refresh_dt = None
		for refresh_date in refresh_dates:
			if self.next_refresh_dt:
				break

			for d in self.refresh_schedule:
				schedule_dt = combine_datetime(refresh_date, d.refresh_time)
				if self.grace_duration:
					schedule_dt -= datetime.timedelta(seconds=self.grace_duration)

				if (not self.last_refresh_dt or schedule_dt > self.last_refresh_dt) and schedule_dt > now_dt:
					self.next_refresh_dt = schedule_dt
					break

	def generate_report_file(self):
		old_file_url = self.report_contents_file
		try:
			self.db_set("is_executing", 1, commit=True)

			report_data = self.get_report_content(
				update_preview_data=True,
				update_execution_time=True,
				auto_commit=False,
			)
			file_url = create_report_file(self.name, report_data, "report_contents_file")

			self.db_set({
				"report_contents_file": file_url,
				"last_refresh_dt": now_datetime(),
				"retry": 0,
			}, commit=True)

			self.set_next_refresh_dt()
			self.db_set("next_refresh_dt", self.next_refresh_dt, commit=True)

			if old_file_url:
				old_file_name = frappe.db.get_value("File", {
					"file_url": old_file_url,
					"attached_to_doctype": "PowerBI Report Source",
					"attached_to_name": self.name,
				}, "name")
				if old_file_name:
					frappe.delete_doc("File", old_file_name, ignore_permissions=True, delete_permanently=True)
					frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise
		finally:
			self.db_set("is_executing", 0, commit=True)

	def get_report_preview(self, auto_commit=False):
		if self.report_type == "Report Builder":
			return self.get_report_content(
				limit=PREVIEW_ROWS,
				update_preview_data=False,
				update_execution_time=False,
				auto_commit=False,
			)

		preview_data = frappe.parse_json(self.preview_json) if self.preview_json else None
		if not preview_data:
			self.get_report_content(
				update_preview_data=True,
				update_execution_time=True,
				auto_commit=auto_commit,
			)
			preview_data = frappe.parse_json(self.preview_json)

		return preview_data

	def get_report_content(
		self,
		user_filters=None,
		update_preview_data=False,
		update_execution_time=False,
		limit=None,
		auto_commit=False,
	):
		start_time = datetime.datetime.now()

		user_filters = frappe.parse_json(user_filters) if user_filters else None
		self.prepare_filters(user_filters)

		if self.report_type == "Report Builder":
			update_preview_data = False

		report = frappe.get_doc("Report", self.report)
		columns, data = report.get_data(
			limit=limit,
			user=self.user,
			filters=self.parsed_filters,
			as_dict=True,
			ignore_prepared_report=True,
			are_default_filters=False,
			with_total_row=False,
		)

		if self.report_type == "Script Report":
			from frappe.desk.query_report import flatten_grouped_report_data
			data = flatten_grouped_report_data(data)

		execution_time = (datetime.datetime.now() - start_time).total_seconds()
		if update_execution_time:
			self.db_set("last_execution_time", execution_time, update_modified=False, commit=auto_commit)

		if update_preview_data:
			preview_data = {
				"columns": columns,
				"result": data[:PREVIEW_ROWS],
			}
			preview_json = as_json(preview_data)
			self.db_set("preview_json", preview_json, update_modified=False, commit=auto_commit)

		return frappe._dict({
			"columns": columns,
			"result": data,
			"filters": self.parsed_filters,
		})

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
	doc.check_permission("read")
	doc.prepare_filters(filters)
	return doc.parsed_filters


@frappe.whitelist()
def refresh_report_data(report_source):
	doc = frappe.get_doc("PowerBI Report Source", report_source, for_update=True)
	doc.check_permission("write")

	if not doc.enabled:
		frappe.throw(_("Report is disabled"))
	if doc.is_executing:
		frappe.throw(_("Report is already being refreshed"))
	if doc.generation_method != "Periodic Refresh":
		frappe.throw(_("Cannot generate report contents file for non Periodic Refresh report sources"))

	job = generate_report_file.enqueue(
		report_source=report_source,
		is_auto_refresh=False,
		job_id=get_refresh_job_id(report_source),
		deduplicate=True,
	)
	if job:
		frappe.msgprint(_("Report data refresh queued in background. It may take a few minutes to complete."))
	else:
		frappe.msgprint(_("Report data refresh is already queued."))


def enqueue_auto_refresh_report_sources():
	to_refresh = frappe.db.sql_list("""
		select name
		from `tabPowerBI Report Source`
		where
			enabled = 1
			and pause_auto_refresh = 0
			and is_executing = 0
			and generation_method = 'Periodic Refresh'
			and next_refresh_dt <= %s
	""", now_datetime())

	for report_source in to_refresh:
		generate_report_file.enqueue(
			report_source=report_source,
			is_auto_refresh=True,
			job_id=get_refresh_job_id(report_source),
			deduplicate=True,
		)


@frappe.task(queue="long")
def generate_report_file(report_source, is_auto_refresh=False):
	doc = frappe.get_doc("PowerBI Report Source", report_source, for_update=True)
	if not doc.enabled or doc.is_executing or doc.generation_method != "Periodic Refresh":
		return
	if is_auto_refresh and doc.pause_auto_refresh:
		return

	try:
		doc.generate_report_file()
		doc.notify_update()
	except Exception as e:
		frappe.db.rollback()

		doc.log_error("Error refreshing PowerBI Report Source")

		paused_auto_refresh = False
		if is_auto_refresh:
			doc.db_set("retry", cint(doc.retry) + 1)
			if doc.retry >= 3:
				paused_auto_refresh = True
				doc.db_set("pause_auto_refresh", 1)

		comment = _("Error refreshing report data:") + "<br>" + str(e)
		if paused_auto_refresh:
			comment += "<br><br>" + _("Auto refresh paused due to errors. Please re-enable after resolving the issue.")
		doc.add_comment(text=comment)

		doc.notify_update()
		frappe.db.commit()


def get_refresh_job_id(report_source):
	return "powerbi_report_refresh::" + report_source


def create_report_file(report_source, data, field):
	json_filename = "{}_{}.json".format(
		frappe.scrub(report_source),
		frappe.utils.data.format_datetime(frappe.utils.now(), "y-M-d-H-m")
	)
	encoded_content = frappe.safe_encode(as_json({
		"message": data
	}))

	_file = frappe.get_doc({
		"doctype": "File",
		"file_name": json_filename,
		"attached_to_doctype": "PowerBI Report Source",
		"attached_to_name": report_source,
		"attached_to_field": field,
		"content": encoded_content,
		"is_private": 1,
	})
	_file.save(ignore_permissions=True)
	return _file.file_url


def as_json(data):
	return frappe.as_json(data, indent=None, separators=(",", ":"))


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
