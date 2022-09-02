#!/usr/bin/env python

from shodan import Shodan
from shodan.helpers import get_ip
from shodan.cli.helpers import get_api_key as shodan_api_key

import argparse
import json
import os, sys
from collections import OrderedDict
from datetime import datetime, date, timezone
from dateutil.relativedelta import relativedelta
import io
from operator import attrgetter
from ipaddress import ip_address
import socket
import re
from support import RelativeDate, DateHelper
from fnmatch import fnmatch


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

class ShodanAPI:
	def __init__(self):
		self._init = False
		self._error_msg = None
		# Setup the Shodan API connection
		try:
			#self._api = Shodan(get_api_key())
			self._api = Shodan(shodan_api_key())
			self._init = True
		except Exception as e:
			self._error_msg = e

	@property
	def api_key(self):
		return shodan_api_key()
	@property
	def is_available(self):
		return self._init
	@property
	def has_error(self):
		return self._error_msg is not None
	@property
	def error_msg(self):
		if self._error_msg is not None:
			return self._error_msg
		return ''

	def _reset_error_msg(self):
		self._error_msg = None

	""" 
	reference: https://developer.shodan.io/api
	"""
	def info(self):
		data = None
		try:
			data = self._api.info()
		except Exception as e:
			self._error_msg = e
		return data

	@property
	def account_profile(self):
		data = None
		try:
			data = self._api._request('/account/profile', {})
		except Exception as e:
			self._error_msg = e
		return data

	# // host doe not cost any credit by query
	def host(self, host_ip, history=False):
		data = None
		try:
			data = self._api.host(host_ip, history=history)
		except Exception as e:
			self._error_msg = e
		return data

	# // the 'domain_info' api costs 1 credit by query
	def domain_info(self, domain, history=False, type="A"):
		data = None
		try:
			data = self._api.dns.domain_info(domain, history=history, type=type)
		except Exception as e:
			self._error_msg = e
		return data

class ShodanSettings:
	def __init__(self, args):
		self.settings = OrderedDict()
		#self.settings['Cache'] = False
		self.settings['Cache'] = True
		self.settings['Cache_Dir'] = "shodan-data"
		self.settings['Flush_Cache'] = False

		self.settings['Target'] = None
		self.settings['Include_History'] = False
		self.settings['No_DNS_Lookup'] = args.no_dns_lookup

		self.settings['Verbose_Mode'] = False
		self.settings['Out_Host_Only'] = False

		self.settings['Out_Head_Service_Count'] = 0
		self.settings['Out_Tail_Service_Count'] = 0
		self.settings['Out_Sort_By_Scan_Date'] = False
		
		self.settings['Out_Host_JSON'] = False
		self.settings['Out_Service_Data'] = False
		self.settings['Out_Service_Module'] = False
		self.settings['Out_Service_JSON'] = False
		self.settings['Out_Custom_Fields'] = []

		self.settings['Match_On_Ports'] = []
		self.settings['Match_On_Modules'] = []
		self.settings['Match_On_ShodanID'] = []
		self.settings['Match_On_Scanned_Hostname'] = []
		self.settings['Match_On_Custom_Conditions'] = []
		self.settings['Match_On_Crawler'] = []
		self.settings['Match_On_Scan_Id'] = []
		self.settings['Filter_Out_Ports'] = []
		self.settings['Filter_Out_Modules'] = []
		self.settings['Filter_Out_Scanned_Hostname'] = []


		self.settings['Date_Since'] = None
		self.settings['Date_After'] = None
		self.settings['Date_Until'] = None
		self.settings['Date_Before'] = None
		
		self.init(args)

	def init(self, args):
		#self.settings['Cache'] = args.cache
		if args.cache_dir is not None:
			self.settings['Cache_Dir'] = args.cache_dir
		self.settings['Flush_Cache'] = args.flush_cache

		self.settings['Target'] = args.target
		self.settings['Include_History'] = args.include_history

		self.settings['Verbose_Mode'] = args.verbose_mode
		self.settings['Debug_Mode'] = args.debug_mode
		self.settings['Out_Host_Only'] = args.out_host_only
		
		self.settings['Out_Sort_By_Scan_Date'] = args.out_sort_by_scan_date
		if args.out_head_service_count is not None:
			self.settings['Out_Head_Service_Count'] = args.out_head_service_count
		if args.out_tail_service_count is not None:
			self.settings['Out_Tail_Service_Count'] = args.out_tail_service_count
		
		self.settings['Out_Host_JSON'] = args.out_host_json
		self.settings['Out_Service_Data'] = args.out_service_data
		self.settings['Out_Service_Module'] = args.out_service_module
		self.settings['Out_Service_JSON'] = args.out_service_json
		if args.match_on_ports is not None:
			for port in args.match_on_ports.split(','):
				self.settings['Match_On_Ports'].append(int(port.strip()))
		if args.match_on_modules is not None:
			for module in args.match_on_modules.split(','):
				self.settings['Match_On_Modules'].append(module.strip())
		if args.match_on_shodan_id is not None:
			for shodan_id in args.match_on_shodan_id.split(','):
				self.settings['Match_On_ShodanID'].append(shodan_id.strip())
		if args.match_on_scanned_hostname is not None:
			for scanned_hostname in args.match_on_scanned_hostname.split(','):
				self.settings['Match_On_Scanned_Hostname'].append(scanned_hostname.strip())
		if args.match_on_custom_conditions is not None:
			for condition in args.match_on_custom_conditions.split(','):
				self.settings['Match_On_Custom_Conditions'].append(condition.strip())
		if args.out_custom_fields is not None:
			for condition in args.out_custom_fields.split(','):
				self.settings['Out_Custom_Fields'].append(condition.strip())
		if args.match_on_crawler is not None:
			for scanned_hostname in args.match_on_crawler.split(','):
				self.settings['Match_On_Crawler'].append(scanned_hostname.strip())
		if args.match_on_scan_id is not None:
			for scanned_hostname in args.match_on_scan_id.split(','):
				self.settings['Match_On_Scan_Id'].append(scanned_hostname.strip())
		
		
		if args.filter_out_ports is not None:
			for port in args.filter_out_ports.split(','):
				self.settings['Filter_Out_Ports'].append(int(port.strip()))
		if args.filter_out_modules is not None:
			for module in args.filter_out_modules.split(','):
				self.settings['Filter_Out_Modules'].append(module.strip())
		if args.filter_out_scanned_hostname is not None:
			for scanned_hostname in args.filter_out_scanned_hostname.split(','):
				self.settings['Filter_Out_Scanned_Hostname'].append(scanned_hostname.strip())

		if args.date_since is not None:
			self.settings['Date_Since'] = args.date_since
		if args.date_after is not None:
			self.settings['Date_After'] = args.date_after
		if args.date_until is not None:
			self.settings['Date_Until'] = args.date_until
		if args.date_before is not None:
			self.settings['Date_Before'] = args.date_before

class ShodanCli:
	def __init__(self, args):
		self.settings = ShodanSettings(args).settings
		self._args = args
		self.api = ShodanAPI()
		self._cache_data = None
		self._setup_cache()

	def _setup_cache(self):
		self._cache_data = None
		if not self.settings['Cache']:
			return

		if not os.path.isdir(self.settings['Cache_Dir']):
			os.mkdir(self.settings['Cache_Dir'])

		out_file = self._target_as_out_file(self.settings['Target'])
		cache_file = self._get_out_path(out_file)
		self.settings['Cache_File'] = cache_file

	def _target_as_out_file(self, target):
		return "host.%s.json" % target
	def _out_file_as_target(self, file):
		if file.startswith("host.") and file.endswith(".json"):
			return '.'.join(file.split('.')[1:5])
		return ''
	def _get_out_path(self, file):
		return os.path.join(self.settings['Cache_Dir'], file)

	@property
	def use_cache(self):
		return self.settings["Cache"]
	@property
	def cache_exists(self):
		if "Cache_File" not in self.settings:
			return False
		if os.path.isfile(self.settings['Cache_File']):
			if os.path.getsize(self.settings['Cache_File']) > 0:
				return True
		return False

	def get_cache(self):
		if self._cache_data is not None:
			return self._cache_data
		if not self.cache_exists:
			return None
		return self.get_cache_by_file(self.settings['Cache_File'])
	def get_cache_by_file(self, file):
		if os.path.isfile(file):
			with open(file, 'r') as f:
				return json.load(f)
		return None
	def cache_host(self):
		if "Cache_File" not in self.settings:
			return
		target = self.settings['Target']
		include_history = self.settings['Include_History']
		self.cache_host_ip(target, include_history)
	def cache_host_ip(self, target, include_history):
		self._cache_data = self.api.host(target, include_history)
		if self.api.has_error:
			print("[!] shodan api error '%s'" % self.api.error_msg)
			self.api._reset_error_msg()
		if self._cache_data is not None:
			cache_file = self._get_out_path(self._target_as_out_file(target))
			with open(cache_file, "w") as f:
				f.write(json.dumps(self._cache_data))

	def _target_is_ip_address(self, target):
		try:
			ip = ip_address(target)
			return True
		except ValueError:
			return False
	def _target_is_cache_index(self, target):
		if target.isnumeric():
			return True
		return False
	def _target_is_domain_host(self, target):
		if '.' in target and not self._target_is_ip_address(target):
			return True
		return False
	def _target_is_cached(self, target):
		dir_list = os.listdir(self.settings['Cache_Dir'])
		for file in dir_list:
			if not file.startswith("host.") or not file.endswith(".json"):
				continue
			if target == self._out_file_as_target(file):
				return True
		return False
	def _get_target_by_cache_index(self, cache_index):
		target = None
		if not self._target_is_cache_index(cache_index):
			return target
		dir_list = os.listdir(self.settings['Cache_Dir'])
		if int(cache_index) < 0 or int(cache_index) >= len(dir_list):
			return target
		cache_file = dir_list[int(cache_index)]
		target = self._out_file_as_target(cache_file)
		return target

class Location:
	def __init__(self, json_data):
		self._json = json_data
		self.country_code = '' if 'country_code' not in self._json else self._json['country_code']
		self.country_name = '' if 'country_name' not in self._json else self._json['country_name']
		self.country = "%s - %s" % (self._json['country_code'], self._json['country_name'])
		self.city = self._json['city']
		self.longitude = self._json['longitude']
		self.latitude = self._json['latitude']
		self.geo = "%s, %s (long, lat)" % (self._json['longitude'], self._json['latitude'])

	def as_string(self):
		data = ""
		
		#self.region_code
		data = "%s (%s), %s" % (self.country_name, self.country_code, self.city)
		data = "%s # long: %s, lat: %s" % (data, self.longitude,self.latitude)
		return data
class Shodan_Host:
	def __init__(self, settings, host_json, include_history):
		self._json = host_json
		self.settings = settings
		self.last_update = '' if 'last_update' not in self._json else self._json['last_update']
		self.ip = self._json['ip_str']
		self.asn = '' if 'asn' not in self._json else self._json['asn']
		self.hostnames = self._json['hostnames']
		self.domains = self._json['domains']
		self.location = Location(self._json)
		self.isp = self._json['isp']
		self.org = self._json['org']
		self.services = []
		self._init_services(include_history)

	def _init_services(self, include_history):
		service_ports = OrderedDict()
		if self.settings['Out_Sort_By_Scan_Date']:
			#service_ports[port].append(Port_Service(port_json))
			for port_json in self._json['data']:
				self.services.append(Port_Service(port_json))
				self.services = sorted(self.services, key=attrgetter('timestamp'))
		else:
			#service_ports = OrderedDict()
			for port_json in self._json['data']:
				port = int(port_json['port'])
				if port not in service_ports:
					service_ports[port] = []
				service_ports[port].append(Port_Service(port_json))

			# sort by timestamp by grouped ports
			for port in service_ports:
				service_ports[port] = sorted(service_ports[port], key=attrgetter('timestamp'))

			sorted_ports = sorted(service_ports)
			if include_history:
				for port in sorted_ports:
					first_seen_date = datetime.strptime(service_ports[port][0].timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
					for service in service_ports[port]:
						service.first_seen = first_seen_date
						self.services.append(service)
			else:
				for port in sorted_ports:
					service_first_scan = service_ports[port][0]
					service_last_scan = service_ports[port][-1]
					first_seen_date = datetime.strptime(service_first_scan.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
					service_last_scan.first_seen = first_seen_date
					#print("%s : %s" % (service_last_scan.port, service_last_scan.identifier))
					self.services.append(service_last_scan)

	@property
	def json(self):
		#// do not return 'data' from json blob
		data = self._json
		for item in data:
			if item == "data":
				data.pop(item)
				break
		data = json.dumps(data, indent=4)
		return data
	@property
	def has_os(self):
		if 'os' in self._json:
			if self._json["os"] is not None:
				return True
		return False
	@property
	def os(self):
		if self.has_os:
			return self._json["os"]
		return ""
	def get_os_by_services(self):
		os_list = []
		for service in self.services:
			if service.has_os:
				if service.os in os_list:
					continue
				os_list.append(service.os)
		return os_list

	@property
	def has_vulns(self):
		if len(self.vulns) > 0:
			return True
		return False
	@property
	def vulns(self):
		if 'vulns' not in self._json:
			return []
		data = self._json["vulns"]
		data.sort()
		return data

	def as_location(self):
		data = ""
		
		#self.region_code
		data = "%s (%s), %s" % (self.country_name, self.country_code, self.city)
		data = "%s # long: %s, lat: %s" % (data, self.longitude,self.latitude)
		return data

	@property
	def host_ports(self):
		ports = self._json["ports"]
		ports.sort()
		return ports
		
		
class Port_Service:
	def __init__(self, json_data):
		self._json = json_data
		self.port = int(self._json['port'])
		self.protocol = self._json['transport']
		self.timestamp = '' if 'timestamp' not in self._json else self._json['timestamp']
		self.scan_date = ''
		if len(self.timestamp) > 0:
			#self.scan_date = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S.%f")
			self.scan_date = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d")
		self.product = Service_Product(self._json)
		self.first_seen = ''

	@property
	def identifier(self):
		if "_shodan" in self._json and "id" in self._json["_shodan"]:
			return self._json["_shodan"]["id"]
		return ''
	@property
	def crawler(self):
		if "_shodan" in self._json and "crawler" in self._json["_shodan"]:
			return self._json["_shodan"]["crawler"]
		return ''
	@property
	def scanned_hostname(self):
		if "_shodan" in self._json and "options" in self._json["_shodan"] and "hostname" in self._json["_shodan"]["options"]:
			return self._json["_shodan"]["options"]["hostname"]
		return ''
	@property
	def scan_id(self):
		if "_shodan" in self._json and "options" in self._json["_shodan"] and "scan" in self._json["_shodan"]["options"]:
			return self._json["_shodan"]["options"]["scan"]
		return ''
	
	@property
	def banner(self):
		data = ""
		if len(self.product.name) > 0:
			data = self.product.name
			if len(self.product.version) > 0:
				data = "%s %s" % (data, self.product.version)
			if len(self.product.info) > 0:
				data = "%s (%s)" % (data, self.product.info)
		return data
	@property
	def has_data(self):
		if len(self._json['data']) > 0:
			return True
		return False
	@property
	def data(self):
		return self._json['data']
	@property
	def has_module(self):
		if "_shodan" in self._json and "module" in self._json["_shodan"]:
			return True
		return False
	@property
	def module_name(self):
		if self.has_module:
			return self._json["_shodan"]["module"]
		return None
	@property
	def has_module_data(self):
		if self.get_module_data() is not None:
			return True
		return False
	def get_module_data(self):
		if not self.has_module:
			return None
		module_name = self.module_name
		if module_name in self._json:
			return self._json[module_name]
		elif '-' in self.module_name:
			module_name = module_name.split('-')[0]
			if module_name in self._json:
				return self._json[module_name]
		return None
	@property
	def has_os(self):
		if 'os' in self._json:
			if self._json["os"] is not None:
				return True
		return False
	@property
	def os(self):
		if self.has_os:
			return self._json["os"]
		return ""

	@property
	def has_tags(self):
		return 'tags' in self._json
	@property
	def tags(self):
		if 'tags' in self._json:
			return self._json['tags']
		return ''

	@property
	def is_web_service(self):
		if self.module_name is not None:
			if 'https' == self.module_name or 'http' == self.module_name or self.module_name.lower().startswith("http-"):
				return True
		return False
	@property
	def is_ssh_service(self):
		if self.module_name is not None:
			if 'ssh' == self.module_name or self.module_name.lower().startswith("ssh-"):
				return True
		return False
class Service_Product:
	def __init__(self, json_data):
		self._json = json_data
		self.name = '' if 'product' not in self._json else self._json['product']
		self.version = '' if 'version' not in self._json else self._json['version']
		self.info = '' if 'info' not in self._json else self._json['info']

	def is_cobaltstrike(self):
		print("is_cobaltstrike: '%s'" % self.name)
		if self.name.lower() == "cobalt strike beacon":
			return True
		return False
	def is_openssh(self):
		if "openssh" in self.name.lower():
			return True
		return False
	def is_apache(self):
		if "apache" in self.name.lower():
			return True
		return False
	def is_nginx(self):
		if "nginx" in self.name.lower():
			return True
		return False

class Product_Cobalt_Strike_Beacon:
	def __init__(self, ssh_service):
		self.service = ssh_service
		self._json = self.service._json

class Module_SSH:
	def __init__(self, ssh_service):
		self.service = ssh_service
		self._json = self.service._json

	@property
	def hassh(self):
		if self.service.get_module_data() is not None:
			data = self.service.get_module_data()
			if 'hassh' in data:
				return data['hassh']
		return None
	
	@property
	def fingerprint(self):
		if self.service.get_module_data() is not None:
			data = self.service.get_module_data()
			if 'fingerprint' in data:
				return data['fingerprint']
		return None
	
	@property
	def type(self):
		if self.service.get_module_data() is not None:
			data = self.service.get_module_data()
			if 'type' in data:
				return data['type']
		return None
class HTTP_SSL_Cert:
	def __init__(self, json_data):
		self._json = json_data

	@property
	def has_ssl(self):
		return 'ssl' in self._json
	@property
	def data(self):
		if self.has_ssl:
			return self._json['ssl']
		return None

	@property
	def issued(self):
		if 'cert' in self.data:
			return datetime.strptime(self.data['cert']['issued'], '%Y%m%d%H%M%SZ').strftime("%Y-%m-%d %H:%M:%S")
		return None
	@property
	def expires(self):
		if 'cert' in self.data:
			return datetime.strptime(self.data['cert']['expires'], '%Y%m%d%H%M%SZ').strftime("%Y-%m-%d %H:%M:%S")
		return None
	@property
	def expired(self):
		if 'cert' in self.data and 'expired' in self.data['cert']:
			return self.data['cert']['expired']
		return True
	@property
	def fingerprint(self):
		if 'cert' in self.data and 'fingerprint' in self.data['cert']:
			return self.data['cert']['fingerprint']['sha256']
		return None
	@property
	def serial(self):
		if 'cert' in self.data and 'serial' in self.data['cert']:
			return self.data['cert']['serial']
		return None
	@property
	def subject_cn(self):
		if 'cert' in self.data and 'subject' in self.data['cert'] and 'CN' in self.data['cert']['subject']:
			return self.data['cert']['subject']['CN']
		return None
	@property
	def issuer_cn(self):
		if 'cert' in self.data and 'issuer' in self.data['cert'] and 'CN' in self.data['cert']['issuer']:
			return self.data['cert']['issuer']['CN']
		return None

class Module_HTTP:
	def __init__(self, http_service):
		self.service = http_service
		self._json = self.service._json

	@property
	def has_headers(self):
		if len(self.headers):
			return True
		return False
	def header_exists(self, header_name):
		if self.has_headers:
			if header_name in self.headers:
				return True
		return False
	def get_header(self, header_name):
		if self.header_exists(header_name):
			return self.headers[header_name]
		return ''
	@property
	def headers(self):
		status_head, headers_dict = self._parse_headers(io.StringIO(self.service.data))
		return headers_dict
	@property
	def header_status(self):
		status_head, headers_dict = self._parse_headers(io.StringIO(self.service.data))
		return status_head

	@property
	def has_ssl_cert(self):
		if self.is_ssl:
			return 'cert' in self.ssl_data
		return False
	@property
	def ssl_cert(self):
		return HTTP_SSL_Cert(self._json)
	@property

	def is_ssl(self):
		return 'ssl' in self._json
	@property
	def ssl_data(self):
		if self.is_ssl:
			return self._json['ssl']
		return None

	@property
	def jarm(self):
		if 'https' == self.service.module_name and self.is_ssl:
			if 'jarm' in self.ssl_data:
				return self.ssl_data['jarm']
		return None
	@property
	def ja3s(self):
		if 'https' == self.service.module_name and self.is_ssl:
			if 'ja3s' in self.ssl_data:
				return self.ssl_data['ja3s']
		return None
	@property
	def tls_versions(self):
		result = []
		if 'versions' in self.ssl_data:
			# only include supported tls versions
			for version in self.ssl_data['versions']:
				if not version.startswith("-"):
					result.append(version)
		return result

	def _parse_headers(self, ioheaders):
		"""
		parses an http response into the status-line and headers
		"""
		status_head = ioheaders.readline().strip()
		headers = {}
		for line in ioheaders:
			item = line.strip()
			if not item:
				break
			item = item.split(':', 1)
			if len(item) == 2:
				key, value = item
				value = value.strip()
				# // concat duplicate headers
				if key in headers:
					value = "%s; %s" % (headers[key], value)
				headers[key] = value # remove leading/trailing whitespace
		return status_head, headers

	@property
	def favicon_hash(self):
		if 'http' in self._json and 'favicon' in self._json['http'] and 'hash' in self._json['http']['favicon']:
			return self._json['http']['favicon']['hash']
		return None
	@property
	def content(self):
		if 'html' in self._json:
			return self._json['html']
		return None

	@property
	def web_technologies(self):
		result = []
		if 'http' in self._json and "components" in self._json['http']:
			for technology in self._json['http']['components']:
				categories = self._json['http']['components'][technology]['categories']
				#result.append('"%s": "%s"' % (technology, ', '.join(categories)))
				result.append('%s (%s)' % (technology, ', '.join(categories)))
		return result

	def has_waf(self):
		if self.waf is not None:
			return True
		return False
	@property
	def waf(self):
		module_data = self.service.get_module_data()
		if module_data is not None:
			if 'waf' in module_data and module_data['waf'] is not None:
				return module_data['waf']
		return None
def match_service_on_condition(shodan, service):
	if not match_on_service(shodan, service):
		return False
	if filter_out_service(shodan, service):
		return False

	return True
def match_on_service(shodan, service):
	# // filter IN service based on conditions
	if len(shodan.settings['Match_On_ShodanID']) > 0:
		if service.identifier not in shodan.settings['Match_On_ShodanID']:
			return False
	if len(shodan.settings['Match_On_Crawler']) > 0:
		if service.crawler not in shodan.settings['Match_On_Crawler']:
			return False
	if len(shodan.settings['Match_On_Scan_Id']) > 0:
		if service.scan_id not in shodan.settings['Match_On_Scan_Id']:
			return False

	if len(shodan.settings['Match_On_Ports']) > 0:
		if service.port not in shodan.settings['Match_On_Ports']:
			return False
	if len(shodan.settings['Match_On_Modules']) > 0:
		module_name = service.module_name
		if '-' in module_name:
			module_name = module_name.split('-')[0]
		if service.module_name not in shodan.settings['Match_On_Modules'] and module_name not in shodan.settings['Match_On_Modules']:
			return False

	if len(shodan.settings['Match_On_Scanned_Hostname']) > 0:
		# // match on single hostname
		if len(shodan.settings['Match_On_Scanned_Hostname']) == 1:
			if len(shodan.settings['Match_On_Scanned_Hostname'][0]) == 0:
				if len(service.scanned_hostname) != 0:
					return False
			elif not fnmatch(service.scanned_hostname, shodan.settings['Match_On_Scanned_Hostname'][0]):
				return False
		else:
			# // if any hostname match then filter IN
			found_hostname = False
			for hostname in shodan.settings['Match_On_Scanned_Hostname']:
				if fnmatch(service.scanned_hostname, hostname):
					found_hostname = True
					break
			if not found_hostname:
				return False

	if len(shodan.settings['Match_On_Custom_Conditions']) > 0:
		if not match_service_on_custom_conditions(shodan, service):
			return False

	return True

def get_json_path(json_dict, path):
	json_data = json_dict

	fields = path.split('.')
	last_field_index = len(fields)-1

	for i in range(len(fields)):
		field = fields[i]
		field_exists = field in json_data

		if not field_exists:
			return False, None
		
		json_data = json_data[field]
		field_type = type(json_data).__name__
		if last_field_index == i:
			return True, json_data
	return False, None
def show_json_path_as_field(shodan, service):
	fill_prefix = "\t\t\t\t"
	fields = []
	field = OrderedDict()
	field["path"] = "_shodan.module"
	field["name"] = "Section - WEB Info"
	field["conditions"] = ["_shodan.module:value=http"]
	field["value"] = "static:WEB Info"
	field["prefix"] = ""
	fields.append(field)

	field = OrderedDict()
	field["path"] = "_shodan.options.hostname"
	field["name"] = "Scanned Host"
	field["conditions"] = ["_shodan.module:value=http", "_shodan.options.hostname:exists", "_shodan.options.hostname:has-value"]
	field["value"] = "json:path"
	field["prefix"] = "\t"
	fields.append(field)

	field = OrderedDict()
	field["path"] = "http.title"
	field["name"] = "Page Title"
	field["conditions"] = ["_shodan.module:value=http", "http.title:exists", "http.title:has-value"]
	field["value"] = "json:path"
	field["prefix"] = "\t"
	fields.append(field)

	for field in fields:
		all_condition_match = True
		for custom in field["conditions"]:
			path = custom.split(':')[0].strip().lower()
			field_condition = custom.split(':')[1].strip().lower()
			
			if not match_on_json_condition(service._json, path, field_condition, shodan.settings['Debug_Mode']):
				all_condition_match = False
		if all_condition_match:
			if field["value"].startswith("static:"):
				path_exists = True
				#path_value = field["value"].split(":")[1]
				path_value = "%s" % field["value"].split(":")[1]
			elif field["value"].startswith("json:"):
				path_exists, path_value = get_json_path(service._json, field["path"])
				path_value = "%s: %s" % (field["name"], path_value)
			if path_exists and shodan.settings["Verbose_Mode"]:
				#print("%s***** %s%s(%s): %s" % (fill_prefix, field["prefix"], field["name"], field["path"], path_value))
				print("%s***** %s%s" % (fill_prefix, field["prefix"], path_value))
	
	if len(shodan.settings['Out_Custom_Fields']) == 0:
		return
	fill_prefix = "\t\t\t\t\t"
	#path_to_field["fields"] = []
	#field = OrderedDict()
	#path_to_field["fields"][]
	path_to_field = OrderedDict()
	path_to_field["_shodan.options.hostname"] = "hostname"
	path_to_field["http.title"] = "Page Title"
	conditions = OrderedDict()
	conditions["path"] = "exists"
	conditions["value"] = "has-value"
	found_path = False
	
	out_data = ""
	for custom in shodan.settings['Out_Custom_Fields']:
		if ':' in custom and len(custom.split(':')) == 2:
			path = custom.split(':')[0].strip().lower()
			field_condition = custom.split(':')[1].strip().lower()

			if not match_on_json_condition(service._json, path, field_condition, shodan.settings['Debug_Mode']):
				continue

			path_exists, path_value = get_json_path(service._json, path)
			path_type = type(path_value).__name__
			print("json-path - path: %s, exists: %s, type: %s" % (path_type, path_exists, path))

			if path_exists:
				found_path = True
				if len(out_data) > 1:
					out_data = "%s\n" % out_data
				field_name = path
				if field_name in path_to_field:
					field_name = path_to_field[path]
				out_data = "%s%s%s: %s" % (out_data, fill_prefix, field_name, path_value)
	if found_path:
		print("%s" % ("*" * 39 * 2))
		print(out_data)
		print("%s" % ("*" * 39 * 2))

def match_service_on_custom_conditions(shodan, service):
	if len(shodan.settings['Match_On_Custom_Conditions']) == 0:
		return True

	for custom_condition in shodan.settings['Match_On_Custom_Conditions']:
		if ':' in custom_condition and len(custom_condition.split(':')) == 2:
			path = custom_condition.split(':')[0].strip().lower()
			field_condition = custom_condition.split(':')[1].strip().lower()

			#if match_on_json_condition(shodan, service._json, path, field_condition):
			if match_on_json_condition(service._json, path, field_condition, shodan.settings['Debug_Mode']):
				return True
	return False
def match_on_json_condition(json, path, field_condition, debug=False):
	path_exists, path_value = get_json_path(json, path)

	path_type = type(path_value).__name__
	#if path_type == "NoneType" or path_type is None:
	if path_type == "NoneType" or path_value is None:
		path_type = "null"
	elif path_type == "dict":
		path_type = "json"
	elif path_type == "bool":
		if field_condition.startswith("value="):
			if path_value:
				path_value = "true"
			else:
				path_value = "false"
			#path_type = str(path_value).lower()
	if debug:
		print("-match_on_json_condition() condition '%s:%s', path.exists: %s, data.type: %s" % (path, field_condition, path_exists, path_type))

	if field_condition == "exists" or field_condition == "not-exists" or field_condition == "exist" or field_condition == "not-exist":
		if field_condition.startswith("exist") and path_exists:
			return True
		if field_condition.startswith("not-exist") and not path_exists:
			return True
	if field_condition == "has-value" or field_condition == "no-value" or field_condition == "not-null":
		#if (field_condition == "has-value" or field_condition == "not-null") and path_type != "null" and path_type != "bool" and path_value is not None and len(path_value) != 0:
		if (field_condition == "has-value" or field_condition == "not-null") and path_type != "null" and path_type != "bool" and path_value is not None:
			if (path_type == "str" or path_type == "list") and len(path_value) != 0:
				return True
			else:
				return True
		if field_condition == "no-value" and (path_type == "null" or path_value is None or len(path_value) == 0):
			return True
	#if not path_exists:
	#	return False

	if field_condition.startswith("equal=") or field_condition.startswith("value=") or field_condition.startswith("not-equal=") or field_condition.startswith("equals=") or field_condition.startswith("not-equals="):
		condition_value = field_condition.split("=")[1]
		if not field_condition.startswith("not-") and condition_value == path_value:
			return True
		if field_condition.startswith("not-") and condition_value != path_value:
			return True

	if field_condition.startswith("contains=") or field_condition.startswith("not-contains=") or field_condition.startswith("has=") or field_condition.startswith("not-has="):
		condition_value = field_condition.split("=")[1]
		if not field_condition.startswith("not-") and path_type == "str" and condition_value in path_value.lower():
			return True
		if field_condition.startswith("not-") and path_type == "str" and condition_value not in path_value.lower():
			return True

	if field_condition.startswith("type=") or field_condition.startswith("not-type="):
		condition_value = field_condition.split("=")[1]
		if not field_condition.startswith("not-") and condition_value == path_type:
			return True
		if field_condition.startswith("not-") and condition_value != path_type:
			return True

	if field_condition.startswith("len=") or field_condition.startswith("not-len=") or field_condition.startswith("min-len=") or field_condition.startswith("max-len="):
		condition_value = field_condition.split("=")[1].strip()
		if debug and path_value is not None:
			print("%s(type: %s): %s, data.len: %s" % (field_condition, type(condition_value).__name__, condition_value, len(path_value)))
		if type(condition_value).__name__ == "str" and condition_value.isnumeric():
			condition_value = int(condition_value)
			if field_condition.startswith("len=") and path_type != "null" and len(path_value) == condition_value:
				return True
			if field_condition.startswith("not-len=") and path_type != "null" and len(path_value) != condition_value:
				return True
			if field_condition.startswith("min-len=") and path_type != "null" and len(path_value) >= condition_value:
				return True
			if field_condition.startswith("max-len=") and path_type != "null" and len(path_value) <= condition_value:
				return True
	if debug:
		print("***************************************\n%s\n***************************************" % path_value)
	return False

def filter_out_service(shodan, service):
	# // filter OUT service based on conditions
	if len(shodan.settings['Filter_Out_Ports']) > 0:
		if service.port in shodan.settings['Filter_Out_Ports']:
			return True
	if len(shodan.settings['Filter_Out_Modules']) > 0:
		module_name = service.module_name
		if '-' in module_name:
			module_name = module_name.split('-')[0]
		if service.module_name in shodan.settings['Filter_Out_Modules'] or module_name in shodan.settings['Filter_Out_Modules']:
			return True

	if len(shodan.settings['Filter_Out_Scanned_Hostname']) > 0:
		# // match on single hostname
		if len(shodan.settings['Filter_Out_Scanned_Hostname']) == 1:
			if len(shodan.settings['Filter_Out_Scanned_Hostname'][0]) == 0:
				if len(service.scanned_hostname) == 0:
					return True
			elif fnmatch(service.scanned_hostname, shodan.settings['Filter_Out_Scanned_Hostname'][0]):
				return True
		else:
			# // if any hostname match then filter IN
			for hostname in shodan.settings['Filter_Out_Scanned_Hostname']:
				if fnmatch(service.scanned_hostname, hostname):
					return True

	return False
def out_shodan(shodan):
	host_json = shodan.get_cache()

	print("* Shodan\n %s" % ('-'*30))
	#print("Target: %s" % shodan.settings["Target"])
	
	host = Shodan_Host(shodan.settings, host_json, shodan.settings['Include_History'])

	if not shodan.settings['No_DNS_Lookup']:
		ip_host = ip_to_host(host.ip)
		if ip_host is not None:
			#print("IP Address to Host: %s" % ip_host)
			print("Target: %s (Host: %s)" % (shodan.settings["Target"], ip_host))
		else:
			print("Target: %s" % shodan.settings["Target"])

	print("Last Update: %s" % host.last_update)
	print("")

	print("* Host Overview\n %s" % ('-'*30))
	print("IP Address: %s" % host.ip)
	if host.has_os:
		print("OS: %s" % host.os)
	else:
		os_list = host.get_os_by_services()
		if len(os_list) > 0:
			print("OS: %s # based on services!" % ', '.join(os_list))
	print("Hostnames: %s" % ', '.join(host.hostnames))
	print("Domains: %s" % ', '.join(host.domains))
	print("Ports: %s" % ", ".join([str(int) for int in host.host_ports])) # convert int to str
	print("Location: %s" % host.location.as_string())
	print("")
	print("ISP: %s" % host.isp)
	print("Organization: %s" % host.org)
	print("ASN: %s" % host.asn)
	print("")
	if host.has_vulns:
		print("Vulns: %s" % ', '.join(host.vulns))
		print("")
	#

	print("Service scans: %s" % len(host.services))
	
	if shodan.settings['Out_Host_JSON']:
		host_data = ["[*] %s" % l for l in host.json.split('\n') if len(l) > 0 ]
		print('\n'.join(host_data))
	if shodan.settings['Out_Host_Only']:
		return
	print("* Service Overview\n %s" % ('-'*30))
	# // format service headers
	print("Scan-Date\tPort      Service\tVersion / Info")
	print("%s\t%s      %s\t%s" % (("-"*len("Scan-date")), ("-"*len("Port")), ("-"*len("Service")), ("-"*len("Version / Info"))))

	filtered_services = []
	for service in host.services:
		# filter in/out based on condition
		if match_service_on_condition(shodan, service):
			filtered_services.append(service)
		
	filtered_services = filter_list_by_head_tail(shodan, filtered_services)

	for service in filtered_services: 
		# // output service overview
		fill_prefix = 1
		service_header = "%s/%s" % (service.port, service.protocol.upper())
		module_name = service.module_name
		if '-' in module_name:
			module_name = module_name.split('-')[0]
		if len(service_header) < 9:
			fill_prefix = 9 - len(service_header) + 1
		service_header = "%s%s%s" % (service_header, (" " * fill_prefix), module_name)
		if len(service.banner) > 0:
			if len(module_name) <= 4:
				service_header = "%s\t" % (service_header)
			service_header = "%s\t%s" % (service_header, service.banner)
		elif len(module_name) != len(service.module_name):
			service_header = "%s\t\t(%s)" % (service_header, service.module_name)
		print("%s\t%s" % (service.scan_date, service_header))

		fill_prefix = "\t\t\t\t\t"

		if shodan.settings['Verbose_Mode']:
			shodan_header = "%sShodan - ID: %s" % (fill_prefix, service.identifier)
			#print("%sShodan.ID: %s" % (fill_prefix, service.identifier))
			#if len(service.scanned_hostname) > 0:
			#	shodan_header = "%s, Scanned Host: %s" % (shodan_header, service.scanned_hostname)
			if len(service.crawler) > 0:
				shodan_header = "%s, Crawler: %s" % (shodan_header, service.crawler)
			if len(service.scan_id) > 0:
				shodan_header = "%s, Scan Id: %s" % (shodan_header, service.scan_id)
			print(shodan_header)
			if len(service.scanned_hostname) > 0:
				#shodan_header = "%s, Scanned Host: %s" % (shodan_header, service.scanned_hostname)
				print("%sScanned Host: %s" % (fill_prefix, service.scanned_hostname))
			print("%sPort - First Seen: %s" % (fill_prefix, service.first_seen))
			if service.has_tags:
				print("%sTags: %s" % (fill_prefix, ', '.join(service.tags)))
			print("%s* %s %s" % (fill_prefix, "Product", service.product.name))
			# v-- [BUG]: shows for every services, even if the product name isn´t 'Cobalt Strike Beacon'!
			#if service.product.is_cobaltstrike:
			#	print("%s* %s" % (fill_prefix, "Hosting 'Cobalt Strike Beacon'"))
			# // HTTP Module
			if service.is_web_service:
				http_module = Module_HTTP(service)
				# // try to figure out the http-server
				http_server = ""
				if http_module.header_exists("Server"):
					http_server = http_module.get_header("Server")
				elif http_module.header_exists("server"):
					http_server = http_module.get_header("server")
				elif 'ASP.NET' in service.data:
					http_server = "most likely 'IIS' (found 'ASP.NET' in headers)"
				if len(http_server) > 0:
					print("%s# 'Server' header: %s" % (fill_prefix, http_server))
				# // info from module data
				module_data = service.get_module_data()
				if module_data is not None:
					#if http_module.has_waf:
					#	print("%sWAF: %s" % (fill_prefix, http_module.waf))
					# ^-- [BUG] has_waf returns True for None, weird
					#
					# v-- this works
					http_waf = http_module.waf
					if http_waf:
						print("%sWAF: %s" % (fill_prefix, http_waf))
						
					print('%sWEB Info' % fill_prefix)
					if 'title' in module_data and module_data['title'] is not None:
						print("%s   Page Title: %s" % (fill_prefix, module_data['title']))
					if 'headers_hash' in module_data and module_data['headers_hash'] is not None:
						print("%s   Headers Hash: %s" % (fill_prefix, module_data['headers_hash']))
					if 'html_hash' in module_data and module_data['html_hash'] is not None:
						print("%s   HTML hash: %s" % (fill_prefix, module_data['html_hash']))
				if http_module.favicon_hash is not None:
					print("%s   favicon Hash: %s" % (fill_prefix, http_module.favicon_hash))
				if len(http_module.web_technologies) > 0:
					print("%s   Web Technologies: %s" % (fill_prefix, ', '.join(http_module.web_technologies)))
	
				# // output SSL Certificate information
				if http_module.is_ssl:
					if http_module.jarm is not None:
						print('%sjarm: %s' % (fill_prefix, http_module.jarm))
					if http_module.ja3s is not None:
						print('%sja3s: %s' % (fill_prefix, http_module.ja3s))
					if len(http_module.tls_versions) > 0:
						print('%sTLS-Versions: %s' % (fill_prefix, ', '.join(http_module.tls_versions)))

					if http_module.has_ssl_cert:
						print('%sSSL Certificate' % fill_prefix)
						ssl_cert = http_module.ssl_cert
						print('%s   Issued: %s, Expires: %s (Expired: %s)' % (fill_prefix, ssl_cert.issued, ssl_cert.expires, ssl_cert.expired))
						if ssl_cert.fingerprint is not None:
							print('%s   Fingerprint: %s' % (fill_prefix, ssl_cert.fingerprint))
						if ssl_cert.serial is not None:
							print('%s   Serial: %s' % (fill_prefix, ssl_cert.serial))
						if ssl_cert.subject_cn is not None and len(ssl_cert.subject_cn) > 0:
							print('%s   Subject.CN: %s' % (fill_prefix, ssl_cert.subject_cn))
						if ssl_cert.issuer_cn is not None and len(ssl_cert.issuer_cn) > 0:
							print('%s   Issuer.CN: %s' % (fill_prefix, ssl_cert.issuer_cn))

			if service.is_ssh_service:
				ssh_module = Module_SSH(service)
				module_data = service.get_module_data()
				print('%sSSH Info' % fill_prefix)
				if ssh_module.type is not None:
					print('%s   Type: %s' % (fill_prefix, ssh_module.type))
				if ssh_module.fingerprint is not None:
					print('%s   Fingerprint: %s' % (fill_prefix, ssh_module.fingerprint))
				if ssh_module.hassh is not None:
					print('%s   Hash: %s' % (fill_prefix, ssh_module.hassh))
				

		if shodan.settings['Out_Service_Data']:
			if service.has_data:
				# clean up empty lines & prefix each line with '[*] '
				serv_data = ["[*] %s" % l for l in service.data.split('\n') if len(l) > 0 ]
				print('\n'.join(serv_data))
			
		if shodan.settings['Out_Service_Module']:
			if service.has_module_data:
				serv_data = json.dumps(service.get_module_data(), indent=4).split('\n')
				# clean up empty lines & prefix each line with '[*] '
				serv_data = ["[*] %s" % l for l in serv_data if len(l) > 0 ]
				print('\n'.join(serv_data))

		if shodan.settings['Out_Service_JSON']:
			serv_data = json.dumps(service._json, indent=4).split('\n')
			# clean up empty lines & prefix each line with '[*] '
			serv_data = ["[*] %s" % l for l in serv_data if len(l) > 0 ]
			print('\n'.join(serv_data))

		if shodan.settings['Out_Service_Data'] or shodan.settings['Out_Service_Module']:
			print("")

		show_json_path_as_field(shodan, service)

def filter_list_by_head_tail(shodan, data_list):
	head_arg_index = get_arg_index(sys.argv, "--head")
	tail_arg_index = get_arg_index(sys.argv, "--tail")

	filtered_list = data_list

	if head_arg_index is None and tail_arg_index is None:
		return filtered_list

	#if head_arg_index < tail_arg_index:
	if head_arg_index is not None and tail_arg_index is None:
		if shodan.settings['Out_Head_Service_Count'] <= len(filtered_list):
			filtered_list = filtered_list[0:shodan.settings['Out_Head_Service_Count']]
	elif head_arg_index is None and tail_arg_index is not None:
		if shodan.settings['Out_Tail_Service_Count'] <= len(filtered_list):
			filtered_list = filtered_list[len(filtered_list)-shodan.settings['Out_Tail_Service_Count']:]
	else:
		if head_arg_index < tail_arg_index:
			if shodan.settings['Out_Head_Service_Count'] <= len(filtered_list):
				filtered_list = filtered_list[0:shodan.settings['Out_Head_Service_Count']]
			if shodan.settings['Out_Tail_Service_Count'] <= len(filtered_list):
				filtered_list = filtered_list[len(filtered_list)-shodan.settings['Out_Tail_Service_Count']:]
		else:
			if shodan.settings['Out_Tail_Service_Count'] <= len(filtered_list):
				filtered_list = filtered_list[len(filtered_list)-shodan.settings['Out_Tail_Service_Count']:]
			if shodan.settings['Out_Head_Service_Count'] <= len(filtered_list):
				filtered_list = filtered_list[0:shodan.settings['Out_Head_Service_Count']]

	return filtered_list

def list_cache(shodan, target=None):
	headers = "Target\t\tShodan Last Update\tCache Date\t\tCached Since"
	#if shodan.settings['Verbose_Mode']:
	if not shodan.settings['Out_Host_Only']:
		headers = "%s\t\t\t\t\t%s" % (headers, "Info")
	headers = "%s\n%s\t\t%s\t%s\t\t%s" % (headers, ("-"*len("Target")), ("-"*len("Shodan Last Update")), ("-"*len("Cache Date")), ("-"*len("Cached Since")))
	#if shodan.settings['Verbose_Mode']:
	if not shodan.settings['Out_Host_Only']:
		headers = "%s\t\t\t\t\t%s" % (headers, ("-"*len("Info")))

	if shodan.settings['Flush_Cache']:
		print("[*] Flushing cache before listing...")

	if target is not None:
		print(headers)
		#if target.isnumeric():
		if shodan._target_is_cache_index(target):
			target = shodan._get_target_by_cache_index(target)
			cache_file = shodan._get_out_path(shodan._target_as_out_file(target))
		else:
			cache_file = shodan._get_out_path(shodan._target_as_out_file(target))
		if not os.path.isfile(cache_file):
			return

		out_data = "%s" % target

		# // re-cache before stats out
		if shodan.settings['Flush_Cache']:
			shodan.cache_host_ip(target, shodan.settings['Include_History'])

		host = Shodan_Host(shodan.settings, shodan.get_cache_by_file(cache_file), False)
		last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, last_update)
		c_time = os.path.getctime(cache_file)
		cached_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, cached_date)

		end_date = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')
		cache_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f')
		cached_delta = relativedelta(end_date, cache_date)
		cache_delta = relativedelta(end_date, cache_date)
		out_data = "%s\t" % out_data
		out_data = "%s%s years" % (out_data, cached_delta.years)
		out_data = "%s, %s months" % (out_data, cached_delta.months)
		out_data = "%s, %s days" % (out_data, cached_delta.days)
		out_data = "%s, %sh, %s min" % (out_data, cached_delta.hours, cached_delta.minutes)
		if cached_delta.minutes == 0:
			out_data = "%s, %s sec" % (out_data, cached_delta.seconds)
		else:
			out_data = "%s\t" % out_data

		if not shodan.settings['Out_Host_Only']:
			if shodan.settings['Verbose_Mode'] and len(host.hostnames) > 0:
				out_data = "%s\thostnames: %s / " % (out_data, ', '.join(host.hostnames))
			else:
				out_data = "%s\t" % (out_data)
			host_ports = ", ".join([str(int) for int in host.host_ports]) # convert int to str
			out_data = "%sPorts: %s" % (out_data, host_ports)
			
		print(out_data)
		return
	
	# prefix each header with "cache index"
	header_data = ["#\t%s" % l for l in headers.split('\n') if len(l) > 0 ]
	header_data[1] = "-%s" % header_data[1][1:]
	headers = '\n'.join(header_data)
	print(headers)
	dir_list = os.listdir(shodan.settings['Cache_Dir'])
	cache_index = -1
	out_cache_list = []
	for file in dir_list:
		cache_index += 1
		if not file.startswith("host.") or not file.endswith(".json"):
			continue
		target = shodan._out_file_as_target(file)
		out_data = "%s\t%s" % (cache_index, target)

		# // re-cache before stats out
		if shodan.settings['Flush_Cache']:
			shodan.cache_host_ip(target, shodan.settings['Include_History'])

		cache_file = shodan._get_out_path(file)
		host = Shodan_Host(shodan.settings, shodan.get_cache_by_file(cache_file), False)
		last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, last_update)
		c_time = os.path.getctime(cache_file)
		cached_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, cached_date)

		end_date = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')
		cache_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f')
		cached_delta = relativedelta(end_date, cache_date)
		cache_delta = relativedelta(end_date, cache_date)
		out_data = "%s\t" % out_data
		out_data = "%s%s years" % (out_data, cached_delta.years)
		out_data = "%s, %s months" % (out_data, cached_delta.months)
		out_data = "%s, %s days" % (out_data, cached_delta.days)
		out_data = "%s, %sh, %s min" % (out_data, cached_delta.hours, cached_delta.minutes)
		if cached_delta.minutes == 0:
			out_data = "%s, %s sec" % (out_data, cached_delta.seconds)
		else:
			out_data = "%s\t" % out_data

		if not shodan.settings['Out_Host_Only']:
			if shodan.settings['Verbose_Mode'] and len(host.hostnames) > 0:
				out_data = "%s\thostnames: %s / " % (out_data, ', '.join(host.hostnames))
			else:
				out_data = "%s\t" % (out_data)
			host_ports = ", ".join([str(int) for int in host.host_ports]) # convert int to str
			out_data = "%sPorts: %s" % (out_data, host_ports)
			
		#print(out_data)
		out_cache_list.append(out_data)
	out_cache_list = filter_list_by_head_tail(shodan, out_cache_list)
	for out_data in out_cache_list:
		print(out_data)
def cache_target_list(shodan, target_file):
	print("[!] 'cache_target_list' function deprecated!")
	return
	if not os.path.isfile(target_file):
		return
	with open(target_file) as f:
		for line in f:
			target = line.strip()
			print(target)

def out_shodan_api_info(shodan):
	api_info = shodan.api.info()
	if shodan.api.has_error:
		print("[!] shodan api error '%s'" % shodan.api.error_msg)
		shodan.api._reset_error_msg()
		return
	print("Shodan API Info\n%s" % (("-"*len("Shodan API Info"))))
	print("Plan: %s\n" % (api_info['plan']))
	
	scan_credits = int(api_info['scan_credits'])
	limits_scan_credits = int(api_info['usage_limits']['scan_credits'])
	query_credits = int(api_info['query_credits'])
	limits_query_credits = int(api_info['usage_limits']['query_credits'])
	limits_monitored_ips = int(api_info['usage_limits']['monitored_ips'])
	unlocked_left = int(api_info['unlocked_left'])
	out_data = "* Credit Limits (left)"
	out_data = "%s\nScan: %s/%s" % (out_data, scan_credits, limits_scan_credits)
	out_data = "%s\nQuery: %s/%s" % (out_data, query_credits, limits_query_credits)
	out_data = "%s\nMonitored IPs: /%s" % (out_data, limits_monitored_ips)
	out_data = "%s\nUnlocked left: %s/?" % (out_data, unlocked_left)
	monitored_ips = api_info['monitored_ips']
	if monitored_ips is not None or monitored_ips is None:
		out_data = "%s\n\n* Monitored IPs\n%s" % (out_data, monitored_ips)
	
	print(out_data)

	if shodan.settings['Verbose_Mode']:
		print("\n%s" % json.dumps(api_info, indent=4))
def out_shodan_account_profile(shodan):
	#profile_data = shodan.api._api._request('/account/profile', {})
	#print(profile_data)
	#print("\n%s" % json.dumps(profile_data, indent=4))

	profile_data = shodan.api.account_profile
	if shodan.api.has_error:
		print("[!] shodan api error '%s'" % shodan.api.error_msg)
		shodan.api._reset_error_msg()
		return
	#print(profile_data)
	#print("\n%s" % json.dumps(profile_data, indent=4))
	#{'member': True, 'credits': 20, 'display_name': None, 'created': '2019-03-05T21:54:48.445000'}
	out_data = "Shodan Account Profile\n%s" % (("-"*len("Shodan Account Profile")))
	out_data = "%s\nMember: %s" % (out_data, profile_data['member'])
	out_data = "%s\nDisplay Name: %s" % (out_data, profile_data['display_name'])
	create_date = DateHelper.format_date(profile_data['created'], DateHelper.DATETIME_FORMAT_STANDARD)
	out_data = "%s\nCreated: %s" % (out_data, create_date)
	out_data = "%s\nCredits: %s" % (out_data, int(profile_data['credits']))
	

	print(out_data)

	if shodan.settings['Verbose_Mode']:
		print("\n%s" % json.dumps(profile_data, indent=4))
	
def host_to_ip(hostname):
	host_ip = None
	try:
		host_ip = socket.gethostbyname(hostname)
	except Exception as e:
		#self._error_msg = e
		pass
	return host_ip
def ip_to_host(ip):
	ip_host = None
	try:
		ip_host = socket.gethostbyaddr(ip)
		ip_host = ip_host[0]
	except Exception as e:
		#self._error_msg = e
		pass
	return ip_host
def main(args):
	#host = "119.45.94.71"

	shodan = ShodanCli(args)
	if shodan.settings['Target'] is not None:
		# // resolve host/domain to ip address
		#if not shodan._target_is_ip_address(args.target) and not shodan._target_is_cache_index(args.target):
		if shodan._target_is_domain_host(shodan.settings['Target']):
			"""
			data = shodan.api.domain_info(args.target)
			if shodan.api.has_error:
				print("[!] shodan api error '%s'" % shodan.api.error_msg)
				shodan.api._reset_error_msg()
				return
			print(data['domain'])
			for sub_item in data['data']:
				if len(sub_item['subdomain']) > 0 and ("%s.%s" % (sub_item['subdomain'], data['domain'])) == args.target:
					print("%s = %s" % (args.target, sub_item['value']))
					break
			if shodan.settings['Verbose_Mode']:
				print(json.dumps(data, indent=4))
			"""
			# // using the domain_info api costs 1 credit by query
			# // lets use "free" resolve solution instead
			host_ip = host_to_ip(shodan.settings['Target'])
			if host_ip is not None:
				print("[*] Target '%s' resolves to IP Address '%s', switching target to IP Address" % (shodan.settings['Target'], host_ip))
				shodan.settings['Target'] = host_ip
				cache_file = shodan._get_out_path(shodan._target_as_out_file(shodan.settings['Target']))
				shodan.settings['Cache_File'] = cache_file
			else:
				print("[!] Target '%s' failed to resolve to IP Address, skipping target" % shodan.settings['Target'])
				return

		# // set target based on cache index
		elif shodan._target_is_cache_index(shodan.settings['Target']):
			cached_target = shodan._get_target_by_cache_index(shodan.settings['Target'])
			if cached_target is None:
				print("[!] Failed to get target by cache index '%s', skipping target" % shodan.settings['Target'])
				return
			shodan.settings['Target'] = cached_target
			cache_file = shodan._get_out_path(shodan._target_as_out_file(shodan.settings['Target']))
			shodan.settings['Cache_File'] = cache_file
			#_set_cache_file_by_target


	if args.remove_target_from_cache:
		if shodan._target_is_cached(shodan.settings['Target']):
			cache_file = shodan._get_out_path(shodan._target_as_out_file(shodan.settings['Target']))
			os.remove(cache_file)
			print("[*] Removed target '%s' from cache" % shodan.settings['Target'])
			return

	if args.out_api_info:
		out_shodan_api_info(shodan)
		return
	if args.out_account_profile:
		out_shodan_account_profile(shodan)
		return

	if args.list_cache:
		if shodan.settings['Target'] is not None:
			list_cache(shodan, shodan.settings['Target'])
		else:
			list_cache(shodan)
		return

	if args.flush_cache:
		# // TODO: flush based on cache age
		if shodan.settings['Target'] is not None:
			file = shodan._target_as_out_file(shodan.settings['Target'])
			cache_file = shodan._get_out_path(file)
			if os.path.isfile(cache_file):
				print("[*] Flushing cache for target '%s'..." % shodan.settings['Target'])
				os.remove(cache_file)
		else:
			dir_list = os.listdir(shodan.settings['Cache_Dir'])
			for file in dir_list:
				cache_file = shodan._get_out_path(file)
				os.remove(cache_file)

	if shodan.settings['Target'] is None:
		print("shodan-cli.py: error: the following arguments are required: -t")
		return

	if not shodan.api.is_available:
		if shodan.api.has_error:
			print("[!] shodan api error '%s'" % shodan.api.error_msg)
			shodan.api._reset_error_msg()
		print("Shodan API not available, please run 'shodan init <api-key>'")
		return

	# // ADD SUPPORT FOR TARGET FILE
	if os.path.isfile(shodan.settings['Target']):
		cache_target_list(shodan, shodan.settings['Target'])
		return

	if not shodan.cache_exists:
		print("[*] Retrieving information for target '%s'..." % shodan.settings['Target'])
		shodan.cache_host()
	if shodan.get_cache() is None:
		print("[!] No information available for target '%s'" % shodan.settings['Target'])
		return

	out_shodan(shodan)

def testing(args):
	"""
	#print(DateHelper.now())
	#dh = DateHelper(DateHelper.now())
	now_date = DateHelper.now()
	print("now_date(type: %s): %s" % (type(now_date).__name__, now_date))

	dh = DateHelper(DateHelper.now())
	print("dh.date: %s" % dh.date)
	print("dh - year-month-day: %s-%s-%s" % (dh.year, dh.month_digits, dh.day_digits))
	print("dh - date: %s %s %s %s (%s)" % (dh.year, dh.month_digits, dh.month, dh.day_digits, dh.weekday))
	dh_2 = DateHelper(DateHelper.remove_months_from(dh.date, 2))
	print("dh_2 - date: %s %s %s %s (%s)" % (dh_2.year, dh_2.month_digits, dh_2.month, dh_2.day_digits, dh_2.weekday))
	#now_date = dh.string_to_date(DateHelper.now())
	print("")
	print("now: %s\n" % now_date)
	print("to_year(%s): %s" % (dh.as_string(), DateHelper.to_year(dh.date)))

	print("year: %s" % dh.year)
	print("dh.date.year: %s" % dh.date.year)
	print("month: %s" % DateHelper.to_month(DateHelper.now()))
	print("month: %s" % dh.month)
	print("month_short: %s" % DateHelper.to_month_short(DateHelper.now()))
	print("month_short: %s" % dh.month_short)
	print("month_digits: %s" % DateHelper.to_month_digits(DateHelper.now()))
	print("month_digits: %s" % dh.month_digits)
	print("day_digits: %s" % dh.to_day_digits(DateHelper.now()))
	print("day_digits: %s" % dh.day_digits)
	
	print("now_date: %s" % now_date)
	print("year + 1: %s" % DateHelper.date_to_string(DateHelper.add_years_to_date(now_date, 1)))
	print("year - 1: %s" % DateHelper.date_to_string(DateHelper.remove_years_from_date(now_date, 1)))
	print("month + 1: %s" % DateHelper.date_to_string(DateHelper.add_months_to(now_date, 1)))
	print("month - 1: %s" % DateHelper.date_to_string(DateHelper.remove_months_from(now_date, 1)))
	print("day + 1: %s" % DateHelper.date_to_string(DateHelper.add_days_to(now_date, 1)))
	print("day - 1: %s" % DateHelper.date_to_string(DateHelper.remove_days_from(now_date, 1)))
	print("week + 1: %s" % DateHelper.date_to_string(DateHelper.add_weeks_to(now_date, 1)))
	print("week - 1: %s" % DateHelper.date_to_string(DateHelper.remove_weeks_from(now_date, 1)))
	print("hour + 1: %s" % DateHelper.date_to_string(DateHelper.add_hours_to(now_date, 1)))
	print("hour - 1: %s" % DateHelper.date_to_string(DateHelper.remove_hours_from(now_date, 1)))
	print("min + 1: %s" % DateHelper.date_to_string(DateHelper.add_minutes_to(now_date, 1)))
	print("min - 1: %s" % DateHelper.date_to_string(DateHelper.remove_minutes_from(now_date, 1)))
	print("sec + 1: %s" % DateHelper.date_to_string(DateHelper.add_seconds_to(now_date, 1)))
	print("sec - 1: %s" % DateHelper.date_to_string(DateHelper.remove_seconds_from(now_date, 1)))

	print("now_date.weekday: %s" % DateHelper.to_weekday(now_date))
	now_date_but_later = DateHelper.add_days_to(DateHelper.add_weeks_to(now_date, 1), 1)
	print("now_date_but_later.weekday: %s" % DateHelper.to_weekday(now_date_but_later))
	
	print("weekday: %s" % DateHelper.to_weekday(DateHelper.now()))
	print("weekday: %s" % dh.weekday)
	print("weekday_short: %s" % DateHelper.to_weekday_short(DateHelper.now()))
	print("weekday_short: %s" % dh.weekday_short)
	print("week_number: %s" % DateHelper.to_week_number(DateHelper.now()))
	print("week_number: %s" % dh.week_number)

	print("hour_digits: %s" % DateHelper.to_hour_digits(DateHelper.now()))
	print("hour_digits: %s" % dh.hour_digits)
	print("minute_digits: %s" % DateHelper.to_minute_digits(DateHelper.now()))
	print("minute_digits: %s" % dh.minute_digits)
	print("as_time: %s" % dh.as_time())
	print("date_to_time: %s" % dh.date_to_time(DateHelper.now()))
	print("date_no_time: %s" % dh.date_no_time(DateHelper.now()))
	print("is_weekday_sun: %s" % DateHelper.is_weekday_sun(DateHelper.now()))
	print("is_month_aug: %s" % DateHelper.is_month_aug(DateHelper.now()))
	"""

	if args.date_since is not None:
		# * type: ago
		#   1 week 1 day ago
		#   1 week 1 hour 5 sec ago
		#   2 year 1 month 1 week 1 day 2 hours 4 min 10 secs ago
		#   yesterday today now
		#   10 dec 10 monday
		#   2022-10-12
		#   10 monday # unsupported
		#   midnight 2 hours ago
		#
		# * type: explicit
		#   today, yesterday, monday (weekday), midnight, noon, tea (tea time)
		#   date: 2022-10-12
		#
		# * type: during
		#   2021 (year), dec (month), dec 2021 (combined month & year), 2022 jan (jan 01 - jan 31)
		#   note that for 'combined month & year' month can either be placed before or after the year.
		#
		# * type: last
		#   year, month,week, day, hour, min (60 sec)
		#   each can be prefixed with a number; ex. 2 years, 2 months, 3 weeks, 3 days, 3 hours, 20 mins, 30 sec
		#
		# * type: between
		#   dates: 2022-10-01 - 2022-10-30, 1 jan - 20 feb, 2022 (jan 01) - 2022 dec (31)
		#   time-frame: 12:20 - 14:40
		#
		print("START of RelativeDate ('--since')")
		date_string = args.date_since
		old_date = DateHelper(DateHelper.now())
		old_date.remove_years(2)
		rel_date = RelativeDate(old_date.date)
		print("RelativeDate(%s, %s)" % (rel_date.date, date_string))
		if rel_date.is_relative_date(date_string):
			if not rel_date.parse(date_string):
				print("RelativeDate(): parse() returned false")
			print("old_date: '%s'" % old_date.date)
			print("rel_date: '%s'" % rel_date.date)
		print("END of RelativeDate ('--since')\n")

		
		# // test pattern for date and time format
		test_pattern(args)
		# // test parsing unknown date format
		test_date_management(args)

	if args.time_range:
		print("START of RelativeDate ('--time')")
		time_range = args.time_range
		if type(time_range).__name__ == "list":
			time_range = ' '.join(time_range).replace('"', "")
		print("time_range '%s'" % time_range)
		date_now = DateHelper(DateHelper.now())
		print("date_now: %s" % date_now.date)
		rel_date = RelativeDate(date_now.date)
		print("RelativeDate(%s, %s)" % (rel_date.date, time_range))
		if rel_date.is_relative_date(time_range):
			if not rel_date.parse(time_range):
				print("RelativeDate(): parse() returned false")
			print("date_now: '%s'" % date_now.date)
			print("rel_date: '%s'" % rel_date.date)
		if rel_date._startswith_last(time_range):
			print("'%s' startswith 'last'" % time_range)
			if not rel_date.parse(time_range):
				print("[!] RelativeDate(): parse() returned false")
			print("date_now: '%s'" % date_now.date)
			print("rel_date: '%s'" % rel_date.date)
		print("END of RelativeDate ('--time')\n")

		#today_date = DateHelper("2022-02-01 00:00:00")
		today_date = DateHelper(DateHelper.now())
		print(today_date.days_in_month)
		print("time: %s" % today_date.time)
		print("minute: %s" % today_date.minute_digits)
		print("second: %s" % today_date.second)
		print("milisecond: %s" % today_date.milisecond)

def test_pattern(args):
	print("START of 'pattern'")
	pattern_date = "^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$"
	pattern_date_time = "^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}$"
	pattern_date_time_no_milisec = "^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}$"
	pattern_date_time_ISO_8061 = "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}-[0-9]{2}:[0-9]{2}$"
	pattern_date_time_ISO_8061_no_timezone = "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}$"
	pattern_date_time_z = "^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
	pattern_time_has_milisec = "[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}"
	pattern_has_time = "[0-9]{2}:[0-9]{2}:[0-9]{2}"

	string_date = "2022-08-23"
	string_date_time_no_milisec = "2022-08-23 02:08:10"
	string_date_time = "2022-08-23 02:08:10.912150"
	string_date_time_ISO_8061 = "2022-08-23T22:32:47.912150-10:00"
	string_date_time_ISO_8061_no_timezone = "2022-08-23T22:32:47.912150"
	string_date_time_z = "2022-08-23T15:02:27Z"

	if re.match(pattern_date, string_date):
		print("found date (no time) '%s'" % string_date)
	if re.match(pattern_date_time, string_date_time):
		print("found date (with time) '%s'" % string_date_time)
	if re.match(pattern_date_time_no_milisec, string_date_time_no_milisec):
		print("found date (time no milisec) '%s'" % string_date_time_no_milisec)
	if re.match(pattern_date_time_ISO_8061, string_date_time_ISO_8061):
		print("found date (time ISO 8061) '%s'" % string_date_time_ISO_8061)
	if re.match(pattern_date_time_ISO_8061_no_timezone, string_date_time_ISO_8061_no_timezone):
		print("found date (time ISO 8061, no_ timezone) '%s'" % string_date_time_ISO_8061_no_timezone)
	if re.match(pattern_date_time_z, string_date_time_z):
		print("found date (time Z) '%s'" % string_date_time_z)
	print("END of 'pattern'\n")

	print("[START] test for time and milisec")
	print("[testing-string] '%s'" % string_date_time_no_milisec)
	string_test_for_time = string_date_time_no_milisec
	#if re.match(".*%s.*" % pattern_has_time, string_test_for_time):
	if re.match(".*%s.*" % pattern_has_time, string_test_for_time):
		print("has time '%s'" % string_test_for_time)
	string_test_for_time = string_date_time
	if re.match(".*%s.*" % pattern_time_has_milisec, string_test_for_time):
		print("time has milisec '%s'" % string_test_for_time)
	print("[END] test for time and milisec\n")
def test_date_management(args):
	print("* Test - Format unknown date(s)")

	date_time_format = DateHelper.DATETIME_FORMAT_STANDARD # %Y-%m-%d %H:%M:%S
	date_list = []
	date_list.append(datetime.today())
	date_list.append("2009/48")
	date_list.append("Feb 17, 2009")
	date_list.append("Feb 17 2009")
	date_list.append("17 Feb 2009")
	date_list.append("17 february, 2009")
	date_list.append("Feb 2009")
	date_list.append("2009 Feb")
	date_list.append("12/18/10")
	date_list.append("2009/ 2/17")
	date_list.append("Feb 17")
	date_list.append("17 Feb")
	date_list.append("17022009")
	date_list.append("02172009")
	date_list.append("02-03-2009")
	date_list.append("03-02-2009")
	date_list.append("02-17-2009")
	date_list.append("17-02-2009")
	date_list.append("2009/17/02")
	date_list.append("2009/02/17")
	date_list.append("20090217")
	date_list.append("2022-08-23")
	date_list.append("2022-08-23 02:08:10")
	date_list.append("2022-08-23 02:08:10.912150")
	date_list.append("2022-08-23T22:32:47.912150-10:00")
	date_list.append("2022-08-23T22:32:47.912150")
	date_list.append("2022-08-23T15:02:27Z")
	date_list.append("2018-10-29 10:02:48 AM")
	date_list.append("2018-10-29 10:02:48 PM")
	date_list.append("2018-10-29 07:30:20 PM")
	date_list.append("12:00:00")
	date_list.append("12:00")
	date_list.append("2022-08-24T20:16:25.864+02:00")
	for date in date_list:
		print("(format '%s') %s <- %s" % (date_time_format, DateHelper.format_date(date, date_time_format), date))
	print("")

	date_time_format = DateHelper.DATETIME_FORMAT_MILISEC # %Y-%m-%d %H:%M:%S.%f
	date_list = []
	date_list.append("2022-08-23T22:32:47.912150-10:00")
	date_list.append("08/23/22 22:32:47.9")
	date_list.append("08/23/22 22:32:47")
	for date in date_list:
		print("(format '%s') %s <- %s" % (date_time_format, DateHelper.format_date(date, date_time_format), date))
	
	#DateHelper.DATETIME_FORMAT_STANDARD
	#datetime.today()
def get_arg_index(args: list, name: str):
	return next((i for i, v in enumerate(args) if v.startswith(name)), None)
if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Shodan Cli in python")

	parser.add_argument('--api-info', dest='out_api_info', action='store_true', help="Output API info and exit, use '-v' for verbose output")
	parser.add_argument('--account-profile', dest='out_account_profile', action='store_true', help="Output Shodan Account Profile info and exit, use '-v' for verbose output")
	#parser.add_argument('-t', dest='target', help='Host or IP address of the target to lookup, specify a file for multiple targets')
	parser.add_argument('-t', dest='target', help='Host or IP address (or cache index) of the target to lookup')
	parser.add_argument('-c', '--cache', dest='cache', action='store_true', help="Use cached data if exists or re-cache if '-O' is not specified.")
	parser.add_argument('-L', '--list-cache', dest='list_cache', action='store_true', help="List cached hosts and exit. Use '-F' to re-cache, use '-t' for specific target")
	parser.add_argument('--cache-dir', dest='cache_dir', metavar="<path>", default='shodan-data', help="define custom cache directory, default './shodan-data'")
	parser.add_argument('-H', '--history', dest='include_history', action='store_true', help="Include host history" +
		"\n\n")
	parser.add_argument('-mp', '--match-ports', metavar="port[,port,...]", dest='match_on_ports', help='Match on port, comma-separated list of ports')
	parser.add_argument('-ms', '--match-service', metavar="service[,service,...]", dest='match_on_modules', help='Match on service type, comma-separated list of services (ex. ssh,http,https)')
	parser.add_argument('-mi', '--match-shodan-id', metavar="id[,id,...]", dest='match_on_shodan_id', help="Match on shodan id, comma-separated list of IDs")
	parser.add_argument('-mH', '--match-hostname', metavar="host[,host,...]", dest='match_on_scanned_hostname', help='Match on hostname that was used to talk to the service, supports Unix shell-style wildcards. Comma-separated list of hosts')
	parser.add_argument('-mC', '--match-crawler', metavar="id[,id,...]", dest='match_on_crawler', help='Match on unique ID of the crawler, comma-separated list of crawler id')
	parser.add_argument('-mI', '--match-scan-id', metavar="id[,id,...]", dest='match_on_scan_id', help="Match on unique scan ID that identifies the request that launched the scan, comma-separated list of IDs")
	parser.add_argument('-fp', '--filter-port', metavar="port[,port,...]", dest='filter_out_ports', help="Filter out port, comma-separated list of ports")
	parser.add_argument('-fs', '--filter-service', metavar="service[,service,...]", dest='filter_out_modules', help='Filter out service type, comma-separated list of services (ex. ssh,http,https)')
	parser.add_argument('-fH', '--filter-hostname', metavar="host[,host,...]", dest='filter_out_scanned_hostname', help='Filter out hostname that was used to talk to the service, supports Unix shell-style wildcards. Comma-separated list of hosts')
	parser.add_argument('-mc', '--match-json', dest='match_on_custom_conditions', metavar="<condition>", help="Match on json condition; syntax '<json-path>:<condition>', supports comma-separated list" +
		"\n" +
		"supported conditions:\n" +
		"- match on 'json path': exists, not-exists\n" +
		"- match on 'value': equals, not-equals, contains (has), not-contains, has-value, no-value, not-null\n" +
		"- match on 'type': type=<type>, not-type=<type>\n" +
		"- match on 'length': len=<length>, not-len=<length>, min-len=<length>, max-len=<length>\n" +
		"\n")
	parser.add_argument('--sort-date', dest='out_sort_by_scan_date', action='store_true', help="Output services by scan date")
	parser.add_argument('--head', metavar="num", dest='out_head_service_count', type=int, help="output first number of services")
	parser.add_argument('--tail', metavar="num", dest='out_tail_service_count', type=int, help="output last number of services")
	parser.add_argument('-d', '--service-data', dest='out_service_data', action='store_true', help="Output service details")
	parser.add_argument('-m', '--service-module', dest='out_service_module', action='store_true', help="Output service module data")
	parser.add_argument('--host-json', dest='out_host_json', action='store_true', help="Output host json")
	parser.add_argument('-sj', '--service-json', dest='out_service_json', action='store_true', help="Output service json" +
		"\n\n")
	parser.add_argument('--time', dest='time_range', metavar="<datetime range>", type=str, nargs="*", help="List cached targets matching range")
	parser.add_argument('--since', dest='date_since', metavar="<date-from>", help="List cached targets since (before) 'date-from'")
	parser.add_argument('--after', dest='date_after', metavar="<after-date>", help="List cached targets after the given date, see 'date-format'")
	parser.add_argument('--until', dest='date_until', metavar="<date-to>", help="List cached targets until 'date-to', from now and up to date")
	parser.add_argument('--before', dest='date_before', metavar="<before-date>", help="List cached targets before 'date-format'" +
		"\n\n" +
		"supported date-formats:\n" +
		"- <year>-<month>-<day> / YYYY-DD-MM, ex 2021-03-20\n" +
		"- <number>.<pronom>.ago, ex 2.days.ago, 1.day.ago\n" +
		"- Apr 1 2021 / 2 weeks ago / 2.weeks.ago\n" +
		"number of Y(ear)(s), M(onth)(s), D(ay)(s), h(our)(s), m/min(s),minute(s), s/sec(s)/second(s)")
	parser.add_argument('-F', '--flush-cache', dest='flush_cache', action='store_true', help="Flush cache from history, use '-t' to re-cache target data")
	parser.add_argument('--rm', dest='remove_target_from_cache', action='store_true', help='Removes target from the cache')
	parser.add_argument('--host-only', dest='out_host_only', action='store_true', help="Only output host information, skip port/service information" +
	"\n\n")
	parser.add_argument('-cf', '--custom-field', dest='out_custom_fields', metavar="<condition>", help="Output field based on condition, see '-mc' for syntax")
	parser.add_argument('-n', '--no-dns', dest='no_dns_lookup', action='store_true', help="Never do DNS resolution/Always resolve")
	parser.add_argument('-v', '--verbose', dest='verbose_mode', action='store_true', help="Enabled verbose mode")
	parser.add_argument('--debug', dest='debug_mode', action='store_true', help="Enabled debug mode")

	args = parser.parse_args()
	main(args)
	testing(args)
