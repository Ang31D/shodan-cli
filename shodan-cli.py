#!/usr/bin/env python

from shodan import Shodan
from shodan.helpers import get_ip
from shodan.cli.helpers import get_api_key

import argparse
import json
import os
from collections import OrderedDict
from datetime import datetime, date
from dateutil import relativedelta
import io
from operator import attrgetter
from ipaddress import ip_address
import socket


class ShodanAPI:
	def __init__(self):
		self._init = False
		self._error_msg = None
		# Setup the Shodan API connection
		try:
			self._api = Shodan(get_api_key())
			self._init = True
		except Exception as e:
			self._error_msg = e

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

	def info(self):
		data = None
		try:
			data = self._api.info()
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

	# // domain_info costs 1 credit by query
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

		self.settings['Verbose_Mode'] = False

		self.settings['Out_Host_JSON'] = False
		self.settings['Out_Service_Data'] = False
		self.settings['Out_Service_Module'] = False
		self.settings['Out_Service_JSON'] = False

		self.settings['Match_On_Ports'] = []
		self.settings['Match_On_Modules'] = []
		self.settings['Filter_Out_Ports'] = []
		
		self.init(args)

	def init(self, args):
		#self.settings['Cache'] = args.cache
		if args.cache_dir is not None:
			self.settings['Cache_Dir'] = args.cache_dir
		self.settings['Flush_Cache'] = args.flush_cache

		self.settings['Target'] = args.target
		self.settings['Include_History'] = args.include_history

		self.settings['Verbose_Mode'] = args.verbose_mode
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
		if args.filter_out_ports is not None:
			for port in args.filter_out_ports.split(','):
				self.settings['Filter_Out_Ports'].append(int(port.strip()))

class ShodanEx:
	def __init__(self, args):
		self.settings = ShodanSettings(args).settings
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
		if not target.isnumeric():
			return False
		dir_list = os.listdir(self.settings['Cache_Dir'])
		if len(dir_list) == 0:
			return False
		if int(target) < 0 or int(target) >= len(dir_list):
			return False
		return True
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
	def __init__(self, json_data, include_history):
		self._json = json_data
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
			return "%s (%s)" % (self._json["_shodan"]["id"], self.timestamp)
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
	def components(self):
		result = []
		if 'http' in self._json and "components" in self._json['http']:
			for technology in self._json['http']['components']:
				categories = self._json['http']['components'][technology]['categories']
				result.append('"%s": "%s"' % (technology, ', '.join(categories)))
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
def filter_out_service(shodan, service):
	# filter in/out based on port, module-name
	if len(shodan.settings['Match_On_Ports']) > 0:
		if service.port not in shodan.settings['Match_On_Ports']:
			return True
	if len(shodan.settings['Filter_Out_Ports']) > 0:
		if service.port in shodan.settings['Filter_Out_Ports']:
			return True
	if len(shodan.settings['Match_On_Modules']) > 0:
		module_name = service.module_name
		if '-' in module_name:
			module_name = module_name.split('-')[0]
		if service.module_name not in shodan.settings['Match_On_Modules'] and module_name not in shodan.settings['Match_On_Modules']:
			return True
	filter_out = False
def out_shodan(shodan):
	json_data = shodan.get_cache()

	print("* Shodan\n %s" % ('-'*30))
	#print("Target: %s" % shodan.settings["Target"])
	
	host = Shodan_Host(json_data, shodan.settings['Include_History'])

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
			print("OS: %s - based on services!" % ', '.join(os_list))
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
	
	if shodan.settings['Out_Host_JSON']:
		host_data = ["[*] %s" % l for l in host.json.split('\n') if len(l) > 0 ]
		print('\n'.join(host_data))
	print("* Service Overview\n %s" % ('-'*30))
	# // format service headers
	print("Scan-Date\tPort      Service\tVersion / Info")
	print("%s\t%s      %s\t%s" % (("-"*len("Scan-date")), ("-"*len("Port")), ("-"*len("Service")), ("-"*len("Version / Info"))))
	for service in host.services:
		# filter in/out based on port, module-name
		if filter_out_service(shodan, service):
			continue

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
		print("%sShodan - Identifier: %s" % (fill_prefix, service.identifier))

		if shodan.settings['Verbose_Mode']:
			print("%sPort - First Seen: %s" % (fill_prefix, service.first_seen))
			if service.has_tags:
				print("%sTags: %s" % (fill_prefix, ', '.join(service.tags)))
			print("%s* %s %s" % (fill_prefix, "Product", service.product.name))
			# [BUG]: shows for every services, even if the product name isn´t 'Cobalt Strike Beacon'!
			if service.product.is_cobaltstrike:
				print("%s* %s" % (fill_prefix, "Hosting 'Cobalt Strike Beacon'"))
			# // HTTP Module
			if service.is_web_service:
				http_module = Module_HTTP(service)
				# // try to figure out the http-server
				http_server = ""
				if http_module.header_exists("Server"):
					http_server = http_module.get_header("Server")
				elif 'ASP.NET' in service.data:
					http_server = "most likely 'IIS' (found 'ASP.NET' in headers)"
				if len(http_server) > 0:
					print("%s# 'Server' header: %s" % (fill_prefix, http_server))
				# // info from module data
				module_data = service.get_module_data()
				if module_data is not None:
					#if 'waf' in module_data and module_data['waf'] is not None:
					#	print("%sWAF: %s" % (fill_prefix, module_data['waf']))
					if http_module.has_waf:
						print("%sWAF: %s" % (fill_prefix, http_module.waf))
						
					print('%sWEB Info' % fill_prefix)
					if 'title' in module_data and module_data['title'] is not None:
						print("%s   Page Title: %s" % (fill_prefix, module_data['title']))
					if 'headers_hash' in module_data and module_data['headers_hash'] is not None:
						print("%s   Headers Hash: %s" % (fill_prefix, module_data['headers_hash']))
					if 'html_hash' in module_data and module_data['html_hash'] is not None:
						print("%s   HTML hash: %s" % (fill_prefix, module_data['html_hash']))
				if http_module.favicon_hash is not None:
					print("%s   favicon Hash: %s" % (fill_prefix, http_module.favicon_hash))
				if len(http_module.components) > 0:
					print("%s   Web Technologies: %s" % (fill_prefix, ', '.join(http_module.components)))
	
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

			#if 'ssh' == service.module_name:
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

def list_cache(shodan, target=None):
	headers = "Target\t\tShodan Last Update\tCache Date\t\tCached Since"
	if shodan.settings['Verbose_Mode']:
		headers = "%s\t\t\t\t\t%s" % (headers, "Info")
	headers = "%s\n%s\t\t%s\t%s\t\t%s" % (headers, ("-"*len("Target")), ("-"*len("Shodan Last Update")), ("-"*len("Cache Date")), ("-"*len("Cached Since")))
	if shodan.settings['Verbose_Mode']:
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

		host = Shodan_Host(shodan.get_cache_by_file(cache_file), False)
		last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, last_update)
		c_time = os.path.getctime(cache_file)
		cached_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, cached_date)

		end_date = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')
		cache_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f')
		cached_delta = relativedelta.relativedelta(end_date, cache_date)
		cache_delta = relativedelta.relativedelta(end_date, cache_date)
		out_data = "%s\t" % out_data
		out_data = "%s%s years" % (out_data, cached_delta.years)
		out_data = "%s, %s months" % (out_data, cached_delta.months)
		out_data = "%s, %s days" % (out_data, cached_delta.days)
		out_data = "%s, %sh, %s min" % (out_data, cached_delta.hours, cached_delta.minutes)
		if cached_delta.minutes == 0:
			out_data = "%s, %s sec" % (out_data, cached_delta.seconds)
		else:
			out_data = "%s\t" % out_data

		if shodan.settings['Verbose_Mode']:
			if len(host.hostnames) > 0:
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
		host = Shodan_Host(shodan.get_cache_by_file(cache_file), False)
		last_update = datetime.strptime(host.last_update, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, last_update)
		c_time = os.path.getctime(cache_file)
		cached_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S")
		out_data = "%s\t%s" % (out_data, cached_date)

		end_date = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')
		cache_date = datetime.strptime(str(datetime.fromtimestamp(c_time)), '%Y-%m-%d %H:%M:%S.%f')
		cached_delta = relativedelta.relativedelta(end_date, cache_date)
		cache_delta = relativedelta.relativedelta(end_date, cache_date)
		out_data = "%s\t" % out_data
		out_data = "%s%s years" % (out_data, cached_delta.years)
		out_data = "%s, %s months" % (out_data, cached_delta.months)
		out_data = "%s, %s days" % (out_data, cached_delta.days)
		out_data = "%s, %sh, %s min" % (out_data, cached_delta.hours, cached_delta.minutes)
		if cached_delta.minutes == 0:
			out_data = "%s, %s sec" % (out_data, cached_delta.seconds)
		else:
			out_data = "%s\t" % out_data

		if shodan.settings['Verbose_Mode']:
			if len(host.hostnames) > 0:
				out_data = "%s\thostnames: %s / " % (out_data, ', '.join(host.hostnames))
			else:
				out_data = "%s\t" % (out_data)
			host_ports = ", ".join([str(int) for int in host.host_ports]) # convert int to str
			out_data = "%sPorts: %s" % (out_data, host_ports)
			
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
	#api_info = json.load(api_info)
	
	scan_credits = int(api_info['scan_credits'])
	print("Scan Credits (left): %s" % (scan_credits))

	limits_scan_credits = int(api_info['usage_limits']['scan_credits'])
	limits_query_credits = int(api_info['usage_limits']['query_credits'])
	limits_monitored_ips = int(api_info['usage_limits']['monitored_ips'])
	out_data = "* Credit Limits"
	out_data = "%s\nScan: %s" % (out_data, limits_scan_credits)
	out_data = "%s\nQuery: %s" % (out_data, limits_query_credits)

	print(out_data)
	

	if shodan.settings['Verbose_Mode']:
		print(json.dumps(api_info, indent=4))
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

	shodan = ShodanEx(args)
	if args.target is not None:
		# // resolve host/domain to ip address
		if not shodan._target_is_ip_address(args.target) and not shodan._target_is_cache_index(args.target):
			# // domain_info costs 1 credit by query
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
	if shodan.settings['Target'] is not None and shodan._target_is_cache_index(shodan.settings['Target']):
		shodan.settings['Target'] = shodan._get_target_by_cache_index(shodan.settings['Target'])
		if shodan.settings['Target'] is None:
			#print("[!] Failed to ")
			return
		cache_file = shodan._get_out_path(shodan._target_as_out_file(shodan.settings['Target']))
		shodan.settings['Cache_File'] = cache_file

	if args.remove_target_from_cache:
		if shodan._target_is_cached(shodan.settings['Target']):
			cache_file = shodan._get_out_path(shodan._target_as_out_file(shodan.settings['Target']))
			os.remove(cache_file)
			print("[*] Removed target '%s' from cache" % shodan.settings['Target'])
			return

	if args.out_api_info:
		out_shodan_api_info(shodan)
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

if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Shodan Cli in python")

	parser.add_argument('--api-info', dest='out_api_info', action='store_true', help="Output API info and exit")
	#parser.add_argument('-t', dest='target', help='Host or IP address of the target to lookup, specify a file for multiple targets')
	parser.add_argument('-t', dest='target', help='Host or IP address (or cache index) of the target to lookup')
	parser.add_argument('-c', '--cache', dest='cache', action='store_true', help="Use cached data if exists or re-cache if '-O' is not specified.")
	parser.add_argument('-C', '--cache-dir', dest='cache_dir', default='shodan-data', help="store cache to directory, default 'shodan-data'")
	parser.add_argument('-L', '--list-cache', dest='list_cache', action='store_true', help="List cached hosts and exit, use '-F' to re-cache")
	parser.add_argument('-F', '--flush-cache', dest='flush_cache', action='store_true', help="Flush cache from history, use '-t' to re-cache target data")
	parser.add_argument('--rm', dest='remove_target_from_cache', action='store_true', help='Removes target from the cache')
	parser.add_argument('-H', '--history', dest='include_history', action='store_true', help="Include host history")
	parser.add_argument('-d', '--service-data', dest='out_service_data', action='store_true', help="Output service details")
	parser.add_argument('-m', '--service-module', dest='out_service_module', action='store_true', help="Output service module data")
	parser.add_argument('-mp', '--match-ports', dest='match_on_ports', help='Match on ports, comma separated list')
	parser.add_argument('-mm', '--match-module', dest='match_on_modules', help='Match on modules, comma separated list')
	parser.add_argument('-fp', '--filter-ports', dest='filter_out_ports', help='Filter out ports, comma separated list')
	parser.add_argument('--host-json', dest='out_host_json', action='store_true', help="Output host json")
	parser.add_argument('--service-json', dest='out_service_json', action='store_true', help="Output service json")
	parser.add_argument('-v', '--verbose', dest='verbose_mode', action='store_true', help="Enabled verbose mode")

	args = parser.parse_args()
	main(args)
