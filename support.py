#!/usr/bin/env python

from collections import OrderedDict
from datetime import datetime, date, timezone
from dateutil.relativedelta import relativedelta
import re


# // steal date formats from 'git'
"""
git log --since="<year-month-day>"
# --since=<date>, --after=<date>
# Show commit messages since <date>
# Show commits more recent than a specific date.
# ex. git log --since="2016-10-07"

git log --oneline --after=1.week.ago
git log --oneline --format="%h %an (%ar) - %s" --after=2.day.ago
git log --since="2.weeks.ago"
# gets the list of commits made in the last two weeks
git log --since="2.weeks.ago" --until="2.weeks.3.days.ago"
git log --until="2.weeks.ago" --since="2.weeks.3.days.ago"
2 years 1 day 3 minutes ago
# gets the list of commits made (between) after 2 weeks and 3 days after that
# from 2 weeks ago, to 3 days ago
# Timed reflogs
# Filter reflog by time
# http://alblue.bandlem.com/2011/05/git-tip-of-week-reflogs.html
# Working with dates in Git
# https://alexpeattie.com/blog/working-with-dates-in-git
# Specification for syntax of git dates
# http://stackoverflow.com/questions/14023794/specification-for-syntax-of-git-dates
# 
# Various supported forms include:
**** relative dates
** ex.
* today
* 1 month 2 days ago
* six minutes ago
# You can include days of the week ("last Tuesday"),
# timezones ("3PM GMT") and
# 'named' times ("noon", "tea time").
<number>.relative
* 1.minute.ago
* 1.hour.ago
* 1.day.ago
* 1.week.ago
* 1.month.ago
* 1.year.ago
* yesterday
* noon
* midnight
* tea
* PM
* AM
* never
* now
**** specific date, fixed dates (in any format)
** ex.
* 10-11-1998
* Fri Jun 4 15:46:55 2010 +0200
* 9/9/83
<year>-<month>-<day>(.<hour>:<minute>:<second>)
* 2011-05-17.09:00:00
* 2011-05-17
**** examples
git log --since=midnight
# get commits from all of today
git log --since="2 weeks ago"
# Show the changes during the last two weeks

# The plural forms are also accepted (e.g. 2.weeks.ago)
# as well as combinations (e.g. 1.day.2.hours.ago).
# 
# The time format is most useful if you want to get back to a branch's state as of an hour ago,
# or want to see what the differences were in the last hour (e.g. git diff @{1.hour.ago}).
# Note that if a branch is missing, then it assumes the current branch (so @{1.hour.ago}
# refers to master@{1.hour.ago} if on the branch master.
"""

class RelativeDate:
	def __init__(self, date):
		self._date = date

	@property
	def date(self):
		return self._date

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
		change_date = self._date
		if len(range_items) == 1:
			word = range_items[0]
			print("[* _remove_from_date].word '%s'" % word)
			if word.endswith("s"):
				print("[* _remove_from_date] removing 's' from '%s'" % word)
				word = word[0:-1]
			if self.is_date_word(word):
				range_items.insert(0, 1)
				print("[* _remove_from_date] change '%s' to '1 %s'" % (range_items[0], range_items[1]))

		if len(range_items) == 2:
			if "int" != type(range_items[0]).__name__ and "str" != type(range_items[1]).__name__:
				return False

			word_num = int(range_items[0])
			date_word = range_items[1]
			print("[* _remove_from_date] '%s %s'" % (word_num, date_word))
			#if self.is_date_word(date_word) or self.is_time_word(date_word):
			if self.is_date_word(date_word):
				if self.word_is_year(date_word):
					date_delta = DateHelper.remove_years_from_date(change_date, word_num)
					print("[+] remove '%s %s' - date: %s, delta: %s" % (word_num, date_word, change_date, date_delta))
					change_date = date_delta
				elif self.word_is_month(date_word):
					date_delta = DateHelper.remove_months_from(change_date, word_num)
					print("[+] remove '%s %s' - date: %s, delta: %s" % (word_num, date_word, change_date, date_delta))
					change_date = date_delta
				elif self.word_is_week(date_word):
					date_delta = DateHelper.remove_weeks_from(change_date, word_num)
					print("[+] remove '%s %s' - date: %s, delta: %s" % (word_num, date_word, change_date, date_delta))
					change_date = date_delta
				elif self.word_is_day(date_word):
					date_delta = DateHelper.remove_days_from(change_date, word_num)
					print("[+] remove '%s %s' - date: %s, delta: %s" % (word_num, date_word, change_date, date_delta))
					change_date = date_delta
			else:
				return False

		self._date = change_date
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
							date_ago_delta = DateHelper.remove_years_from_date(date_ago, word_num)
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
		if self.word_is_year(word):
			return True
		elif self.word_is_month(word):
			return True
		elif self.word_is_week(word):
			return True
		elif self.word_is_day(word):
			return True
		return False
	def is_time_word(self, word):
		if self.word_is_hour(word):
			return True
		elif self.word_is_min(word):
			return True
		elif self.word_is_sec(word):
			return True
		return False
	def has_word_now(self, date_string):
		if "now" in date_string.lower():
			return True
		return False
	def has_word_today(self, date_string):
		if "today" in date_string.lower():
			return True
		return False
	def has_word_yesterday(self, date_string):
		if "yesterday" in date_string.lower():
			return True
		return False

	def word_is_now(self, word):
		if "now" == word.lower():
			return True
		return False
	def word_is_today(self, word):
		if "today" == word.lower():
			return True
		return False
	def word_is_yesterday(self, word):
		if "yesterday" == word.lower():
			return True
		return False
	def word_is_year(self, word):
		if "year" == word.lower() or "years" == word.lower():
			return True
		return False
	def word_is_month(self, word):
		if "month" == word.lower() or "months" == word.lower():
			return True
		return False
	def word_is_week(self, word):
		if "week" == word.lower() or "weeks" == word.lower():
			return True
		return False
	def word_is_day(self, word):
		if "day" == word.lower() or "days" == word.lower():
			return True
		return False
	def word_is_hour(self, word):
		if "hour" == word.lower() or "hours" == word.lower():
			return True
		return False
	def word_is_min(self, word):
		if "min" == word.lower() or "min" == word.lower() or "minute" == word.lower() or "minutes" == word.lower():
			return True
		return False
	def word_is_sec(self, word):
		if "sec" == word.lower() or "sec" == word.lower() or "second" == word.lower() or "seconds" == word.lower():
			return True
		return False
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
	def change_to_month(self, month):
		month_digits = None
		if 'int' == type(month).__name__:
			if month >= 1 and month <= 12:
				month_digits = month
		elif 'str' == type(month).__name__ and self.is_month_word(month):
			month_digits = DateHelper.month_to_digits(month)

		if month_digits is not None:
			self._date = self._date.replace(month=month_digits)
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

# https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
class DateHelper:
	DATETIME_FORMAT_STANDARD = "%Y-%m-%d %H:%M:%S"
	DATETIME_FORMAT_MILISEC = "%Y-%m-%d %H:%M:%S.%f"
	def __init__(self, date):
		self._date = date

	@property
	def date(self):
		return self._date

	def as_string(self):
		return DateHelper.date_to_string(self._date)
	def as_time(self):
		return self._date.strftime('%H:%M:%S')

	# // format (string) date and return as type 'datetime'
	@staticmethod
	def format_date(date, date_format):
		formatted_date = date

		try:
			if "str" == type(formatted_date).__name__:
				formatted_date = date_parser.parse(formatted_date).strftime(date_format)
			elif "datetime" == type(formatted_date).__name__:
				formatted_date = date_parser.parse(formatted_date.isoformat()).strftime(date_format)
			else:
				formatted_date = None
		except:
			formatted_date = None

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
		return DateHelper.date_is_today(self._date)
		#today_date = DateHelper.now()
		#if self._date.year != today_date.year:
		#	return False
		#if self._date.month != today_date.month:
		#	return False
		#if self._date.day != today_date.day:
		#	return False
		#return True
	@property
	def is_yesterday(self):
		return DateHelper.date_is_yesterday(self._date)
		#yesterday_date = DateHelper.remove_days_from(DateHelper.now(), 1)
		#if self._date.year != yesterday_date.year:
		#	return False
		#if self._date.month != yesterday_date.month:
		#	return False
		#if self._date.day != yesterday_date.day:
		#	return False
		#return True

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
		return int(self._date.strftime("%H"))
	@property
	def minute_digits(self):
		return int(self._date.minute)
	@property
	def second(self):
		return int(self._date.second)
	@property
	def milisecond(self):
		return int(self._date.strftime("%f"))
	@property
	def time(self):
		return self._date.strftime("%H:%M:%S")

	@staticmethod
	def add_years_to_date(date, years):
		return date + relativedelta(years=years)
	@staticmethod
	def remove_years_from_date(date, years):
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
		#self._date = self._date + relativedelta(years=years)
		self._date = DateHelper.add_years_to_date(self._date, years)
	def remove_years(self, years):
		#self._date = self._date - relativedelta(years=years)
		self._date = DateHelper.remove_years_from_date(self._date, years)
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


	@property
	def days_in_month(self):
		last_day_of_month_date = DateHelper(datetime(self.year, self.month_digits, 1) + relativedelta(months=1, days=-1))
		return last_day_of_month_date.day_digits
