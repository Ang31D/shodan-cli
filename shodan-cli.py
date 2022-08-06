#!/usr/bin/env python

from shodan import Shodan
from shodan.helpers import get_ip
from shodan.cli.helpers import get_api_key

import argparse
import json
import os
from collections import OrderedDict
from datetime import datetime


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

		self.settings['Out_Service_Data'] = False
		self.settings['Out_Service_Module'] = False

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
		self.settings['Out_Service_Data'] = args.out_service_data
		self.settings['Out_Service_Module'] = args.out_service_module
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
	print("Hostnames: %s" % ','.join(host.hostnames))
	print("Domains: %s" % ','.join(host.domains))
	print("Ports: %s" % ", ".join([str(int) for int in shodan.host_ports])) # convert int to str
	print("Location: %s" % host.as_location())
	print("")
	print("ISP: %s" % host.isp)
	print("Organization: %s" % host.org)
	print("ASN: %s" % host.asn)
	print("")
	#
	print("* Service Overview\n %s" % ('-'*30))
	print("Scan-Date\tPort/Prot\tBanner")
	print("%s\t%s\t%s" % (("-"*len("Scan-date")), ("-"*len("Scan-date")), ("-"*len("Banner"))))
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

		service_header = "%s/%s" % (service.port, service.transport.upper())
		if len(service.banner) > 0:
			service_header = "%s\t\t%s" % (service_header, service.banner)
		print("%s\t%s" % (service.scan_date, service_header))

		if service.has_tags:
			print("\t\t\t\tTags: %s" % ', '.join(service.tags))

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

		if shodan.settings['Out_Service_Data'] or shodan.settings['Out_Service_Module']:
			print("")
		#if "cobalt_strike_beacon" in json_port:

def main(args):
	#host = "119.45.94.71"

	shodan = ShodanEx(args)
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
	parser.add_argument('-H', '--history', dest='fetch_history', action='store_true', help="Fetch host history")
	parser.add_argument('-O', '--out-data', dest='out_data', action='store_true', help="Output data to console")
	parser.add_argument('-v', '--verbose', dest='verbose_mode', action='store_true', help="Enabled verbose mode")
	parser.add_argument('-d', '--service-data', dest='out_service_data', action='store_true', help="Output service details")
	parser.add_argument('-m', '--service-module', dest='out_service_module', action='store_true', help="Output service module data")
	parser.add_argument('-mp', '--match-ports', dest='match_on_ports', help='Match on ports, comma separated list')
	parser.add_argument('-mm', '--match-module', dest='match_on_modules', help='Match on modules, comma separated list')
	parser.add_argument('-fp', '--filter-ports', dest='filter_out_ports', help='Filter out ports, comma separated list')

	args = parser.parse_args()
	main(args)
