from frappe.utils import getdate, get_time
import datetime


def combine_datetime(date, time):
	date = getdate(date)
	time = get_time(time)
	return datetime.datetime.combine(date, time)
