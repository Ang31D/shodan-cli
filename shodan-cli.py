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
from match_helper import Condition, Compare
import base64


def json_prettify(json_data):
	json_type = type(json_data).__name__
	if "dict" == json_type:
		return json.dumps(json_data, indent=4)
	if "str" == json_type:
		return json.dumps(json.loads(json_data), indent=4)
	return json_data

#data = json.loads('{"foo":1, "bar": 2}', object_pairs_hook=OrderedDict)
def json_minify(json_data):
	json_type = type(json_data).__name__
	if "dict" == json_type:
		return json.dumps(json_data)
	if "str" == json_type:
		return json.dumps(json.loads(json_data))
	return json_data
def json_minify_sorted(json_data):
	json_type = type(json_data).__name__
	if "dict" == json_type:
		#return json.dumps(json_data)
		return json.dumps(json_data, sort_keys=True)
	if "str" == json_type:
		return json.dumps(json.loads(json_data, object_pairs_hook=OrderedDict), sort_keys=True)
	return json_data

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
		self.settings['Out_No_Hostname'] = args.out_no_hostname
		self.settings['Out_No_Vulns'] = args.out_no_vulns
		self.settings['Out_No_CacheTime'] = args.out_no_cache_time

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
		self.settings['Out_Custom_Fields_AS_CSV'] = None
		self.settings['Out_Custom_Fields_AS_JSON'] = args.out_custom_fields_as_json
		self.settings['Out_Custom_Fields_AS_Base64'] = args.out_custom_fields_as_base64
		

		self.settings['Match_On_Ports'] = []
		self.settings['Match_On_Modules'] = []
		self.settings['Match_On_ShodanID'] = []
		self.settings['Match_On_Scanned_Hostname'] = []
		self.settings['Match_On_Custom_Conditions'] = []
		self.settings['Match_On_Multi_Custom_Conditions'] = []
		self.settings['Match_On_Named_Custom_Condition_File'] = None
		self.settings['Match_On_Named_Custom_Conditions'] = []
		self.settings['Filter_Out_Non_Matched_Named_Custom_Conditions'] = False
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
			for multi_conditions in args.match_on_custom_conditions:
				self.settings['Match_On_Custom_Conditions'].append(multi_conditions[0].split(','))
				for multi_condition in multi_conditions:
					self.settings['Match_On_Multi_Custom_Conditions'].append(multi_condition)
		if args.match_on_named_custom_condition_file is not None:
			self.settings['Match_On_Named_Custom_Condition_File'] = args.match_on_named_custom_condition_file
			#self.settings['Match_On_Named_Custom_Conditions'] = get_named_multi_custom_conditions_from_file(args.match_on_named_custom_condition_file)
			self.settings['Match_On_Named_Custom_Conditions'] = get_conditional_tags_from_file(args.match_on_named_custom_condition_file)
			self.settings['Filter_Out_Non_Matched_Named_Custom_Conditions'] = args.filter_out_non_matched_named_custom_conditions
		if args.out_custom_fields is not None:
			for condition in args.out_custom_fields.split(','):
				self.settings['Out_Custom_Fields'].append(condition.strip())
		if args.out_custom_fields_as_csv is not None:
			self.settings['Out_Custom_Fields_AS_CSV'] = args.out_custom_fields_as_csv
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
			#return '.'.join(file.split('.')[1:5])
			target = '.'.join(file.split('.')[1:])
			target = '.'.join(target.split('.')[:-1])
			return target
			return '.'.join(file.split('.')[1:-1])
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
		if '.' in target and not self._target_is_ip_address(target) and "," not in target:
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
	def _target_is_range(self, target):
		if target is not None:
			if self._target_is_cache_index(target):
				return False
			if self._target_is_domain_host(target):
				return False
			if ("-" in target or "," in target):
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
		self.country = "%s - %s" % (self.country_code, self.country_name)
		self.city = '' if 'city' not in self._json else self._json['city']
		self.longitude = '' if 'longitude' not in self._json else self._json['longitude']
		self.latitude = '' if 'latitude' not in self._json else self._json['latitude']
		self.geo = "%s, %s (long, lat)" % (self.longitude, self.latitude)

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
		self.hostnames = '' if 'hostnames' not in self._json else self._json['hostnames']
		self.domains = '' if 'domains' not in self._json else self._json['domains']
		self.location = Location(self._json)
		self.isp = self._json['isp']
		self.org = self._json['org']
		self.services = []
		self._init_services(include_history)

	def _init_services(self, include_history):
		service_ports = OrderedDict()
		
		# grop by port
		for port_json in self._json['data']:
			port = int(port_json['port'])
			if port not in service_ports:
				service_ports[port] = []
			service_ports[port].append(Port_Service(port_json))

		# default sort by timestamp for each grouped port
		for port in service_ports:
			service_ports[port] = sorted(service_ports[port], key=attrgetter('timestamp'))

		sorted_ports = sorted(service_ports)
		for port in sorted_ports:
			first_seen_date = datetime.strptime(service_ports[port][0].timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")

			if include_history:
				for service in service_ports[port]:
					service.first_seen = first_seen_date
					self.services.append(service)
			else:
				service_first_scan = service_ports[port][0]
				service_last_scan = service_ports[port][-1]
				first_seen_date = datetime.strptime(service_first_scan.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
				service_last_scan.first_seen = first_seen_date
				self.services.append(service_last_scan)


#		if include_history:
#			for port in sorted_ports:
#				first_seen_date = datetime.strptime(service_ports[port][0].timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
#				for service in service_ports[port]:
#					service.first_seen = first_seen_date
#					self.services.append(service)
#		else:
#			for port in sorted_ports:
#				service_first_scan = service_ports[port][0]
#				service_last_scan = service_ports[port][-1]
#				first_seen_date = datetime.strptime(service_first_scan.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
#				service_last_scan.first_seen = first_seen_date
#				self.services.append(service_last_scan)

		if self.settings['Out_Sort_By_Scan_Date']:
			self.services = sorted(self.services, key=attrgetter('timestamp'))

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
		ports = []
		if "ports" in self._json:
			ports = self._json["ports"]
		ports.sort()
		return ports
		
		
class Port_Service:
	def __init__(self, json_data):
		self._json = json_data
		self.port = int(self._json['port'])
		self.protocol = '?' if 'transport' not in self._json else self._json['transport']
		self.timestamp = '' if 'timestamp' not in self._json else self._json['timestamp']
		self.scan_date = ''
		if len(self.timestamp) > 0:
			#self.scan_date = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S.%f")
			self.scan_date = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d")
		self.product = Service_Product(self._json)
		self.first_seen = ''
		# // add parsed 'headers' to the 'http.headers' element
		if self.is_web_service and "http" in self._json:
			http_module = Module_HTTP(self)
			if http_module.has_headers:
				self._json["http"]["headers"] = http_module.headers

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
		#return None
		return 'null'
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
		if 'http' in self._json and 'favicon' in self._json['http'] and self._json['http']['favicon'] is not None and 'hash' in self._json['http']['favicon']:
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
				category_list = []
				skip_default_append = False
				for category in categories:
					if "dict" == type(category).__name__:
						result.append('%s (%s)' % (technology, json_minify(categories)))
						skip_default_append = True
				if skip_default_append:
					continue
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
		if module_name is not None and '-' in module_name:
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

def get_json_path(json_dict, path):
	json_data = json_dict
	if json_data is None:
		return False, None

	fields = path.split('.')
	# // override if '|' is used as path separator instead
	if "|" in path:
		fields = path.split('|')
	last_field_index = len(fields)-1

	for i in range(len(fields)):
		field = fields[i]
		if json_data is None:
			continue
		field_exists = field in json_data

		if not field_exists:
			if last_field_index-1 != i:
				return False, None
			if "list" == type(json_data).__name__:
				result_data = []
				for item in json_data:
					if field in item:
						remove_fields = []
						for other_field in item:
							if other_field != field:
								remove_fields.append(other_field)
						for other_field in remove_fields:
							item.pop(other_field)
						#result_data.append("{'%s': '%s'}" % (field, item[field]))
						result_data.append(item)
				if len(result_data) > 0:
					return True, json_prettify(result_data)
			return False, None
		
		json_data = json_data[field]
		field_type = type(json_data).__name__
		if last_field_index == i:
			return True, json_data
	return False, None

#show_json_path_as_field
def custom_field_csv_file(shodan):
	csv_file = None
	if shodan.settings['Out_Custom_Fields_AS_CSV'] is None:
		return csv_file
	if ":" not in shodan.settings['Out_Custom_Fields_AS_CSV']:
		return csv_file
	if len(shodan.settings['Out_Custom_Fields_AS_CSV'].split(":")) != 2:
		return csv_file

	fields_and_file = shodan.settings['Out_Custom_Fields_AS_CSV'].split(":")
	if len(fields_and_file[1].strip()) > 0:
		csv_file = fields_and_file[1].strip()
	return csv_file
def custom_fields_as_csv_headers(shodan):
	csv_headers = []
	#map_field_to_path = map_custom_fields_as_csv_headers(shodan)
	map_path_to_field = map_custom_fields_as_csv_headers(shodan)
	for custom in shodan.settings['Out_Custom_Fields']:
		path = set_default_json_path_condition(custom).split(':')[0].strip()
		if path in map_path_to_field:
			csv_headers.append(map_path_to_field[path])
		else:
			csv_headers.append(path)
	return ','.join(csv_headers)
def map_custom_fields_as_csv_headers(shodan):
	map_field_to_path = OrderedDict()
	map_path_to_field = OrderedDict()
	if shodan.settings['Out_Custom_Fields_AS_CSV'] is None:
		return map_field_to_path
	if ":" not in shodan.settings['Out_Custom_Fields_AS_CSV']:
		return map_field_to_path
	if len(shodan.settings['Out_Custom_Fields_AS_CSV'].split(":")) != 2:
		return map_field_to_path

	paths_as_fields = shodan.settings['Out_Custom_Fields_AS_CSV']
	# // no naming of paths defined, used path as header
	if len(paths_as_fields.split(":")[0].strip()) == 0:
		for custom in shodan.settings['Out_Custom_Fields']:
			path = set_default_json_path_condition(custom).split(':')[0].strip()
			if path not in map_field_to_path:
				map_field_to_path[path] = path
		return map_field_to_path

	path_as_field_list = paths_as_fields.split(":")[0].split(",")
	for path_as_field in path_as_field_list:
		json_path = path_as_field.strip()
		field_name = None
		if "=" in json_path:
			field_name = json_path.split("=")[1].strip()
			json_path = json_path.split("=")[0].strip()
		else:
			field_name = json_path

		if field_name not in map_field_to_path:
			map_field_to_path[field_name] = json_path
		if json_path not in map_path_to_field:
			map_path_to_field[json_path] = field_name

	#return map_field_to_path
	return map_path_to_field
def custom_fields_as_csv_format(shodan, service):
	csv_format = ""
	if len(shodan.settings['Out_Custom_Fields']) == 0:
		return csv_format
	
	for custom in shodan.settings['Out_Custom_Fields']:
		if len(csv_format) > 0:
			csv_format = "%s," % csv_format
		if not match_on_json_path_condition(service._json, custom, shodan.settings['Debug_Mode']):
			#csv_format = "%s," % csv_format
			continue
		
		path = set_default_json_path_condition(custom).split(':')[0].strip()
		path_exists, path_value = get_json_path(service._json, path)
		
		if path_exists:
			if "dict" == type(path_value).__name__:
				path_value = json_minify(path_value)
			if "list" == type(path_value).__name__:
				if len(path_value) > 0 and "str" == type(path_value[0]).__name__:
					path_value = ','.join(path_value)

			if "str" == type(path_value).__name__:
				if " " in path_value or "," in path_value:
					path_value = '"%s"' % path_value
			csv_format = "%s%s" % (csv_format, path_value)
		else:
			csv_format = "%s," % csv_format

	return csv_format

def show_json_path_as_field(shodan, service):
	if len(shodan.settings['Out_Custom_Fields']) == 0:
		return
	fill_prefix = "\t\t\t\t"
	# // experimental, translate (change) output field from path to custom name
	translate_path_as_out_field_name = OrderedDict()
	#translate_path_as_out_field_name["_shodan.options.hostname"] = "hostname"
	#translate_path_as_out_field_name["http.title"] = "Page Title"
	#translate_path_as_out_field_name["http.host"] = "Host header"
	#translate_path_as_out_field_name["hostnames"] = "hostname list"
	found_path = False
	
	out_data = ""
	for custom in shodan.settings['Out_Custom_Fields']:
		if not match_on_json_path_condition(service._json, custom, shodan.settings['Debug_Mode']):
			continue
		#
		path = set_default_json_path_condition(custom).split(':')[0].strip()
		path_exists, path_value = get_json_path(service._json, path)
		path_type = type(path_value).__name__
		if shodan.settings['Debug_Mode']:
			print("json-path - path: %s, exists: %s, type: %s" % (path_type, path_exists, path))
		#
		if path_exists:
			found_path = True
			if len(out_data) > 1:
				out_data = "%s\n" % out_data
			
			field_name = path
			if field_name in translate_path_as_out_field_name:
				field_name = translate_path_as_out_field_name[path]
			#
			if "dict" == path_type:
				path_value = json_minify(path_value)
				if shodan.settings['Out_Custom_Fields_AS_Base64']:
					field_name = "%s (base64)" % field_name
					try:
						path_value = path_value.encode("ascii")
						path_value = base64.b64encode(path_value)
						path_value = path_value.decode("ascii")
					except Exception as e:
						path_value = "<failed to encode '%s' as base64>" % field_name
			out_data = "%s%s     ** %s: %s" % (out_data, fill_prefix, field_name, path_value)
	if found_path:
		print(out_data)
def match_service_on_conditional_tag_conditions(shodan, service, conditional_tag):
	if len(conditional_tag.conditions) == 0:
		return True

	for condition in conditional_tag.conditions:
		_service_id = "?"
		if "_shodan" in service._json and "id" in service._json["_shodan"]:
			_service_id = service._json["_shodan"]["id"]
		if not match_on_json_path_condition(service._json, condition.as_string(), shodan.settings["Debug_Mode"]):
			if shodan.settings["Debug_Mode"]:
				print("[-] match_service_on_conditional_tag_conditions() : timestamp: %s, _shodan.id == '%s', port: %s, no match on condition_string '%s'" % (service._json["timestamp"], _service_id, service._json["port"], condition.as_string()))
			return False
	return True
def match_service_on_multi_custom_conditions(shodan, service, multi_custom_conditions):
	if len(multi_custom_conditions) == 0:
		return True
	
	for custom_condition in multi_custom_conditions:
		if shodan.settings["Debug_Mode"]:
			print("[*] match_service_on_multi_custom_conditions() condition '%s'" % custom_condition)
		#path_exists, path_value = get_json_path(service._json, set_default_json_path_condition(custom_condition).split(":")[0].strip())
		if not match_on_json_path_condition(service._json, custom_condition, shodan.settings['Debug_Mode']):
			if shodan.settings['Debug_Mode']:
				print("[-] tags_by_match_service_on_named_multi_custom_conditions() : _shodan.id == '%s', port: %s, no match on condition '%s'" % (service._json["_shodan"]["id"], service._json["port"], custom_condition))
			return False
		else:
			if shodan.settings['Debug_Mode']:
				print("[+] tags_by_match_service_on_named_multi_custom_conditions() : _shodan.id == '%s', port: %s, match on condition '%s'" % (service._json["_shodan"]["id"], service._json["port"], custom_condition))
	return True
def get_named_multi_custom_conditions_from_file(file):
	named_multi_custom_conditions = OrderedDict()
	if not os.path.isfile(file):
		return named_multi_custom_conditions

	with open(file, "r") as f:
		for line in f:
			rule_string = line.strip()
			if len(rule_string) == 0 or "#" == rule_string[0]:
				continue
			rule_name = rule_string.split(";")[0].strip()
			rule_conditions = rule_string.split(";")[1:][0].split(",")
			if rule_name not in named_multi_custom_conditions:
				named_multi_custom_conditions[rule_name] = rule_conditions

	return named_multi_custom_conditions
def get_conditional_tags_from_file(file):
	conditional_tags = OrderedDict()
	if not os.path.isfile(file):
		return conditional_tags

	with open(file, "r") as f:
		for line in f:
			tag_string = line.strip()
			conditional_tag = ConditionalTag(tag_string)
			conditional_tags[conditional_tag.name] = conditional_tag

	#for tag_name in conditional_tags:
	#	conditional_tag = conditional_tags[tag_name]
	#	for json_condition in conditional_tag.conditions:
	#		print("// is_enabled: '%s' - tag_name '%s' - (is_negate: %s-, is_case_sensitive: %s)\n\t - path: '%s', compare: '%s', match_on: '%s'" % (conditional_tag.is_enabled, tag_name, json_condition.is_negate, json_condition.is_case_sensitive, json_condition.path, json_condition.compare, json_condition.match_on))
	return conditional_tags
class ConditionalTag:
	def __init__(self, definition):
		self._definition = definition
		self._tag_name = ''
		self._is_enabled = True
		self._multi_conditions = []
		self._init()

	def _init(self):
		if self._definition.startswith("#"):
			self._is_enabled = False
		if ";" in self._definition:
			tag_name = self._definition.split(";")[0].strip()
			if tag_name.startswith("#"):
				tag_name = tag_name[1:].strip()
			if len(tag_name) > 0:
				self._tag_name = tag_name
		condition_definitions = self._definition.split(";")[1:]
		for multi_condition_definition in condition_definitions:
			for path_condition_definition in multi_condition_definition.split(","):
				self._multi_conditions.append(JsonCondition(path_condition_definition))

	@property
	def name(self):
		return self._tag_name
	@property
	def is_enabled(self):
		return self._is_enabled
	@property
	def conditions(self):
		return self._multi_conditions
	def as_string(self):
		definition_string = "%s;" % self._tag_name
		definition_string = ""
		is_first_iterate = True
		for condition_tag in self._multi_conditions:
			if not is_first_iterate:
				definition_string = "%s," % definition_string
			definition_string = "%s%s" % (definition_string, condition_tag.as_string())
			is_first_iterate = False
		return definition_string
class JsonCondition:
	def __init__(self, definition):
		self._definition = definition.strip()
		self._path = None
		self._compare = None
		self._match_on_value = None
		self._is_negate = False
		self._is_case_sensitive = False
		self._init()

	def _init(self):
		path_condition = set_default_json_path_condition(self._definition)
		if ':' not in path_condition or len(path_condition.split(':')) < 2:
			return
		self._path = path_condition.split(':')[0].strip()
		self._compare = ':'.join(path_condition.split(':')[1:]).strip()

		if "=" in self._compare:
			self._match_on_value = self._compare.split("=")[1]
			self._compare = self._compare.split("=")[0]
		
		self._is_negate = Condition.has_negation_operator(self._compare)
		self._compare = Condition.strip_negation_operator(self._compare)
		self._is_case_sensitive = Condition.is_case_sensitive(self._compare)
		self._compare = self._compare.lower()

	@property
	def path(self):
		return self._path
	@property
	def compare(self):
		return self._compare
	@property
	def match_on(self):
		return self._match_on_value
	@property
	def is_negate(self):
		return self._is_negate
	@property
	def is_case_sensitive(self):
		return self._is_case_sensitive

	def as_string(self):
		condition_as_string = "%s:%s" % (self.path, self.compare)
		if self.match_on is not None:
			condition_as_string = "%s=%s" % (condition_as_string, self.match_on)
		return condition_as_string

def tags_by_match_service_on_conditional_tag_conditions(shodan, service):
	tags = []
	if len(shodan.settings['Match_On_Named_Custom_Conditions']) == 0:
		return tags

	#if "_shodan" in service._json and "id" in service._json["_shodan"] and service._json["_shodan"]["id"] == "3b5a9345-805e-484e-be7f-3d88832d481c":
	#	print("tags_by_match_service_on_named_multi_custom_conditions() : _shodan.id == '%s'" % service._json["_shodan"]["id"])
	
	conditional_tags = shodan.settings['Match_On_Named_Custom_Conditions']
	for tag_name in conditional_tags:
		conditional_tag = conditional_tags[tag_name]
		if not conditional_tag._is_enabled or  len(conditional_tag.conditions) == 0:
			continue
		if shodan.settings["Debug_Mode"]:
			print("[*] tags_by_match_service_on_conditional_tag_conditions() : [checking tag] _shodan.id == '%s', port: %s, tag_name '%s', condition_string: '%s'" % (service._json["_shodan"]["id"], service._json["port"], tag_name, conditional_tag.as_string()))
		if match_service_on_conditional_tag_conditions(shodan, service, conditional_tag):
			if shodan.settings["Debug_Mode"]:
				print("[+] tags_by_match_service_on_conditional_tag_conditions() : _shodan.id == '%s', port: %s, match on tag '%s'" % (service._json["_shodan"]["id"], service._json["port"], tag_name))
			if tag_name not in tags:
				tags.append(tag_name)
		else:
			if shodan.settings["Debug_Mode"]:
				print("[-] tags_by_match_service_on_conditional_tag_conditions() : _shodan.id == '%s', port: %s, no match on tag '%s'" % (service._json["_shodan"]["id"], service._json["port"], tag_name))

	return tags
def tags_by_match_service_on_named_multi_custom_conditions(shodan, service):
	tags = []
	if len(shodan.settings['Match_On_Named_Custom_Conditions']) == 0:
		return tags

	#if "_shodan" in service._json and "id" in service._json["_shodan"] and service._json["_shodan"]["id"] == "3b5a9345-805e-484e-be7f-3d88832d481c":
	#	print("tags_by_match_service_on_named_multi_custom_conditions() : _shodan.id == '%s'" % service._json["_shodan"]["id"])
	
	named_multi_custom_conditions = shodan.settings['Match_On_Named_Custom_Conditions']
	for rule_name in named_multi_custom_conditions:
		rule_multi_custom_conditions = named_multi_custom_conditions[rule_name]
		if len(rule_multi_custom_conditions) == 0:
			continue
		if shodan.settings["Debug_Mode"]:
			print("[*] tags_by_match_service_on_named_multi_custom_conditions() : [checking rule] _shodan.id == '%s', port: %s, rule_name '%s', conditions: '%s'" % (service._json["_shodan"]["id"], service._json["port"], rule_name, rule_multi_custom_conditions))
		if match_service_on_multi_custom_conditions(shodan, service, rule_multi_custom_conditions):
			if shodan.settings["Debug_Mode"]:
				print("[+] tags_by_match_service_on_named_multi_custom_conditions() : _shodan.id == '%s', port: %s, match on rule '%s'" % (service._json["_shodan"]["id"], service._json["port"], rule_name))
			if rule_name not in tags:
				tags.append(rule_name)
		else:
			if shodan.settings["Debug_Mode"]:
				print("[-] tags_by_match_service_on_named_multi_custom_conditions() : _shodan.id == '%s', port: %s, no match on rule '%s'" % (service._json["_shodan"]["id"], service._json["port"], rule_name))

	return tags
def match_service_on_named_multi_custom_conditions(shodan, service, rule_name):
	if len(shodan.settings['Match_On_Named_Custom_Conditions']) == 0:
		return True
	
	if rule_name not in shodan.settings['Match_On_Named_Custom_Conditions']:
		return False

	multi_custom_conditions = shodan.settings['Match_On_Named_Custom_Conditions'][rule_name]
	if len(multi_custom_conditions) == 0:
		return False

	return match_service_on_multi_custom_conditions(shodan, service, multi_custom_conditions)
def match_service_on_any_named_multi_custom_conditions(shodan, service):
	if len(shodan.settings['Match_On_Named_Custom_Conditions']) == 0:
		return True

	conditional_tags = shodan.settings['Match_On_Named_Custom_Conditions']
	for tag_name in conditional_tags:
		conditional_tag = conditional_tags[tag_name]
		if match_service_on_conditional_tag_conditions(shodan, service, conditional_tag):
			return True

	return False
def match_service_on_andor_multi_custom_conditions(shodan, service):
	if len(shodan.settings['Match_On_Custom_Conditions']) == 0:
		return True

	negated_match_found = False
	for multi_custom_condition in shodan.settings['Match_On_Custom_Conditions']:
		if match_service_on_multi_custom_conditions(shodan, service, multi_custom_condition):
			return True

	return False
def match_service_on_custom_conditions(shodan, service):
	return match_service_on_andor_multi_custom_conditions(shodan, service)
	if len(shodan.settings['Match_On_Custom_Conditions']) == 0:
		return True

	for custom_condition in shodan.settings['Match_On_Custom_Conditions']:
		path_exists, path_value = get_json_path(service._json, set_default_json_path_condition(custom_condition).split(":")[0].strip())
		if not match_on_json_path_condition(service._json, custom_condition, shodan.settings['Debug_Mode']):
			return False
	return True
def set_default_json_path_condition(path_condition):
	path = None
	condition = None
	if ':' not in path_condition:
		if '=' in path_condition:
			if len(path_condition.split('=')) == 2:
				path = path_condition.split('=')[0].strip()
				condition_value = path_condition.split('=')[1].strip()
				condition = "%s=%s" % (Condition.EQUALS, condition_value)
		else:
			path = path_condition
			condition = Condition.EXISTS
	else:
		if len(path_condition.split(':')) == 2:
			if "not" == path_condition.split(':')[1].strip().lower() or "!" == path_condition.split(':')[1].strip():
				path = path_condition.split(':')[0].strip()
				condition = "not-%s" % Condition.EXISTS

	if path is not None and condition is not None:
		return "%s:%s" % (path, condition)
	return path_condition
def parse_json_path_condition(path_condition):
	path_condition = set_default_json_path_condition(path_condition)
	path = path_condition.split(':')[0].strip()
	field_condition = ':'.join(path_condition.split(':')[1:]).strip()
	condition_value = None
	condition = field_condition
	if "=" in condition:
		condition_value = condition.split("=")[1]
		condition = condition.split("=")[0]
	return path, condition, condition_value

def match_on_json_path_condition(json, path_condition, debug=False):
	path_condition = set_default_json_path_condition(path_condition)
	#if ':' not in path_condition or len(path_condition.split(':')) != 2:
	if ':' not in path_condition or len(path_condition.split(':')) < 2:
		if debug:
			print("[!] match_on_json_path_condition() : invalid path_condition format '%s'" % (path_condition))
		return False
	path, condition, condition_value = parse_json_path_condition(path_condition)
#	path = path_condition.split(':')[0].strip()
	field_condition = ':'.join(path_condition.split(':')[1:]).strip()
#	condition_value = None
#	condition = field_condition
#	if "=" in condition:
#		condition_value = condition.split("=")[1]
#		condition = condition.split("=")[0]
	
	
	if debug:
		print("[*] match_on_json_path_coidition() field_condition '%s'" % (field_condition))
	negated_match = Condition.has_negation_operator(condition)
	case_sensitive_match = Condition.is_case_sensitive(condition)
	condition = Condition.strip_negation_operator(condition)
	condition = condition.lower()

	path_exists, path_value = get_json_path(json, path)

	path_type = type(path_value).__name__
	if path_type == "NoneType" or path_value is None:
		path_type = "null"
	elif path_type == "dict":
		path_type = "json"

	if debug:
		print("[*] match_on_json_path_condition() condition path: '%s', condition: '%s', path.exists: %s, path_value.type: %s\n################\n%s\n################" % (path, field_condition, path_exists, path_type, path_value))

	if Condition.EXISTS == condition:
		if path_exists:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False

	if Condition.HAS_VALUE == condition:
		return Compare.has_value(path_value, negated_match)

	if Condition.IS_EMPTY == condition or Condition.NO_VALUE == condition:
		return Compare.is_empty(path_value, negated_match)

	if Condition.IS_NULL == condition or Condition.NULL == condition:
		return Compare.is_null(path_value, negated_match)
	if Condition.IS_TYPE == condition or Condition.TYPE == condition:
		return Compare.is_type(path_value, condition_value, negated_match)

	if Condition.EQUALS == condition or Condition.VALUE == condition or Condition.IS == condition:
		return Compare.equals(path_value, condition_value, case_sensitive_match, negated_match)

	if Condition.CONTAINS == condition:
		return Compare.contains(path_value, condition_value, negated_match)
	if Condition.HAS == condition:
		return Compare.has(path_value, condition_value, negated_match)

	if Condition.STARTS == condition or Condition.BEGINS == condition:
		return Compare.starts(path_value, condition_value, negated_match)

	if Condition.ENDS == condition:
		return Compare.ends(path_value, condition_value, negated_match)

	if Condition.LEN == condition:
		if path_exists and path_value is not None:
			return Compare.is_length(path_value, condition_value, negated_match)

	if Condition.MIN_LEN == condition:
		if path_exists and path_value is not None:
			return Compare.min_length(path_value, condition_value, negated_match)

	if Condition.MAX_LEN == condition:
		if path_exists and path_value is not None:
			return Compare.max_length(path_value, condition_value, negated_match)

	if Condition.NUM_GREATER_THEN == condition:
		if path_exists and path_value is not None:
			return Compare.num_is_greater_then(path_value, condition_value, negated_match)

	if Condition.NUM_GREATER_EQUAL_LTHEN == condition:
		if path_exists and path_value is not None:
			return Compare.num_is_greater_equal_then(path_value, condition_value, negated_match)

	if Condition.NUM_LESS_THEN == condition:
		if path_exists and path_value is not None:
			return Compare.num_is_less_then(path_value, condition_value, negated_match)

	if Condition.NUM_LESS_EQUAL_THEN == condition:
		if path_exists and path_value is not None:
			return Compare.num_is_less_equal_then(path_value, condition_value, negated_match)

	if Condition.NUM_EQUAL == condition:
		return Compare.num_is_equal(path_value, condition_value, negated_match)

	if Condition.REGEX == condition:
		if path_exists and path_value is not None:
			return Compare.match_on_regex(path_value, condition_value, negated_match)
	return False

	if debug:
		print("***************************************\n%s\n***************************************" % path_value)
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

	out_shodan_host_info(shodan, host)
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
			if len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
				#service_tags = tags_by_match_service_on_named_multi_custom_conditions(shodan, service)
				service_tags = tags_by_match_service_on_conditional_tag_conditions(shodan, service)
				if len(service_tags) == 0 and shodan.settings['Filter_Out_Non_Matched_Named_Custom_Conditions']:
					continue
			filtered_services.append(service)
		
	filtered_services = filter_list_by_head_tail(shodan, filtered_services)

	for service in filtered_services: 
		out_shodan_service_info(shodan, service)

	if len(shodan.settings['Out_Custom_Fields']) > 0:
		if shodan.settings['Out_Custom_Fields_AS_CSV'] is not None:
			out_service_custom_fields_as_csv(shodan, filtered_services)
		if shodan.settings['Out_Custom_Fields_AS_JSON']:
			out_service_json_by_custom_fields(shodan, filtered_services)

def out_service_json_by_custom_fields(shodan, services):
	custom_json = {"blob": []}

	path_blob = OrderedDict()
	for service in services:
		service_blob = {}
		for json_path in shodan.settings['Out_Custom_Fields']:
			path_exists, path_value = get_json_path(service._json, json_path)
			if json_path not in service_blob:
				service_blob[json_path] = None
			if path_exists:
				service_blob[json_path] = path_value
		
		custom_json["blob"].append(service_blob)

	#print(json_minify_sorted(custom_json))
	print(json_minify(custom_json))

def get_service_json_by_path(shodan, service, json_path):
	custom_json = []
	if not shodan.settings['Out_Custom_Fields_AS_JSON']:
		return custom_json

	for json_path in shodan.settings['Out_Custom_Fields']:
		path_exists, path_value = get_json_path(service._json, json_path)
		if path_exists:
			custom_json.append({json_path: path_value})

	return custom_json

def out_service_custom_fields_as_csv(shodan, services):
	out_custom_fields_as_csv_format = []
	for service in services:
		csv_format = custom_fields_as_csv_format(shodan, service)
		out_custom_fields_as_csv_format.append(csv_format)

	if len(out_custom_fields_as_csv_format) > 0:
		csv_file = custom_field_csv_file(shodan)
		# // write to file if specified
		if csv_file is not None:
			print("csv stored in file '%s'" % csv_file)
			with open(csv_file, "w") as f:
				f.write('%s\n' % custom_fields_as_csv_headers(shodan))
			with open(csv_file, "a") as f:
				f.write('\n'.join(out_custom_fields_as_csv_format))
				f.write('\n')
			for csv_format in out_custom_fields_as_csv_format:
				break
				print(csv_format)
		else:
			# // output if no file is specified
			print(custom_fields_as_csv_headers(shodan))
			for csv_line in out_custom_fields_as_csv_format:
				print(csv_line)

def out_shodan_host_info(shodan, host):
	print("* Host Overview\n %s" % ('-'*30))
	print("IP Address: %s" % host.ip)
	if host.has_os:
		print("OS: %s" % host.os)
	else:
		os_list = host.get_os_by_services()
		if len(os_list) > 0:
			print("OS: %s # based on services!" % ', '.join(os_list))
	if not shodan.settings["Out_No_Hostname"]:
		print("Hostnames: %s" % ', '.join(host.hostnames))
		print("Domains: %s" % ', '.join(host.domains))
	print("Ports: %s" % ", ".join([str(int) for int in host.host_ports])) # convert int to str
	print("Location: %s" % host.location.as_string())
	print("")
	print("ISP: %s" % host.isp)
	print("Organization: %s" % host.org)
	print("ASN: %s" % host.asn)
	print("")
	if host.has_vulns and not shodan.settings['Out_No_Vulns']:
		print("Vulns: %s" % ', '.join(host.vulns))
		print("")

	print("Total Service scans: %s" % len(host.services))

	if shodan.settings['Out_Host_JSON']:
		host_data = ["[*] %s" % l for l in host.json.split('\n') if len(l) > 0 ]
		print('\n'.join(host_data))

def out_shodan_service_info(shodan, service):
	service_tags = []
	# // skip service if filter out on tags
	if len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
		if shodan.settings["Debug_Mode"]:
			print("[*] out_shodan_service_info() : [fetching tags] _shodan.id == '%s', port: %s" % (service._json["_shodan"]["id"], service._json["port"]))
		#service_tags = tags_by_match_service_on_named_multi_custom_conditions(shodan, service)
		service_tags = tags_by_match_service_on_conditional_tag_conditions(shodan, service)
		if len(service_tags) == 0 and shodan.settings['Filter_Out_Non_Matched_Named_Custom_Conditions']:
			return

	# // output service overview (Scan-Date, Port, Service)
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

	# // output - Version / Info overview
	if shodan.settings['Verbose_Mode']:
		shodan_header = "%sShodan - ID: %s" % (fill_prefix, service.identifier)
		if len(service.crawler) > 0:
			shodan_header = "%s, Crawler: %s" % (shodan_header, service.crawler)
		if len(service.scan_id) > 0:
			shodan_header = "%s, Scan Id: %s" % (shodan_header, service.scan_id)
		print(shodan_header)
		if len(service.scanned_hostname) > 0:
			print("%sScanned Host: %s" % (fill_prefix, service.scanned_hostname))
		print("%sPort - First Seen: %s" % (fill_prefix, service.first_seen))
		if service.has_tags:
			print("%sTags: %s" % (fill_prefix, ', '.join(service.tags)))

	if len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
		for service_tag in service_tags:
			print("%s! %s" % (fill_prefix, service_tag))
		#for threat_name in shodan.settings['Match_On_Named_Custom_Conditions']:
		#	if match_service_on_named_multi_custom_conditions(shodan, service, threat_name):
		#		print("%s! %s" % (fill_prefix, threat_name))

	if shodan.settings['Verbose_Mode']:
		print("%s* %s %s" % (fill_prefix, "Product", service.product.name))
		# v-- [BUG]: shows for every services, even if the product name isn??t 'Cobalt Strike Beacon'!
		#if service.product.is_cobaltstrike:
		#	print("%s* %s" % (fill_prefix, "Hosting 'Cobalt Strike Beacon'"))
		out_shodan_service_details(shodan, service, fill_prefix)

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
		service_json = service._json
		if shodan.settings['Out_No_Vulns'] and "vulns" in service_json:
			service_json.pop("vulns")
		serv_data = json.dumps(service_json, indent=4).split('\n')
		# clean up empty lines & prefix each line with '[*] '
		serv_data = ["[*] %s" % l for l in serv_data if len(l) > 0 ]
		print('\n'.join(serv_data))

	if shodan.settings['Out_Service_Data'] or shodan.settings['Out_Service_Module']:
		print("")

	if len(shodan.settings['Out_Custom_Fields']) > 0:
		if shodan.settings['Out_Custom_Fields_AS_CSV'] is None:
			show_json_path_as_field(shodan, service)
		else:
			csv_format = custom_fields_as_csv_format(shodan, service)
			print("%s     ** %s" % (fill_prefix[0:-1], csv_format))

def out_shodan_service_details(shodan, service, fill_prefix):
	# // HTTP Module
	if service.is_web_service:
		out_shodan_http_service(shodan, service, fill_prefix)
	elif service.is_ssh_service:
		out_shodan_ssh_service(shodan, service, fill_prefix)
def out_shodan_http_service(shodan, service, fill_prefix):
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
def out_shodan_ssh_service(shodan, service, fill_prefix):
	ssh_module = Module_SSH(service)

	module_data = service.get_module_data()
	print('%sSSH Info' % fill_prefix)
	if ssh_module.type is not None:
		print('%s   Type: %s' % (fill_prefix, ssh_module.type))
	if ssh_module.fingerprint is not None:
		print('%s   Fingerprint: %s' % (fill_prefix, ssh_module.fingerprint))
	if ssh_module.hassh is not None:
		print('%s   Hash: %s' % (fill_prefix, ssh_module.hassh))

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

class Shodan_Cache:
	TYPE_HOST = "host"       # class Shodan_Host
	TYPE_SERVICE = "service" # class Port_Service

	def __init__(self, shodan):
		self._shodan = shodan
		self.settings = self._shodan.settings
		self._cache_dir = self._shodan.settings['Cache_Dir']
		self._target = None

	@property
	def location(self):
		return self._cache_dir

	def render_output(self):
		pass

	def list_cache(self):
		dir_list = os.listdir(self.location)
		cache_index = -1
		out_cache_list = []
		for file in dir_list:
			cache_index += 1
			if not file.startswith("host.") or not file.endswith(".json"):
				continue
			target = self._host_cache_filename_as_target(file)

	def _is_host_cache_filename(self, file):
		if file.startswith("host.") and file.endswith(".json"):
			return True
		return False
	def _target_as_out_file(self, target):
		return "host.%s.json" % target
	def _host_cache_filename_as_target(self, file):
		if self._is_host_cache_filename(file):
			# strip of '^host.' and '.json$'
			target = '.'.join(file.split('.')[1:])
			target = '.'.join(target.split('.')[:-1])
			return target
		return ''
	def _get_out_path(self, file):
		return os.path.join(self.location, file)

	def _get_json_from_cached_file(self, file):
		if os.path.isfile(file):
			with open(file, 'r') as f:
				return json.load(f)
		return None
	def _get_target_cache_path(self, target):
		return self._get_out_path(self._target_as_out_file(target))
	def _target_is_cached(self, target):
		cache_file = self._get_target_cache_path(target)
		if os.path.isfile(cache_file):
			return True
		return False

	def _get_target_by_cache_index(self, cache_index):
		pass

		target = None
		if not self._shodan._target_is_cache_index(cache_index):
			return target

		dir_list = os.listdir(self.location)
		if int(cache_index) < 0 or int(cache_index) >= len(dir_list):
			return target

		cache_filename = dir_list[int(cache_index)]
		#target = self._out_file_as_target(cache_filename)
		target = self._host_cache_filename_as_target(cache_filename)
		return target

	def get_host_from_file(self, file):
		if not self._is_host_cache_filename(file):
			return None

		target = self._host_cache_filename_as_target(file)
		if len(target) == 0:
			return None
		return self.get_host_by_target(target)
	def get_host_by_target(self, target):
		# // re-cache host before fetching data
		if self.settings['Flush_Cache']:
			self._shodan.cache_host_ip(target, self.settings['Include_History'])

		if not self._target_is_cached(target):
			return None

		cache_file = self._get_target_cache_path(target)
		host_json = self._get_json_from_cached_file(cache_file)
		host = Shodan_Host(self.settings, host_json, self.settings['Include_History'])
		return host

def list_cache(shodan, target=None):
	shodan_cache = Shodan_Cache(shodan)

	#headers = "Target\t\tShodan Last Update\tCache Date\t\tCached Since"
	headers = "Target\t\tShodan Last Update"
	if not shodan.settings['Out_No_CacheTime']:
		headers = "%s\tCache Date\t\tCached Since" % headers
		headers = "%s\t\t\t\t" % (headers)
	#if shodan.settings['Verbose_Mode'] or len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
	if shodan.settings['Verbose_Mode'] or len(shodan.settings['Out_Custom_Fields']) > 0:
		#headers = "%s\t\t\t\t\t%s" % (headers, "Info")
		headers = "%s\t%s" % (headers, "Info")
	#headers = "%s\n%s\t\t%s\t%s\t\t%s" % (headers, ("-"*len("Target")), ("-"*len("Shodan Last Update")), ("-"*len("Cache Date")), ("-"*len("Cached Since")))
	headers = "%s\n%s\t\t%s" % (headers, ("-"*len("Target")), ("-"*len("Shodan Last Update")))
	if not shodan.settings['Out_No_CacheTime']:
		headers = "%s\t%s\t\t%s" % (headers, ("-"*len("Cache Date")), ("-"*len("Cached Since")))
	if shodan.settings['Verbose_Mode'] or len(shodan.settings['Out_Custom_Fields']) > 0:
		#headers = "%s\t\t\t\t\t%s" % (headers, ("-"*len("Info")))
		if not shodan.settings['Out_No_CacheTime']:
			headers = "%s\t\t\t\t" % (headers)
		headers = "%s\t%s" % (headers, ("-"*len("Info")))

	if shodan.settings['Flush_Cache']:
		print("[*] Flushing cache before listing...")

	# // output info of specified target
	#if target is not None:
	#if target is not None and ("-" not in target and "," not in target):
	if target is not None and not shodan._target_is_range(target):
		print(headers)
		if shodan._target_is_cache_index(target):
			target = shodan._get_target_by_cache_index(target)
			cache_file = shodan._get_out_path(shodan._target_as_out_file(target))
		else:
			cache_file = shodan._get_out_path(shodan._target_as_out_file(target))
		if not os.path.isfile(cache_file):
			shodan.cache_host_ip(target, shodan.settings['Include_History'])
			#return

		out_data = "%s" % target

		# // re-cache before stats out
		if shodan.settings['Flush_Cache']:
			shodan.cache_host_ip(target, shodan.settings['Include_History'])

		host = Shodan_Host(shodan.settings, shodan.get_cache_by_file(cache_file), False)
		last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, last_update)
		if not shodan.settings['Out_No_CacheTime']:
			c_time = os.path.getctime(cache_file)
			cached_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
			out_data = "%s\t%s" % (out_data, cached_date)
			#
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

		out_info = ""
		if shodan.settings['Verbose_Mode']:
			if len(host.hostnames) > 0 and not shodan.settings['Out_No_Hostname']:
				out_data = "%s\thostnames: %s" % (out_data, ', '.join(host.hostnames))
				if not shodan.settings['Out_Host_Only']:
					out_data = "%s / " % (out_data)
			else:
				out_data = "%s\t" % (out_data)
			if not shodan.settings['Out_Host_Only']:
				host_ports = ", ".join([str(int) for int in host.host_ports]) # convert int to str
				out_data = "%sPorts: %s" % (out_data, host_ports)
#		if shodan.settings['Verbose_Mode']:
#			if not shodan.settings['Out_No_Hostname'] and len(host.hostnames) > 0:
#				out_info = "%s\thostnames: %s" % (out_info, ', '.join(host.hostnames))
#			if not shodan.settings['Out_Host_Only']:
#				if len(out_info) > 0:
#					out_info = "%s / " % (out_info)
#				else:
#					out_info = "%s\t" % (out_info)
#				host_ports = ", ".join([str(int) for int in host.host_ports]) # convert int to str
#				out_info = "%sPorts: %s" % (out_info, host_ports)
#			if len(out_info) > 0:
#				out_data = "%s%s" % (out_data, out_info)

		# // tag target from matched named custom conditions
		if len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
			service_tags = []
			for service in host.services:
				#for tag in tags_by_match_service_on_named_multi_custom_conditions(shodan, service):
				for tag in tags_by_match_service_on_conditional_tag_conditions(shodan, service):
					if "[%s]" % tag not in service_tags:
						service_tags.append("[%s]" % tag)
			#if len(service_tags) == 0 and shodan.settings['Filter_Out_Non_Matched_Named_Custom_Conditions']:
			#	continue
			if len(service_tags) > 0:
				if shodan.settings['Out_Host_Only'] and shodan.settings['Verbose_Mode']:
					if not shodan.settings['Out_No_Hostname'] and len(host.hostnames) > 0:
						out_data = "%s / " % (out_data)
				elif shodan.settings['Out_No_Hostname'] and len(host.hostnames) > 0 and shodan.settings['Verbose_Mode']:
					out_data = "%s / " % (out_data)
				elif shodan.settings['Verbose_Mode']:
					out_data = "%s / " % (out_data)
				else:
					out_data = "%s\t" % (out_data)
				out_data = "%sTags: %s" % (out_data, ', '.join(service_tags))
			
		print(out_data)
		return
	
	# // output targets in cached
	# prefix each header with "cache index"
	header_data = ["#\t%s" % l for l in headers.split('\n') if len(l) > 0 ]
	header_data[1] = "-%s" % header_data[1][1:]
	headers = '\n'.join(header_data)
	print(headers)

	# // filter the target list based on specified target ranged (if any)
	filter_on_target_range = []
	if target is not None and ("-" in target or "," in target):
		target_ranges = target
		for target_range in target_ranges.split(","):
			if "-" in target_range:
				target_range = target_range.split("-")
				if len(target_range) != 2 or (not target_range[0].isnumeric() or not target_range[1].isnumeric()):
					continue
				for cache_index in range(int(target_range[0]), int(target_range[1])+1):
					target = shodan._get_target_by_cache_index(str(cache_index))
					filter_on_target_range.append(shodan._target_as_out_file(target))
				continue
			elif shodan._target_is_cache_index(target_range):
				cache_index = target_range
				target = shodan._get_target_by_cache_index(cache_index)
				filter_on_target_range.append(shodan._target_as_out_file(target))
			else:
				target = target_range
				# // re-cache before stats out
				#if shodan.settings['Flush_Cache']:
				#	shodan.cache_host_ip(target, shodan.settings['Include_History'])
				# ^-- managed through shodan_cache
				filter_on_target_range.append(shodan._target_as_out_file(target))

	#dir_list = os.listdir(shodan.settings['Cache_Dir'])
	dir_list = os.listdir(shodan_cache.location)
	cache_index = -1
	out_cache_list = []
	for file in dir_list:
		cache_index += 1
		#if not file.startswith("host.") or not file.endswith(".json"):
		if not shodan_cache._is_host_cache_filename(file):

			continue
		if len(filter_on_target_range) > 0 and file not in filter_on_target_range:
			continue

		target = shodan._out_file_as_target(file)
		out_data = "%s\t%s" % (cache_index, target)

		# // re-cache before stats out
		#if shodan.settings['Flush_Cache']:
		#	shodan.cache_host_ip(target, shodan.settings['Include_History'])
		# ^-- managed through shodan_cache

		host = shodan_cache.get_host_by_target(target)

		if not match_on_cached_host(shodan, host):
			continue

		last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		#if len(host.last_update) > 0:
		#	last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		#last_update = 'xxxx-xx-xx xx:xx:xx'
		out_data = "%s\t%s" % (out_data, last_update)

		if not shodan.settings['Out_No_CacheTime']:
			#c_time = os.path.getctime(cache_file)
			c_time = os.path.getctime(shodan_cache._get_target_cache_path(target))
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

		info_data = ""
		if shodan.settings['Verbose_Mode']:
			if len(host.hostnames) > 0 and not shodan.settings['Out_No_Hostname']:
				#info_data = "%s\tHostnames: %s" % (out_data, ', '.join(host.hostnames))
				info_data = "\tHostnames: %s" % (', '.join(host.hostnames))

			if not shodan.settings['Out_Host_Only']:
				if len(info_data) > 0:
					info_data = "%s / " % (info_data)
				else:
					info_data = "%s\t" % (info_data)
				host_ports = ", ".join([str(int) for int in host.host_ports]) # convert int to str
				info_data = "%sPorts: %s" % (info_data, host_ports)

		# // tag target from matched named custom conditions
		if len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
			service_tags = []
			for service in host.services:
				if shodan.settings['Debug_Mode']:
					print("[*] list_cache() : _shodan.id == '%s', port: %s, conditional_tag_conditions '%s'" % (service._json["_shodan"]["id"], service._json["port"], len(shodan.settings['Match_On_Named_Custom_Conditions'])))
				for tag in tags_by_match_service_on_conditional_tag_conditions(shodan, service):
					if "[%s]" % tag not in service_tags:
						service_tags.append("[%s]" % tag)
			if len(service_tags) == 0 and shodan.settings['Filter_Out_Non_Matched_Named_Custom_Conditions']:
				continue

			if len(service_tags) > 0:
				if len(info_data) > 0:
					info_data = "%s / " % (info_data)
				else:
					info_data = "%s\t" % (info_data)
				info_data = "%sTags: %s" % (info_data, ', '.join(service_tags))

		# // custom fields based on host services
		if len(shodan.settings['Out_Custom_Fields']) > 0:
			custom_field_list = []
			custom_fields = get_cache_host_custom_fields_by_host_services(shodan, host)
			field_data = ""
			for field in custom_fields:
				if len(field_data) > 0:
					field_data = "%s, " % field_data
				if 'list' == type(custom_fields[field]).__name__ and len(custom_fields[field]) > 0:
					if 'int' == type(custom_fields[field][0]).__name__:
						custom_fields[field] = [str(int) for int in custom_fields[field]] # convert int to str
					# expand nested list items
					elif 'list' == type(custom_fields[field][0]).__name__:
						field_items = []
						for item_index in range(len(custom_fields[field])):
							if 'list' == type(custom_fields[field][item_index]).__name__:
								if custom_fields[field][item_index] is None or len(custom_fields[field][item_index]) == 0:
									#custom_fields[field][item_index] = "null"
									continue
								field_items.append(', '.join(custom_fields[field][item_index]))
								custom_fields[field][item_index] = ', '.join(custom_fields[field][item_index])
							else:
								field_items.append(custom_fields[field][item_index])
						custom_fields[field] = field_items
					else:
						for item_index in range(len(custom_fields[field])):
							if custom_fields[field][item_index] is None:
								custom_fields[field][item_index] = "null"
				field_data = "%s[%s]: '%s'" % (field_data, field, ', '.join(custom_fields[field]))
			if len(field_data) > 0:
				if len(info_data) > 0:
					info_data = "%s / " % (info_data)
				else:
					info_data = "%s\t" % (info_data)
				info_data = "%s%s" % (info_data, field_data)

		if len(info_data) > 0:
			out_data = "%s%s" % (out_data, info_data)

		out_cache_list.append(out_data)

	out_cache_list = filter_list_by_head_tail(shodan, out_cache_list)
	for out_data in out_cache_list:
		print(out_data)

def get_cache_host_custom_fields_by_host_services(shodan, host):
	host_fields = OrderedDict()
	for service in host.services:
		service_fields = get_cache_host_custom_fields_by_service(shodan, service)
		for field in service_fields:
			if field not in host_fields:
				host_fields[field] = []
			for value in service_fields[field]:
				if value not in host_fields[field]:
					host_fields[field].append(value)

	return host_fields
def get_cache_host_custom_fields_by_service(shodan, service):
	fields = OrderedDict()
	if len(shodan.settings['Out_Custom_Fields']) == 0:
		return fields
	
	for custom in shodan.settings['Out_Custom_Fields']:
		if not match_on_json_path_condition(service._json, custom, shodan.settings['Debug_Mode']):
			continue
		#print("\tget_cache_host_custom_fields_by_service() : custom '%s'" % custom)
		
		path = set_default_json_path_condition(custom).split(':')[0].strip()
		path_exists, path_value = get_json_path(service._json, path)
		
		if path_exists:
			if path not in fields:
				fields[path] = []

			if "dict" == type(path_value).__name__:
				path_value = json_minify(path_value)

			if "str" == type(path_value).__name__:
				if " " in path_value or "," in path_value:
					path_value = '"%s"' % path_value
			
			if "list" == type(path_value).__name__ and len(path_value) > 0:
				for item in path_value:
					if item not in fields[path]:
						fields[path].append(item)
			else:
				if path_value not in fields[path]:
					fields[path].append(path_value)

			#if len(fields[path]) == 0:
			#	fields.pop(path)

	return fields
def match_on_cached_host(shodan, host):
	#if filter_out_cached_host(shodan, host):
	#	return False
	if not match_cached_host_on_condition(shodan, host):
		return False
	return True
def match_cached_host_on_condition(shodan, host):
	# // filter IN host based on conditions
	if len(shodan.settings['Match_On_Ports']) > 0:
		for port in shodan.settings['Match_On_Ports']:
			if port not in host.host_ports:
				return False

	if match_cache_host_or_services_on_multi_custom_conditions(shodan, host):
		return True
	return False
	if match_host_on_multi_custom_conditions(shodan, host):
		return True
	#return False

	found_any_match = False
	found_match = False
	filtered_services = []
	for service in host.services:
		# filter in/out based on condition
		#if match_service_on_condition(shodan, service):
		if match_host_on_multi_custom_conditions(shodan, service):
			found_match = True
			filtered_services.append(service)
		#if shodan.settings['Match_On_Named_Custom_Condition_File'] is not None:
		#if len(shodan.settings['Match_On_Named_Custom_Conditions']) > 0:
		#	if match_service_on_any_named_multi_custom_conditions(shodan, service):
		#		found_any_match = True
	
#	if len(shodan.settings['Match_On_Named_Custom_Conditions']) == 0:
#		if len(filtered_services) > 0:
#			return True
#	else:
#		for service in filtered_services:
#			if match_service_on_any_named_multi_custom_conditions(shodan, service):
#				return True
	return found_match

	#for service in filtered_services:

	if not found_any_match and not found_match:
		#return True
		return False
	return True
def match_cache_host_or_services_on_multi_custom_conditions(shodan, host):
	if len(shodan.settings['Match_On_Custom_Conditions']) == 0:
		return True

	multi_custom_conditions = shodan.settings['Match_On_Custom_Conditions']
	multi_condition_count = len(multi_custom_conditions)

	if shodan.settings['Debug_Mode']:
		print("[*] match_cache_host_or_services_on_multi_custom_conditions() : host.ip_str: %s, last_update: %s, condition.count: %s, multi_conditions: '%s'" % (host._json["ip_str"], host._json["last_update"], multi_condition_count, multi_custom_conditions))

	for multi_custom_condition in multi_custom_conditions:
		found_match_on_all_multi = True

		if shodan.settings['Debug_Mode']:
			print("[*] match_cache_host_or_services_on_multi_custom_conditions() : host.ip_str: %s, last_update: %s, condition.count: %s, conditions: '%s'" % (host._json["ip_str"], host._json["last_update"], len(multi_custom_condition), multi_custom_condition))
		
		for custom_condition in multi_custom_condition:
			if shodan.settings['Debug_Mode']:
				print("[*] match_cache_host_or_services_on_multi_custom_conditions() : host.ip_str: %s, last_update: %s, condition: '%s'" % (host._json["ip_str"], host._json["last_update"], custom_condition))
			# // first-check: check for match on host
			if match_host_or_service_json_on_custom_condition(shodan, host._json, custom_condition):
				continue
			# // second-check: try match on service instead
			found_service_match = False
			for service in host.services:
				if match_host_or_service_json_on_custom_condition(shodan, service._json, custom_condition):
					found_service_match = True
					continue
			if not found_service_match:
				found_match_on_all_multi = False

		if not found_match_on_all_multi:
			return False

	# // if no match then return false
	return True

def match_host_or_service_json_on_custom_condition(shodan, json, custom_condition):
	json_type = 'host'
	if "ports" not in json:
		json_type = 'service'

	path, condition, condition_value = parse_json_path_condition(custom_condition)
	#path = set_default_json_path_condition(custom_condition).split(':')[0].strip()
	path_exists, path_value = get_json_path(json, path)
	#print("json-path - path: %s, exists: %s, type: %s, condition: %s" % (path, path_exists, type(path_value).__name__, custom_condition[0]))
	#if not path_exists:
#	if not path_exists and Condition.strip_negation_operator(condition) == Condition.EXISTS and Condition.has_negation_operator(condition):
#		if shodan.settings['Debug_Mode']:
#			print("[+] [%s] - match_json_on_custom_conditions() : json.ip_str: %s, match on condition: '%s:%s'" % (json_type, json["ip_str"], path,condition))
#		return True
	#if not path_exists and Condition.strip_negation_operator(condition) != Condition.EXISTS and not Condition.has_negation_operator(condition):
	#if not path_exists:
#		if shodan.settings['Debug_Mode']:
#			print("[-] [%s] - match_json_on_custom_conditions() : json.ip_str: %s, skipping condition: '%s'" % (json_type, json["ip_str"], custom_condition))
#		return False

	if not match_on_json_path_condition(json, custom_condition, shodan.settings['Debug_Mode']):
		if shodan.settings['Debug_Mode']:
			print("[-] [%s] - match_json_on_custom_conditions() : json.ip_str: %s, no match on condition: '%s'" % (json_type, json["ip_str"], custom_condition))
		return False
	else:
		if shodan.settings['Debug_Mode']:
			print("[+] [%s] - match_json_on_custom_conditions() : json.ip_str: %s, match on condition: '%s'" % (json_type, json["ip_str"], custom_condition))
	return True
def match_host_on_multi_custom_conditions(shodan, host):
	if len(shodan.settings['Match_On_Multi_Custom_Conditions']) == 0:
		return True

	for multi_custom_condition in shodan.settings['Match_On_Multi_Custom_Conditions']:
		found_match_on_all_multi = True
		if shodan.settings['Debug_Mode']:
			print("[*] match_host_on_multi_custom_conditions() : host.ip_str: %s, last_update: %s, condition.count: %s, conditions: '%s'" % (host._json["ip_str"], host._json["last_update"], len(multi_custom_condition), multi_custom_condition))
		if not match_host_on_custom_conditions(shodan, host, multi_custom_condition.split(",")):
			found_match_on_all_multi = False
			break
	if found_match_on_all_multi:
		return True
	return False

def match_host_on_custom_conditions(shodan, host, custom_conditions):
	#print("Match_On_Custom_Conditions.count: %s" % len(shodan.settings['Match_On_Custom_Conditions']))
	if len(shodan.settings['Match_On_Custom_Conditions']) == 0:
		return True

	condition_count = len(custom_conditions)
	if shodan.settings['Debug_Mode']:
		print("[*] match_host_on_custom_conditions() : host.ip_str: %s, last_update: %s, condition.count: %s, conditions: '%s'" % (host._json["ip_str"], host._json["last_update"], condition_count, custom_conditions))
	for custom_condition in custom_conditions:
		#print("[*] match_host_on_custom_conditions() : host.ip_str: %s, last_update: %s, condition: '%s'" % (host._json["ip_str"], host._json["last_update"], custom_condition))
		path = set_default_json_path_condition(custom_condition).split(':')[0].strip()
		path_exists, path_value = get_json_path(host._json, path)
		if not path_exists:
			if shodan.settings['Debug_Mode']:
				print("[-] match_host_on_custom_conditions() : host.ip_str: %s, last_update: %s, skipping condition: '%s'" % (host._json["ip_str"], host._json["last_update"], custom_condition))
			return False
		#print("json-path - path: %s, exists: %s, type: %s, condition: %s" % (path, path_exists, type(path_value).__name__, custom_condition[0]))
		if not match_on_json_path_condition(host._json, custom_condition, False):
			if shodan.settings['Debug_Mode']:
				print("[-] match_host_on_custom_conditions() : host.ip_str == '%s', last_update: %s, no match on condition '%s'" % (host._json["ip_str"], host._json["last_update"], custom_condition))
			return False
		else:
			if shodan.settings['Debug_Mode']:
				print("[+] match_host_on_custom_conditions() : host.ip_str == '%s', last_update: %s, no match on condition '%s'" % (host._json["ip_str"], host._json["last_update"], custom_condition))
	return True
def filter_out_cached_host(shodan, host):
	# // filter OUT host based on conditions
	if len(shodan.settings['Filter_Out_Ports']) > 0:
		for port in host.host_ports:
			if port in shodan.settings['Filter_Out_Ports']:
				return True
	return False

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
	#if shodan.settings['Target'] is not None:
	if shodan.settings['Target'] is not None and not args.list_cache:
		# // resolve host/domain to ip address
		#if not shodan._target_is_ip_address(args.target) and not shodan._target_is_cache_index(args.target):
		if shodan._target_is_domain_host(shodan.settings['Target']):
			# // using the domain_info api costs 1 credit by query
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

	#if not shodan.cache_exists:
	#if not os.path.isfile(shodan._get_out_path(shodan._target_as_out_file(shodan.settings['Target']))):
	if not shodan._target_is_cached(shodan.settings['Target']):
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
	parser.add_argument('-t', dest='target', help="Host or IP address (or cache index) of the target to lookup. Use '-L' to list indexed cached targets (supports cache index range 'n,n-n,n')")
	parser.add_argument('-c', '--cache', dest='cache', action='store_true', help="Use cached data if exists or re-cache if '-O' is not specified.")
	parser.add_argument('-L', '--list-cache', dest='list_cache', action='store_true', help="List an overview of cached hosts and exit. Use '-F' to re-cache and '-t' for specific target. Use '-v' to list available ports and hostnames of the target." +
		"\nUse '--host-only' to only show hostnames in verbose mode ('-v'), '--hide-hostname' to hide hostnames in verbose mode ('-v')")
	parser.add_argument('-H', '--history', dest='include_history', action='store_true', help="Include host history when query shodan or when viewing cached target if available")
	parser.add_argument('--cache-dir', dest='cache_dir', metavar="<path>", default='shodan-data', help="define custom cache directory, default './shodan-data' in current directory" +
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
	parser.add_argument('-mc', '--match-json', dest='match_on_custom_conditions', type=str, nargs="*", action="append", metavar="<condition>", help="Match on json condition; syntax '<json-path>[:[negation-operator]<condition>[=<value>]]', supports comma-separated list" +
		"\n" +
		"supported conditions:\n" +
		"- 'exists': match if <json-path> exists\n" +
		"- 'is-null|null', 'is-empty|no-value', 'has-value': match on value of returned <json-path>\n" +
		"- 'is-type|type': match if defined type (<value>) == type of returned <json-path> value\n" +
		"- 'equals|value|is': match if <value> == value of returned <json-path>\n" +
		"- 'contains': match if value of returned <json-path> contains <value>\n" +
		"- 'has': match if <value> == value of returned <json-path> for 'list', 'OrderedDict' & 'dict' (json) \n" +
		"- 'starts|begins', 'ends': match if value of returned <json-path> matches condition of <value> for 'str' & 'int'\n" +
		"- 'len', 'min-len', 'max-len': match if length of returned <json-path> matches condition (same length, greater then equal or less then equal) of <value> for 'str', 'int', 'list', 'OrderedDict' & 'dict'\n" +
		"- 'gt', 'gte', 'lt', 'lte', 'eq': match if number of returned <json-path> matches condition (greater then, greater equal then, less then, less equal then, equal) of <value>\n" +
		"supported conditional negation operators: '!' or 'not-'; when prefixed the condition match on negated condition ('false' as 'true' and vice verse)" +
		"\n\texample: -mc '_shodan:!exists', -mc _shodan.module:not-contains=http" +
		"\ndefault behaviours:\n" +
		"- By default match by 'case insensitive', 'case sensitive' match when 'condition' starts with an uppercase letter\n" +
		"- Missing condition as '<path>' defaults to '<path>:exists', only negated condition as '<path>:not' defaults to '<path>:not-exists'\n" +
		"\n")
	parser.add_argument('--sort-date', dest='out_sort_by_scan_date', action='store_true', help="Output services by scan date, default port and scan date")
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
	parser.add_argument('--rm', dest='remove_target_from_cache', action='store_true', help="Removes target from the cache" +
	"\n\n")
	parser.add_argument('-cf', '--custom-field', dest='out_custom_fields', metavar="<condition>", help="Output field based on condition, see '-mc' for syntax")
	parser.add_argument('--cf-b64', dest='out_custom_fields_as_base64', action='store_true', help="Output field based on condition as base 64 (for safe output)")
	parser.add_argument('-cf-csv', dest='out_custom_fields_as_csv', metavar="<map-format>", help="Output the result using '-cf' as 'csv' format; format: <json-path>=<as_field_name>[,<json-path>=<as_field_name>,...][:<out_file>]")
	parser.add_argument('-cf-json', dest='out_custom_fields_as_json', action='store_true', help="Output the service result defined by '-cf' in flatten 'json' format as '{\"blob\"}: [<json-blob>]'")
	parser.add_argument('-n', '--no-dns', dest='no_dns_lookup', action='store_true', help="Never do DNS resolution/Always resolve")
	parser.add_argument('--host-only', dest='out_host_only', action='store_true', help="Only output host information, skip port/service information")
	parser.add_argument('--hide-hostname', dest='out_no_hostname', action='store_true', help="Hide hostnames and domains from overview")
	parser.add_argument('--hide-vulns', dest='out_no_vulns', action='store_true', help="Hide vulns information from overview and json output")
	parser.add_argument('--no-cache-time', dest='out_no_cache_time', action='store_true', help="Hide cache time when using '-L'")
	parser.add_argument('--threat-rule', dest='match_on_named_custom_condition_file', metavar="<file>", help="Tags services based on file with named (tag) defined custom conditions to match, same syntax as for '-mc'")
	parser.add_argument('--threat-only', dest='filter_out_non_matched_named_custom_conditions', action='store_true', help="Filter out services not matching the '--threat-rule' match")
	parser.add_argument('-v', '--verbose', dest='verbose_mode', action='store_true', help="Enabled verbose mode")
	parser.add_argument('--debug', dest='debug_mode', action='store_true', help="Enabled debug mode")

	args = parser.parse_args()
	main(args)
	testing(args)
