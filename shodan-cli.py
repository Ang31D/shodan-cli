#!/usr/bin/env python

from shodan import Shodan
from shodan.helpers import get_ip
from shodan.cli.helpers import get_api_key

import argparse
import json
import os
from collections import OrderedDict
from datetime import datetime
import io


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

	def lookup_host_ip(self, host_ip, history=False):
		data = None
		try:
			data = self._api.host(host_ip, history=history)
		except Exception as e:
			self._error_msg = e
		return data

class ShodanSettings:
	def __init__(self, args):
		self.settings = OrderedDict()
		self.settings['Use_Cache'] = False
		self.settings['Cache_Dir'] = "shodan-data"

		self.settings['Target'] = None
		self.settings['Fetch_History'] = False

		self.settings['Out_Data'] = False
		self.settings['Verbose_Enabled'] = False

		self.settings['Out_Host_JSON'] = False
		self.settings['Out_Service_Data'] = False
		self.settings['Out_Service_Module'] = False
		self.settings['Out_Service_JSON'] = False

		self.settings['Match_On_Ports'] = []
		self.settings['Match_On_Modules'] = []
		self.settings['Filter_Out_Ports'] = []
		
		self.init(args)

	def init(self, args):
		self.settings['Use_Cache'] = args.cache
		if args.cache_dir is not None:
			self.settings['Cache_Dir'] = args.cache_dir

		self.settings['Target'] = args.target
		self.settings['Fetch_History'] = args.fetch_history

		self.settings['Out_Data'] = args.out_data
		self.settings['Verbose_Enabled'] = args.verbose_mode
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
		if not self.settings['Use_Cache']:
			return

		if not os.path.isdir(self.settings['Cache_Dir']):
			os.mkdir(self.settings['Cache_Dir'])

		out_file = "host.%s.json" % self.settings['Target']
		cache_file = os.path.join(self.settings['Cache_Dir'], out_file)
		self.settings['Cache_File'] = cache_file

	@property
	def use_cache(self):
		return self.settings["Use_Cache"]
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

		json_data = None
		with open(self.settings['Cache_File'], 'r') as f:
			json_data = json.load(f)
		return json_data
	def cache_host_ip(self):
		if "Cache_File" not in self.settings:
			return
		target = self.settings['Target']
		fetch_history = self.settings['Fetch_History']
		self._cache_data = self.api.lookup_host_ip(target, fetch_history)
		if self.api.has_error:
			print("[!] shodan api error '%s'" % self.api.error_msg)
		if self._cache_data is not None:
			with open(self.settings['Cache_File'], "w") as f:
				f.write(json.dumps(self._cache_data))

	@property
	def host_ports(self):
		data = self.get_cache()
		ports = data["ports"]
		ports.sort()
		return ports
class Shodan_Host:
	def __init__(self, json_data):
		self._json = json_data
		self.last_update = '' if 'last_update' not in self._json else self._json['last_update']
		self.ip = self._json['ip_str']
		#self.os = 'Unknown' if self._json['os'] is None else self._json['os']
		self.asn = '' if 'asn' not in self._json else self._json['asn']
		self.hostnames = self._json['hostnames']
		self.domains = self._json['domains']
		self.country_code = '' if 'country_code' not in self._json else self._json['country_code']
		self.country_name = '' if 'country_name' not in self._json else self._json['country_name']
		self.country = "%s - %s" % (self._json['country_code'], self._json['country_name'])
		self.city = self._json['city']
		self.longitude = self._json['longitude']
		self.latitude = self._json['latitude']
		self.geo = "%s, %s (long, lat)" % (self._json['longitude'], self._json['latitude'])
		self.isp = self._json['isp']
		self.org = self._json['org']
		self.services = []
		for json_port in self._json['data']:
			self.services.append(Port_Service(json_port))

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
		
		
class Port_Service:
	def __init__(self, json_data):
		self._json = json_data
		self.port = int(self._json['port'])
		self.transport = self._json['transport']
		self.timestamp = '' if 'timestamp' not in self._json else self._json['timestamp']
		self.scan_date = ''
		if len(self.timestamp) > 0:
			#self.scan_date = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d %H:%M:%S.%f")
			self.scan_date = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%d")
		self.product = Service_Product(self._json)
	
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
class Service_Product:
	def __init__(self, json_data):
		self._json = json_data
		self.name = '' if 'product' not in self._json else self._json['product']
		self.version = '' if 'version' not in self._json else self._json['version']
		self.info = '' if 'info' not in self._json else self._json['info']

	def is_cobaltstrike(self):
		if self.name == "Cobalt Strike Beacon":
			return True
		return False

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
		status_head, headers_dict = self._create_header_dict(io.StringIO(self.service.data))
		return headers_dict
	@property
	def header_status(self):
		status_head, headers_dict = self._create_header_dict(io.StringIO(self.service.data))
		return status_head

	@property
	def has_ssl_data(self):
		return 'ssl' in self._json
	@property
	def ssl_data(self):
		if self.has_ssl_data:
			return self._json['ssl']
		return None

	@property
	def jarm(self):
		if 'https' == self.service.module_name and self.has_ssl_data:
			if 'jarm' in self.ssl_data:
				return self.ssl_data['jarm']
		return None
	@property
	def ja3s(self):
		if 'https' == self.service.module_name and self.has_ssl_data:
			if 'ja3s' in self.ssl_data:
				return self.ssl_data['ja3s']
		return None
	@property
	def tls_versions(self):
		if 'versions' in self.ssl_data:
			return self.ssl_data['versions']
		return []

	@property
	def has_cert(self):
		if self.has_ssl_data:
			return 'cert' in self.ssl_data
		return False
	@property
	def cert_issued(self):
		if 'cert' in self.ssl_data:
			return datetime.strptime(self.ssl_data['cert']['issued'], '%Y%m%d%H%M%SZ').strftime("%Y-%m-%d %H:%M:%S")
		return None
	@property
	def cert_expires(self):
		if 'cert' in self.ssl_data:
			return datetime.strptime(self.ssl_data['cert']['expires'], '%Y%m%d%H%M%SZ').strftime("%Y-%m-%d %H:%M:%S")
		return None
	@property
	def cert_expired(self):
		if 'cert' in self.ssl_data:
			return self.ssl_data['cert']['expired']
		return ''
	@property
	def cert_fingerprint(self):
		if 'cert' in self.ssl_data and 'fingerprint' in self.ssl_data['cert']:
			return self.ssl_data['cert']['fingerprint']['sha256']
		return None
	@property
	def cert_serial(self):
		if 'cert' in self.ssl_data and 'serial' in self.ssl_data['cert']:
			return self.ssl_data['cert']['serial']
		return None
	@property
	def cert_subject_cn(self):
		if 'cert' in self.ssl_data and 'subject' in self.ssl_data['cert']:
			return self.ssl_data['cert']['subject']['CN']
		return None
	@property
	def cert_issuer_cn(self):
		if 'cert' in self.ssl_data and 'issuer' in self.ssl_data['cert']:
			return self.ssl_data['cert']['issuer']['CN']
		return None

	def _create_header_dict(self, ioheaders):
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

def out_shodan(shodan):
	json_data = shodan.get_cache()

	#print(shodan.get_cache())
	print("* Shodan\n %s" % ('-'*30))
	print("Target: %s" % shodan.settings["Target"])
	
	#print("Tags: %s" % ','.join(json_data['tags']))
	host = Shodan_Host(json_data)
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
	print("Ports: %s" % ", ".join([str(int) for int in shodan.host_ports])) # convert int to str
	print("Location: %s" % host.as_location())
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
		#print(host.json)
		host_data = ["[*] %s" % l for l in host.json.split('\n') if len(l) > 0 ]
		print('\n'.join(host_data))
	print("* Service Overview\n %s" % ('-'*30))
	# // format service headers
	print("Scan-Date\tPort      Service\tVersion / Info")
	print("%s\t%s      %s\t%s" % (("-"*len("Scan-date")), ("-"*len("Port")), ("-"*len("Service")), ("-"*len("Version / Info"))))
	for service in host.services:
		# filter in/out based on port, module-name
		if len(shodan.settings['Match_On_Ports']) > 0:
			if service.port not in shodan.settings['Match_On_Ports']:
				continue
		if len(shodan.settings['Filter_Out_Ports']) > 0:
			if service.port in shodan.settings['Filter_Out_Ports']:
				continue

		if len(shodan.settings['Match_On_Modules']) > 0:
			if service.module_name not in shodan.settings['Match_On_Modules']:
				continue

		# // output service overview
		fill_prefix = 1
		service_header = "%s/%s" % (service.port, service.transport.upper())
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
		if service.has_tags:
			print("%sTags: %s" % (fill_prefix, ', '.join(service.tags)))

		# // HTTP Module
		if 'https' == service.module_name or 'http' == service.module_name:
			http_module = Module_HTTP(service)
			#print(json.dumps(http_module.headers, indent=4))
			# // try to figure out the http-server
			http_server = ""
			if http_module.header_exists("Server"):
				http_server = http_module.get_header("Server")
			elif 'ASP.NET' in service.data:
				http_server = "most likely 'IIS' (found 'ASP.NET' in headers)"
				#print(json.dumps(http_module.headers, indent=4))
			if len(http_server) > 0:
				print("%s# Server: %s" % (fill_prefix, http_server))

			# // output SSL Certificate information
			if 'https' == service.module_name and http_module.has_ssl_data:
				if http_module.jarm is not None:
					print('%sjarm: %s' % (fill_prefix, http_module.jarm))
				if http_module.ja3s is not None:
					print('%sja3s: %s' % (fill_prefix, http_module.ja3s))
				if len(http_module.tls_versions) > 0:
					print('%sTLS-Versions: %s' % (fill_prefix, ', '.join(http_module.tls_versions)))
				if http_module.has_cert:
					print('%sSSL Certificate' % fill_prefix)
					print('%s   Issued: %s, Expires: %s (Expired: %s)' % (fill_prefix, http_module.cert_issued, http_module.cert_expires, http_module.cert_expired))
					if http_module.cert_fingerprint is not None:
						print('%s   Fingerprint: %s' % (fill_prefix, http_module.cert_fingerprint))
					if http_module.cert_serial is not None:
						print('%s   Serial: %s' % (fill_prefix, http_module.cert_serial))
					if http_module.cert_subject_cn is not None:
						print('%s   Subject.CN: %s' % (fill_prefix, http_module.cert_subject_cn))
					if http_module.cert_issuer_cn is not None:
						print('%s   Issuer.CN: %s' % (fill_prefix, http_module.cert_issuer_cn))
				

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
		#if "cobalt_strike_beacon" in json_port:

def main(args):
	#host = "119.45.94.71"

	shodan = ShodanEx(args)

	if args.list_cache:
		dir_list = os.listdir(shodan.settings['Cache_Dir'])
		for file in dir_list:
			if file.startswith("host.") and file.endswith(".json"):
				print('.'.join(file.split('.')[1:5]))
		return

	if args.flush_cache:
		dir_list = os.listdir(shodan.settings['Cache_Dir'])
		for file in dir_list:
			cache_file = os.path.join(shodan.settings['Cache_Dir'], file)
			os.remove(cache_file)
		return

	if not shodan.api.is_available:
		if shodan.api.has_error:
			print("[!] shodan api error '%s'" % shodan.api.error_msg)
			shodan.api._reset_error_msg()
		print("Shodan API not available, please run 'shodan init <api-key>'")
		return

	if shodan.use_cache:
		# re-cache data
		if not shodan.settings['Out_Data']:
			print("[*] Caching information for target '%s'..." % shodan.settings['Target'])
			shodan.cache_host_ip()
			if shodan.get_cache() is None:
				print("[!] No information available for target '%s'" % shodan.settings['Target'])
			return
		# cache data if not exists
		if not shodan.cache_exists:
			#print('[*] caching data...')
			print("[*] Retrieving information for target '%s'..." % shodan.settings['Target'])
			shodan.cache_host_ip()
		if shodan.get_cache() is None:
			print("[!] No information available for target '%s'" % shodan.settings['Target'])
			return
	if shodan.settings['Out_Data']:
		out_shodan(shodan)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Shodan Cli in python")

	parser.add_argument('-t', dest='target', required=True, help='Host or IP address of the target to lookup')
	parser.add_argument('-c', '--cache', dest='cache', action='store_true', help="Use cached data if exists or re-cache if '-O' is not specified.")
	parser.add_argument('-C', '--cache-dir', dest='cache_dir', default='shodan-data', help="store cache to directory, default 'shodan-data'")
	parser.add_argument('-L', '--list-cache', dest='list_cache', action='store_true', help="List cached hosts")
	parser.add_argument('-F', '--flush-cache', dest='flush_cache', action='store_true', help="Flush cache from history")
	parser.add_argument('-H', '--history', dest='fetch_history', action='store_true', help="Fetch host history")
	parser.add_argument('-O', '--out-data', dest='out_data', action='store_true', help="Output data to console")
	parser.add_argument('-v', '--verbose', dest='verbose_mode', action='store_true', help="Enabled verbose mode")
	parser.add_argument('-d', '--service-data', dest='out_service_data', action='store_true', help="Output service details")
	parser.add_argument('-m', '--service-module', dest='out_service_module', action='store_true', help="Output service module data")
	parser.add_argument('-mp', '--match-ports', dest='match_on_ports', help='Match on ports, comma separated list')
	parser.add_argument('-mm', '--match-module', dest='match_on_modules', help='Match on modules, comma separated list')
	parser.add_argument('-fp', '--filter-ports', dest='filter_out_ports', help='Filter out ports, comma separated list')
	parser.add_argument('--host-json', dest='out_host_json', action='store_true', help="Output host json")
	parser.add_argument('--service-json', dest='out_service_json', action='store_true', help="Output service json")

	args = parser.parse_args()
	main(args)
