#!/usr/bin/env python

from collections import OrderedDict
from datetime import datetime, date, timedelta, timezone
from dateutil.relativedelta import relativedelta
import dateutil.parser as date_parser
#import pytz
import re

# https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
class DateHelper:
	DATETIME_FORMAT_STANDARD = "%Y-%m-%d %H:%M:%S"
	DATETIME_FORMAT_STANDARD_UTC = "%Y-%m-%d %H:%M:%S %Z%z"
	DATETIME_FORMAT_DATE_ONLY = "%Y-%m-%d"
	DATETIME_FORMAT_MILISEC = "%Y-%m-%d %H:%M:%S.%f"
	def __init__(self, date):
		self._date = date
	@property
	def date(self):
		return self._date
	@property
	def type(self):
		return type(self._date).__name__

	def as_string(self):
		return DateHelper.date_to_string(self._date)
	def as_time(self):
		return self._date.strftime('%H:%M:%S')
	def as_date(self):
		return self._date.strftime('%Y-%m-%d')

	def day_is_before_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year > compare_date.year:
			return False
		if self._date.month > compare_date.month:
			return False
		if self._date.day >= compare_date.day:
			return False
		return True
	def day_is_after_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year < compare_date.year:
			return False
		if self._date.month < compare_date.month:
			return False
		if self._date.day <= compare_date.day:
			return False
		return True
	def day_is_same_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year != compare_date.year:
			return False
		if self._date.month != compare_date.month:
			return False
		if self._date.day != compare_date.day:
			return False
		return True
	def day_is_between_dates(self, from_date, to_date):
		return self.day_is_after_date(from_date) and self.day_is_before_date(to_date)
	def month_is_before_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year > compare_date.year:
			return False
		if self._date.month >= compare_date.month:
			return False
		return True
	def month_is_after_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year < compare_date.year:
			return False
		if self._date.month <= compare_date.month:
			return False
		return True
	def month_is_same_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year != compare_date.year:
			return False
		if self._date.month != compare_date.month:
			return False
		return True
	def month_is_between_dates(self, from_date, to_date):
		return self.month_is_after_date(from_date) and self.month_is_before_date(to_date)

	def year_is_before_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year >= compare_date.year:
			return False
		return True
	def year_is_after_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year <= compare_date.year:
			return False
		return True
	def year_is_same_date(self, date):
		compare_date = DateHelper.format_date(date, DateHelper.DATETIME_FORMAT_DATE_ONLY)
		if self._date.year != compare_date.year:
			return False
		return True
	def year_is_between_dates(self, from_date, to_date):
		return self.year_is_after_date(from_date) and self.year_is_before_date(to_date)

	# // format (string) date and return as type 'datetime'
	@staticmethod
	def format_date(date, date_format=DATETIME_FORMAT_STANDARD):
		formatted_date = None

		try:
			if "str" == type(date).__name__:
				#date
				pattern_date = "^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$"
				if re.match(pattern_date, date):
					date = "%s 00:00:00" % date
				formatted_date = date_parser.parse(date).strftime(date_format)
			elif "datetime" == type(date).__name__:
				formatted_date = date_parser.parse(date.isoformat()).strftime(date_format)
			else:
				formatted_date = None
		except:
			formatted_date = None
			print("[!] format_date failed to pre-format")

		if "str" == type(formatted_date).__name__:
			formatted_date = datetime.strptime(formatted_date, date_format)

		return formatted_date

	@staticmethod
	def now():
		date_string = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
		return DateHelper.string_to_date(date_string)

	@staticmethod
	def is_date_string(date):
		if "str" == type(date).__name__:
			return True
		return False
	@staticmethod
	def is_date_type(date):
		if "datetime" == type(date).__name__:
			return True
		return False

	@staticmethod
	def date_is_today(date):
		today_date = DateHelper.now()
		if date.year != today_date.year:
			return False
		if date.month != today_date.month:
			return False
		if date.day != today_date.day:
			return False
		return True
	@staticmethod
	def date_is_yesterday(date):
		yesterday_date = DateHelper.remove_days_from(DateHelper.now(), 1)
		if date.year != yesterday_date.year:
			return False
		if date.month != yesterday_date.month:
			return False
		if date.day != yesterday_date.day:
			return False
		return True
	@property
	def is_today(self):
		today_date = DateHelper.now()
		if self._date.year != today_date.year:
			return False
		if self._date.month != today_date.month:
			return False
		if self._date.day != today_date.day:
			return False
		return True
	@property
	def is_yesterday(self):
		yesterday_date = DateHelper.remove_days_from(DateHelper.now(), 1)
		if self._date.year != yesterday_date.year:
			return False
		if self._date.month != yesterday_date.month:
			return False
		if self._date.day != yesterday_date.day:
			return False
		return True

	@staticmethod
	def is_same_hour(date, other_date):
		return date.hour == other_date.hour
	def is_same_min(date, other_date):
		return date.minutes == other_date.minutes

	@staticmethod
	def date_is_weekday_mon(date):
		return "monday" == DateHelper.to_weekday(date).lower()
	@staticmethod
	def date_is_weekday_tue(date):
		return "tuesday" == DateHelper.to_weekday(date).lower()
	@staticmethod
	def date_is_weekday_wed(date):
		return "wednesday" == DateHelper.to_weekday(date).lower()
	@staticmethod
	def date_is_weekday_thu(date):
		return "thursday" == DateHelper.to_weekday(date).lower()
	@staticmethod
	def date_is_weekday_fri(date):
		return "friday" == DateHelper.to_weekday(date).lower()
	@staticmethod
	def date_is_weekday_sat(date):
		return "saturday" == DateHelper.to_weekday(date).lower()
	@staticmethod
	def date_is_weekday_sun(date):
		return "sunday" == DateHelper.to_weekday(date).lower()

	@staticmethod
	def date_is_month_jan(date):
		if "january" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_feb(date):
		if "february" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_mar(date):
		if "march" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_apr(date):
		if "april" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_may(date):
		if "may" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_jun(date):
		if "june" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_jul(date):
		if "july" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_aug(date):
		if "august" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_sep(date):
		if "september" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_oct(date):
		if "october" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_nov(date):
		if "november" == DateHelper.to_month(date).lower():
			return True
		return False
	@staticmethod
	def date_is_month_dec(date):
		if "december" == DateHelper.to_month(date).lower():
			return True
		return False

	@property
	def is_month_jan(self):
		return "january" == self.month.lower()
	@property
	def is_month_feb(self):
		return "february" == self.month.lower()
	@property
	def is_month_mar(self):
		return "march" == self.month.lower()
	@property
	def is_month_apr(self):
		return "april" == self.month.lower()
	@property
	def is_month_may(self):
		return "may" == self.month.lower()
	@property
	def is_month_jun(self):
		return "june" == self.month.lower()
	@property
	def is_month_jul(self):
		return "july" == self.month.lower()
	@property
	def is_month_aug(self):
		return "august" == self.month.lower()
	@property
	def is_month_sep(self):
		return "september" == self.month.lower()
	@property
	def is_month_oct(self):
		return "october" == self.month.lower()
	@property
	def is_month_nov(self):
		return "november" == self.month.lower()
	@property
	def is_month_dec(self):
		return "december" == self.month.lower()

	@staticmethod
	def month_to_digits(month):
		if "january" == month.lower() or "jan" == month.lower():
			return 1
		elif "february" == month.lower() or "feb" == month.lower():
			return 2
		elif "march" == month.lower() or "mar" == month.lower():
			return 3
		elif "april" == month.lower() or "apr" == month.lower():
			return 4
		elif "may" == month.lower():
			return 5
		elif "june" == month.lower() or "jun" == month.lower():
			return 6
		elif "july" == month.lower() or "jul" == month.lower():
			return 7
		elif "august" == month.lower() or "aug" == month.lower():
			return 8
		elif "september" == month.lower() or "sep" == month.lower():
			return 9
		elif "october" == month.lower() or "oct" == month.lower():
			return 10
		elif "november" == month.lower() or "nov" == month.lower():
			return 11
		elif "december" == month.lower() or "dec" == month.lower():
			return 12
		return None



	@staticmethod
	def string_to_date(date_string):
		return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
	@staticmethod
	def date_to_string(date):
		return date.strftime('%Y-%m-%d %H:%M:%S')

	@staticmethod
	def date_to_time(date):
		return date.strftime('%H:%M:%S')
	@staticmethod
	def date_no_time(date):
		return date.strftime('%Y-%m-%d')

	@staticmethod
	def to_year(date):
		return date.year
	@staticmethod
	def to_month_digits(date):
		return date.strftime('%m')
	@staticmethod
	def to_month(date):
		return date.strftime("%B")
	@staticmethod
	def to_month_short(date):
		return date.strftime("%b")
	@staticmethod
	def to_day_digits(date):
		return date.strftime("%d")
	@staticmethod
	def to_weekday(date):
		return date.strftime('%A')
	@staticmethod
	def to_weekday_short(date):
		return date.strftime('%a')
	@staticmethod
	def to_week_number(date):
		return datetime.date(date).strftime("%V")
	@staticmethod
	def to_hour_digits(date):
		return date.strftime("%H")
	@staticmethod
	def to_minute_digits(date):
		return date.strftime('%M')
	
	@property
	def year(self):
		return int(self._date.strftime("%Y"))
	@property
	def month_digits(self):
		return int(self._date.strftime('%m'))
	@property
	def month(self):
		return self._date.strftime("%B")
	@property
	def month_short(self):
		return self._date.strftime("%b")
	@property
	def day_digits(self):
		return int(self._date.strftime("%d"))
	@property
	def weekday(self):
		return self._date.strftime('%A')
	@property
	def weekday_short(self):
		return self._date.strftime('%a')
	@property
	def week_number(self):
		return int(self._date.strftime("%V"))
	@property
	def hour_digits(self):
		return int(self._date.strftime("%-H"))
		return int(self._date.strftime("%H"))
	@property
	def minute_digits(self):
		return int(self._date.minute)
	@property
	def time_zone(self):
		return self._date.strftime("%Z")
	@property
	def utc_offset(self):
		return self._date.strftime("%z")
	@property
	def time_pm_am(self):
		return self._date.strftime("%p")

	@staticmethod
	def add_years_to(date, years):
		return date + relativedelta(years=years)
	@staticmethod
	def remove_years_from(date, years):
		return date - relativedelta(years=years)
	@staticmethod
	def add_months_to(date, months):
		return date + relativedelta(months=months)
	@staticmethod
	def remove_months_from(date, months):
		return date - relativedelta(months=months)
	@staticmethod
	def add_days_to(date, days):
		return date + timedelta(days=days)
	@staticmethod
	def remove_days_from(date, days):
		return date - timedelta(days=days)
	@staticmethod
	def add_weeks_to(date, weeks):
		return date + timedelta(weeks=weeks)
	@staticmethod
	def remove_weeks_from(date, weeks):
		return date - timedelta(weeks=weeks)
	@staticmethod
	def add_hours_to(date, hours):
		return date + timedelta(hours=hours)
	@staticmethod
	def remove_hours_from(date, hours):
		return date - timedelta(hours=hours)
	@staticmethod
	def add_minutes_to(date, minutes):
		return date + timedelta(minutes=minutes)
	@staticmethod
	def remove_minutes_from(date, minutes):
		return date - timedelta(minutes=minutes)
	@staticmethod
	def add_seconds_to(date, seconds):
		return date + timedelta(seconds=seconds)
	@staticmethod
	def remove_seconds_from(date, seconds):
		return date - timedelta(seconds=seconds)

	def add_years(self, years):
		self._date = self._date + relativedelta(years=years)
	def remove_years(self, years):
		self._date = self._date - relativedelta(years=years)
	def add_months(self, months):
		self._date = self._date + relativedelta(months=months)
	def remove_months(self, months):
		self._date = self._date - relativedelta(months=months)
	def add_days(self, days):
		self._date = self._date + timedelta(days=days)
	def remove_days(self, days):
		self._date = self._date - timedelta(days=days)
	def add_weeks(self, weeks):
		self._date = self._date + timedelta(weeks=weeks)
	def remove_weeks(self, weeks):
		self._date = self._date - timedelta(weeks=weeks)
	def add_hours(self, hours):
		self._date = self._date + timedelta(hours=hours)
	def remove_hours(self, hours):
		self._date = self._date - timedelta(hours=hours)
	def add_minutes(self, minutes):
		self._date = self._date + timedelta(minutes=minutes)
	def remove_minutes(self, minutes):
		self._date = self._date - timedelta(minutes=minutes)
	def add_seconds(self, seconds):
		self._date = self._date + timedelta(seconds=seconds)
	def remove_seconds(self, seconds):
		self._date = self._date - timedelta(seconds=seconds)

	def set_year(self, year):
		self._date = self._date.replace(year=year)
	def set_month(self, month):
		# convert named month to digital
		if 'str' == type(month).__name__:
			month_digits = DateHelper.month_to_digits(month)
			print("set_month.month_digits(%s).type: %s" % (month_digits, type(month_digits).__name__))
			#if month_digits is not None:
			if 'int' == type(month_digits).__name__:
				month = month_digits
		print("set_month.month_digits(%s).type: %s" % (month, type(month).__name__))
		print("set_month.self._date.type: %s" % (type(self._date).__name__))
		self._date = self._date.replace(month=month)
	def set_day(self, day):
		self._date = self._date.replace(day=day)
	def set_hour(self, hour):
		self._date = self._date.replace(hour=hour)
	def set_minute(self, minute):
		self._date = self._date.replace(minute=minute)
	def set_second(self, second):
		self._date = self._date.replace(second=second)
	# // something sets self._data to None in the 'set_to_today' method
	def set_to_today(self):
		today_date = DateHelper(datetime.now())
		print("set_today_day.type: %s" % (type(today_date.year).__name__))
		self._date = self.set_year(today_date.year)
		print(today_date.month)
		self._date = self.set_month(today_date.month)
		self._date = self.set_year(today_date.year)
	def set_to_noon(self):
		if self.hour_digits > 12:
			self.add_days(1)
		self.set_hour(12)
		self.set_minute(0)
		self.set_second(0)
	def set_to_midnight(self):
		self.add_days(1)
		self.set_hour(0)
		self.set_minute(0)
		self.set_second(0)


class RelativeDate:
	def __init__(self, time_range):
		self._range = time_range
		self._date = None
		self._date_range = None
		self._set_date_by_range()

	@property
	def date(self):
		return self._date
	@property
	def date_range(self):
		return self._date_range
	@property
	def range(self):
		return self._range
	@property
	def is_valid_date(self):
		return self._date is not None
	@property
	def is_valid_date_range(self):
		return self._date_range is not None
	
	def _set_date_by_range(self):
		# // extract ranges by searching for:
		# // since, after, until, before
		# // last, ago / these are the same thingy; last 2 hours, 2 hours ago
		# // this year, month, week, day, hour, min
		# // (since) date until
		ranges = OrderedDict()
		# 2 years 1 day 3 minutes ago
		if self._range.lower() == "today":
			self._date = datetime.today()
		elif self._range.lower() == "yesterday":
			self._date = datetime.today() - timedelta(days=1)
		elif self._range.lower().startswith("last "):
			self._set_date_by_range_last()

		elif self._range.lower().startswith("since "):
			self._set_date_by_range_since()
	def _parse_range(self):
		if " " in self._range:
			date_range = self._range.split(" ")[1:]
	def _set_date_by_range_last(self):
		date_range = None
		if ' ' in self._range:
			date_range = self._range.split(" ")[1:]
		if date_range is None:
			return

		if len(date_range) == 1:
			word = date_range[0]
			if self.is_date_word(word) or not self.date_word_is_plural(word):
				date_range.insert(0, 1)
				print("[* _set_date_by_last_range] change '%s' to '%s %s'" % (word, date_range[0], date_range[1]))
		if len(date_range) == 2:
			word_num = int(date_range[0])
			date_word = date_range[1]
			now_date = self._now_date
			date = self._get_removed_num_date_word(now_date, word_num, date_word)
			if date is not None:
				self._date_range = [date, now_date]
				self._date = date
	def _set_date_by_range_since(self):
		date_range = None
		if ' ' in self._range:
			date_range = self._range.split(" ")[1:]
		if date_range is None:
			return
	def _get_removed_num_date_word(self, date, word_num, date_word):
		changed_date = None

		if not self.is_date_word(date_word):
			return changed_date

		if self.word_is_year(date_word) or self.word_is_years(date_word):
			changed_date = DateHelper.remove_years_from(date, word_num)
		elif self.word_is_month(date_word) or self.word_is_months(date_word):
			changed_date = DateHelper.remove_months_from(date, word_num)
		elif self.word_is_week(date_word) or self.word_is_weeks(date_word):
			changed_date = DateHelper.remove_weeks_from(date, word_num)
		elif self.word_is_day(date_word) or self.word_is_days(date_word):
			changed_date = DateHelper.remove_days_from(date, word_num)
		else:
			return changed_date

		print("[+] remove '%s %s' - date: %s, delta: %s" % (word_num, date_word, date, changed_date))
		return changed_date
	@property
	def _now_date(self):
		# // init the date as now
		date_string = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')

	def parse(self, date_string):
		if self._endswith_ago(date_string) and self.is_relative_date(date_string):
			ago_items = None
			if ' ' in date_string:
				ago_items = date_string.split(" ")[0:-1]
			elif '.' in date_string:
				ago_items = date_string.split(".")[0:-1]
			if ago_items is None:
				return False
			return self.parse_ago(ago_items)
		elif self._startswith_last(date_string):
			last_items = None
			if ' ' in date_string:
				last_items = date_string.split(" ")[1:]
			elif '.' in date_string:
				last_items = date_string.split(".")[1:]
			if last_items is None:
				return False
			return self._parse_last(last_items)
		return False

	def _parse_last(self, last_items):
		if last_items is None:
			return False
		print("[* parse_last] '%s', len=%s" % (last_items, len(last_items)))
		if len(last_items) == 1 or len(last_items) == 2:
			return self._remove_from_date(last_items)
		return False
	def _remove_from_date(self, range_items):
		#change_date = self._date
		date_range = range_items
		if len(date_range) == 1:
			word = date_range[0]
			print("[* _remove_from_date].word '%s'" % word)
			#if word.endswith("s"):
			#	print("[* _remove_from_date] removing 's' from '%s'" % word)
			#	word = word[0:-1]
			if self.is_date_word(word) or not self.date_word_is_plural(word):
				date_range.insert(0, 1)
				print("[* _remove_from_date] change '%s' to '%s %s'" % (word, date_range[0], date_range[1]))

		if len(range_items) == 2:
			if "int" != type(range_items[0]).__name__ and "str" != type(range_items[1]).__name__:
				return False

			word_num = int(range_items[0])
			date_word = range_items[1]
			print("[* _remove_from_date] '%s %s'" % (word_num, date_word))
			if self.is_date_word(date_word):
				return self._remove_num_date_word(word_num, date_word)
			else:
				return False

		self._date = change_date
		return True
	def _validate_num_date_word(self, word_num, date_word):
		if self.is_date_word(date_word):
			if word_num == 1 and not self.date_word_is_plural(date_word):
				return True
			elif word_num > 1 and self.date_word_is_plural(date_word):
				return True
		return False
	def _remove_num_date_word(self, word_num, date_word):
		if not self.is_date_word(date_word):
			return False

		changed_date = None

		if self.word_is_year(date_word) or self.word_is_years(date_word):
			changed_date = DateHelper.remove_years_from(self._date, word_num)
		elif self.word_is_month(date_word) or self.word_is_months(date_word):
			changed_date = DateHelper.remove_months_from(self._date, word_num)
		elif self.word_is_week(date_word) or self.word_is_weeks(date_word):
			changed_date = DateHelper.remove_weeks_from(self._date, word_num)
		elif self.word_is_day(date_word) or self.word_is_days(date_word):
			changed_date = DateHelper.remove_days_from(self._date, word_num)
		else:
			return False

		print("[+] remove '%s %s' - date: %s, delta: %s" % (word_num, date_word, self._date, changed_date))
		changed_date = self._date

		return True
	def parse_ago(self, ago_items):
		if ago_items is None:
			return False

		date_ago = self._date
		ago_items_count = len(ago_items)
		skip_next = False
		for i in range(0, len(ago_items)):
			current_item = ago_items[i]
			print("- 1st ago_items(%s) '%s'" % (i, ago_items[i]))
			if skip_next:
				skip_next = False
				print("[-] skipping ago_items(%s) '%s'" % (i, current_item))
				continue
			#print("- 1st ago_items(%s) '%s'" % (i, ago_items[i]))
			
			if current_item.isnumeric():
				print("- 1st ago_items(%s) '%s'" % (i, current_item))
				word_num = int(current_item)
				
				#// check next item if relative word
				if (i+1) < len(ago_items):
					next_item = ago_items[i+1]
					print("- 2nd next ago_items(%s) '%s'" % (i+1, next_item))
					# // remove number of year, month, week, day, hour, min, sec
					if self.is_date_word(next_item) or self.is_time_word(next_item):
						if self.word_is_year(next_item):
							date_ago_delta = DateHelper.remove_years_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						elif self.word_is_month(next_item):
							date_ago_delta = DateHelper.remove_months_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						elif self.word_is_week(next_item):
							date_ago_delta = DateHelper.remove_weeks_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						elif self.word_is_day(next_item):
							date_ago_delta = DateHelper.remove_days_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						elif self.word_is_hour(next_item):
							date_ago_delta = DateHelper.remove_hours_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						elif self.word_is_min(next_item):
							date_ago_delta = DateHelper.remove_minutes_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						elif self.word_is_sec(next_item):
							date_ago_delta = DateHelper.remove_seconds_from(date_ago, word_num)
							print("[+] add '%s %s' - date: %s, delta: %s" % (word_num, next_item, date_ago, date_ago_delta))
							date_ago = date_ago_delta
						else:
							print("[!] warning - unknown date word, ago_items[%s], '%s'" % ((i+1), next_item))
							#return False
						skip_next = True
						continue
					# // set date by month: jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec
					elif self.is_month_word(next_item):
						month_digits = DateHelper.month_to_digits(next_item)
						date_ago_delta = date_ago.replace(month=month_digits, day=word_num)
						print("[+] set date to '%s %s (%s)' - date: %s, delta: %s" % (word_num, next_item, month_digits, date_ago, date_ago_delta))
						date_ago = date_ago_delta
						skip_next = True
					elif self.is_weekday_word(next_item):
						print("[!] warning - unsupported word '%s' after digit(s), ago_items[%s], '%s'" % (next_item, (i+1), next_item))
						return False
					else:
						print("[!] warning - unknown next word, ago_items[%s], '%s'" % ((i+1), next_item))
						return False
				else:
					print("warning - no more items after - current ago_items[%s], '%s'" % (i, current_item))
					return False
			# // word: today, yesterday
			elif self.is_relative_day(current_item):
				print("- 1st ago_items(%s) '%s'" % (i, current_item))
				if self.word_is_now(current_item):
					date_ago_delta = DateHelper.now()
					print("[+] set date to '%s' - date: %s, delta: %s" % (current_item, date_ago, date_ago_delta))
					date_ago = date_ago_delta
					skip_next = False
				if self.word_is_today(current_item):
					print("word is 'today' (%s)" % i)
					today_date = DateHelper(DateHelper.now())
					date_ago_delta = date_ago.replace(year=today_date.year, month=today_date.month_digits, day=today_date.day_digits)
					print("[+] set date to '%s' - %s %s (%s) %s - date: %s, delta: %s" % (current_item, today_date.year, today_date.day_digits, today_date.weekday, today_date.month, date_ago, date_ago_delta))
					date_ago = date_ago_delta
					skip_next = False
				elif self.word_is_yesterday(current_item):
					#print("word is 'yesterday' (%s)" % i)
					yesterday_date = DateHelper(DateHelper.now())
					yesterday_date.remove_days(1)
					date_ago_delta = date_ago.replace(year=yesterday_date.year, month=yesterday_date.month_digits, day=yesterday_date.day_digits)
					date_ago_delta_date = DateHelper(date_ago_delta)
					print("[+] set date to '%s' - %s %s (%s) %s - date: %s, delta: %s" % (current_item, date_ago_delta_date.year, date_ago_delta_date.day_digits, date_ago_delta_date.weekday, date_ago_delta_date.month, date_ago, date_ago_delta))
					date_ago = date_ago_delta
					skip_next = False
			# // mon, tue, wed, thu, fri, sat, sun
			elif self.is_weekday_word(current_item):
				print("next is weekday word (%s)" % next_item)
				print("info - 'is_weekday_word' not implemented yet, ago_items[%s], '%s'" % (i, current_item))
				skip_next = True
				pass

		self._date = date_ago
		return True

	def is_today(self, date):
		return DateHelper.date_is_today(date)

	def is_relative_date(self, date_string):
		if not self.has_relative_date_ago(date_string):
			return False
		
		if self.has_weekday(date_string):
			return True
		elif self.has_month(date_string):
			return True
		elif self.has_relative_day(date_string):
			return True
		elif self.has_date_word(date_string):
			return True
		elif self.has_time_word(date_string):
			return True
		elif self.has_named_time(date_string):
			return True
		return False
	def has_relative_date_ago(self, date_string):
		if self._endswith_ago(date_string):
			return True
		return False
	def _endswith_ago(self, date_string):
		if date_string.lower().endswith(".ago") or date_string.lower().endswith(" ago"):
			return True
		return False
	def _startswith_last(self, date_string):
		if date_string.lower().startswith("last.") or date_string.lower().startswith("last "):
			return True
		return False
	def _startswith_between(self, date_string):
		if date_string.lower().startswith("between.") or date_string.lower().startswith("between "):
			return True
		return False
	def has_relative_day(self, date_string):
		if self.has_word_now(date_string):
			return True
		elif self.has_word_today(date_string):
			return True
		elif self.has_word_yesterday(date_string):
			return True
		return False
	def is_relative_day(self, day):
		if self.word_is_now(day):
			return True
		elif self.word_is_today(day):
			return True
		elif self.word_is_yesterday(day):
			return True
		return False
	def has_named_time(self, date_string):
		if "now" in date_string.lower():
			return True
		elif "noon" in date_string.lower():
			return True
		elif "midnight" in date_string.lower():
			return True
		elif "tea" in date_string.lower():
			return True
		elif "pm" in date_string.lower():
			return True
		elif "am" in date_string.lower():
			return True
		return False
	def is_named_time(self, named_item):
		if self.word_is_midnight(named_item):
			return True
		elif self.word_is_noon(named_item):
			return True
		elif self.word_is_tea(named_item):
			return True
		elif self.word_is_pm(named_item):
			return True
		elif self.word_is_am(named_item):
			return True
		return False
	def has_time_word(self, date_string):
		if "hour" in date_string.lower():
			return True
		elif "minute" in date_string.lower():
			return True
		elif "second" in date_string.lower():
			return True
		return False
	def has_date_word(self, date_string):
		if "year" in date_string.lower() or "years" in date_string.lower():
			return True
		elif "month" in date_string.lower() or "months" in date_string.lower():
			return True
		elif "week" in date_string.lower() or "weeks" in date_string.lower():
			return True
		elif "day" in date_string.lower() or "days" in date_string.lower():
			return True
		return False
	def is_date_word(self, word):
		if self.word_is_year(word) or self.word_is_years(word):
			return True
		elif self.word_is_month(word) or self.word_is_months(word):
			return True
		elif self.word_is_week(word) or self.word_is_weeks(word):
			return True
		elif self.word_is_day(word) or self.word_is_days(word):
			return True
		return False
	# plural word
	def date_word_is_plural(self, word):
		if self.word_is_years(word):
			return True
		elif self.word_is_months(word):
			return True
		elif self.word_is_weeks(word):
			return True
		elif self.word_is_days(word):
			return True
		return False
	def is_time_word(self, word):
		if self.word_is_hour(word) or self.word_is_hours(word):
			return True
		elif self.word_is_min(word) or self.word_is_minutes(word):
			return True
		elif self.word_is_sec(word) or self.word_is_seconds(word):
			return True
		return False
	def has_word_now(self, date_string):
		return "now" in date_string.lower()
	def has_word_today(self, date_string):
		return "today" in date_string.lower()
	def has_word_yesterday(self, date_string):
		return "yesterday" in date_string.lower()

	def word_is_now(self, word):
		return "now" == word.lower()
	def word_is_today(self, word):
		return "today" == word.lower()
	def word_is_yesterday(self, word):
		return "yesterday" == word.lower()
	def word_is_year(self, word):
		return "year" == word.lower()
	def word_is_years(self, word):
		return "years" == word.lower()
	def word_is_month(self, word):
		return "month" == word.lower()
	def word_is_months(self, word):
		return "months" == word.lower()
	def word_is_week(self, word):
		return "week" == word.lower()
	def word_is_weeks(self, word):
		return "weeks" == word.lower()
	def word_is_day(self, word):
		return "day" == word.lower()
	def word_is_days(self, word):
		return "days" == word.lower()
	def word_is_hour(self, word):
		return "hour" == word.lower()
	def word_is_hours(self, word):
		return "hours" == word.lower()
	def word_is_min(self, word):
		return "min" == word.lower() or "minute" == word.lower()
	def word_is_minutes(self, word):
		return "minutes" == word.lower()
	def word_is_sec(self, word):
		return "sec" == word.lower() or "second" == word.lower()
	def word_is_seconds(self, word):
		return "seconds" == word.lower()
	def word_is_midnight(self, word):
		if "midnight" == word.lower():
			return True
		return False
	def word_is_noon(self, word):
		if "noon" == word.lower():
			return True
		return False
	def word_is_tea(self, word):
		if "tea" == word.lower():
			return True
		return False
	def word_is_pm(self, word):
		if "pm" == word.lower():
			return True
		return False
	def word_is_am(self, word):
		if "am" == word.lower():
			return True
		return False

	def is_month_word(self, word):
		if self.month_is_jan(word):
			return True
		elif self.month_is_feb(word):
			return True
		elif self.month_is_mar(word):
			return True
		elif self.month_is_apr(word):
			return True
		elif self.month_is_may(word):
			return True
		elif self.month_is_jun(word):
			return True
		elif self.month_is_jul(word):
			return True
		elif self.month_is_aug(word):
			return True
		elif self.month_is_sep(word):
			return True
		elif self.month_is_oct(word):
			return True
		elif self.month_is_nov(word):
			return True
		elif self.month_is_dec(word):
			return True
		return False
	def is_weekday_word(self, word):
		if self.weekday_is_mon(word):
			return True
		elif self.weekday_is_tue(word):
			return True
		elif self.weekday_is_wed(word):
			return True
		elif self.weekday_is_thu(word):
			return True
		elif self.weekday_is_fri(word):
			return True
		elif self.weekday_is_sat(word):
			return True
		elif self.weekday_is_sun(word):
			return True
		return False

	def has_weekday(self, date_string):
		if "monday" in date_string.lower():
			return True
		elif "tuesday" in date_string.lower():
			return True
		elif "wednesday" in date_string.lower():
			return True
		elif "thursday" in date_string.lower():
			return True
		elif "friday" in date_string.lower():
			return True
		elif "saturday" in date_string.lower():
			return True
		elif "sunday" in date_string.lower():
			return True
		return False
	def weekday_is_mon(self, day):
		if "monday" in day.lower() or "mon" in day.lower():
			return True
		return False
	def weekday_is_tue(self, day):
		if "tuesday" in day.lower() or "tue" in day.lower():
			return True
		return False
	def weekday_is_wed(self, day):
		if "wednesday" in day.lower() or "wed" in day.lower():
			return True
		return False
	def weekday_is_thu(self, day):
		if "thursday" in day.lower() or "thu" in day.lower():
			return True
		return False
	def weekday_is_fri(self, day):
		if "friday" in day.lower() or "fri" in day.lower():
			return True
		return False
	def weekday_is_sat(self, day):
		if "saturday" in day.lower() or "sat" in day.lower():
			return True
		return False
	def weekday_is_sun(self, day):
		if "sunday" in day.lower() or "sun" in day.lower():
			return True
		return False

	def has_month(self, date_string):
		if "january" in date_string.lower() or "jan" in date_string.lower():
			return True
		elif "february" in date_string.lower() or "feb" in date_string.lower():
			return True
		elif "march" in date_string.lower() or "mar" in date_string.lower():
			return True
		elif "april" in date_string.lower() or "apr" in date_string.lower():
			return True
		elif "may" in date_string.lower():
			return True
		elif "june" in date_string.lower() or "jun" in date_string.lower():
			return True
		elif "july" in date_string.lower() or "jul" in date_string.lower():
			return True
		elif "august" in date_string.lower() or "aug" in date_string.lower():
			return True
		elif "september" in date_string.lower() or "sep" in date_string.lower():
			return True
		elif "october" in date_string.lower() or "oct" in date_string.lower():
			return True
		elif "november" in date_string.lower() or "nov" in date_string.lower():
			return True
		elif "december" in date_string.lower() or "dec" in date_string.lower():
			return True
		return False
	def month_is_jan(self, month):
		if "january" == month.lower() or "jan" == month.lower():
			return True
		return False
	def month_is_feb(self, month):
		if "february" == month.lower() or "feb" == month.lower():
			return True
		return False
	def month_is_mar(self, month):
		if "march" == month.lower() or "mar" == month.lower():
			return True
		return False
	def month_is_apr(self, month):
		if "april" == month.lower() or "apr" == month.lower():
			return True
		return False
	def month_is_may(self, month):
		if "may" == month.lower():
			return True
		return False
	def month_is_jun(self, month):
		if "june" == month.lower() or "jun" == month.lower():
			return True
		return False
	def month_is_jul(self, month):
		if "july" == month.lower() or "jul" == month.lower():
			return True
		return False
	def month_is_aug(self, month):
		if "august" == month.lower() or "aug" == month.lower():
			return True
		return False
	def month_is_sep(self, month):
		if "september" == month.lower() or "sep" == month.lower():
			return True
		return False
	def month_is_oct(self, month):
		if "october" == month.lower() or "oct" == month.lower():
			return True
		return False
	def month_is_nov(self, month):
		if "november" == month.lower() or "nov" == month.lower():
			return True
		return False
	def month_is_dec(self, month):
		if "december" == month.lower() or "dec" == month.lower():
			return True
		return False

	# // return date - 1 day
	def date_to_yesterday(self, date):
		pass

	def relative_to_date(self, date):
		pass
