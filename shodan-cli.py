#!/usr/bin/env python

from shodan import Shodan
from shodan.helpers import get_ip
from shodan.cli.helpers import get_api_key

import argparse
import json
import os
from collections import OrderedDict


class ShodanAPI:
	def __init__(self):
		self._init = False
		# Setup the Shodan API connection
		try:
			self._api = Shodan(get_api_key())
			self._init = True
		except:
			self._init = False

	@property
	def is_available(self):
		return self._init

	def lookup_host_ip(self, host_ip, history=False):
		data = None
		try:
			data = self._api.host(host_ip, history=history)
		except:
			pass
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
		if args.filter_out_ports is not None:
			for port in args.filter_out_ports.split(','):
				self.settings['Filter_Out_Ports'].append(int(port.strip()))

class ShodanEx:
	def __init__(self, args):
		self.settings = ShodanSettings(args).settings
		self.api = ShodanAPI()
		self.cache_data = None
		self._setup_cache()

	def _setup_cache(self):
		self.cache_data = None
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
		#return os.path.isfile(self.settings['Cache_File'])
		if os.path.isfile(self.settings['Cache_File']):
			if os.path.getsize(self.settings['Cache_File']) > 0:
				return True
		return False

	def get_cache(self):
		if self.cache_data is not None:
			return self.cache_data
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
		self.cache_data = self.api.lookup_host_ip(target, fetch_history)
		if self.cache_data is not None:
			with open(self.settings['Cache_File'], "w") as f:
				f.write(json.dumps(self.cache_data))

	@property
	def host_ports(self):
		data = self.get_cache()
		ports = data["ports"]
		return ports
class Shodan_Host:
	def __init__(self, json_data):
		self._json = json_data
		self.ip = json_data['ip_str']
		self.asn = '' if 'asn' not in json_data else json_data['asn']
		self.hostnames = json_data['hostnames']
		self.domains = json_data['domains']
		#self.country_code = json_data['country_code']
		#self.country_name = json_data['country_name']
		self.country_code = '' if 'country_code' not in json_data else json_data['country_code']
		self.country_name = '' if 'country_name' not in json_data else json_data['country_name']
		self.country = "%s - %s" % (json_data['country_code'], json_data['country_name'])
		self.city = json_data['city']
		self.longitude = json_data['longitude']
		self.latitude = json_data['latitude']
		self.geo = "%s, %s (long, lat)" % (json_data['longitude'], json_data['latitude'])
		self.isp = json_data['isp']
		self.org = json_data['org']

	def as_location(self):
		data = ""
		
		#self.region_code
		data = "%s (%s), %s" % (self.country_name, self.country_code, self.city)
		data = "%s # long: %s, lat: %s" % (data, self.longitude,self.latitude)
		return data
		
		
class Port_Service:
	def __init__(self, json_data):
		self._json = json_data
		self.port = json_data['port']
		self.transport = json_data['transport']
		#self.product = json_data['product']
		#self.version = json_data['version']
		self.product = '' if 'product' not in json_data else json_data['product']
		self.version = '' if 'version' not in json_data else json_data['version']
	
	def as_string(self):
		data = "%s/%s" % (self.port, self.transport.upper())
		if len(self.product) > 0:
			data = "%s - %s" % (data, self.product)
			if len(self.version) > 0:
				data = "%s (%s)" % (data, self.version)
		return data
		#return "%s/%s - %s # %s" % (self.transport.upper(), self.port, self.product, self.version)

def out_shodan(shodan):
	json_data = shodan.get_cache()

	#print(shodan.get_cache())
	print("")
	print("Target: %s" % shodan.settings["Target"])
	"""
			    "location": {
        		"city": "Beijing",
        		"region_code": null,
        		"area_code": null,
        		"longitude": 116.39723,
        		"country_name": "China",
        		"country_code": "CN",
        		"latitude": 39.9075
        	}
	"""
	print("")
	#print("Tags: %s" % ','.join(json_data['tags']))
	host = Shodan_Host(json_data)
	print("* Host Overview\n %s" % ('-'*30))
	print("IP Address: %s" % host.ip)
	print("Hostnames: %s" % ','.join(host.hostnames))
	print("Ports: %s" % ", ".join([str(int) for int in shodan.host_ports])) # convert int to str
	print("Location: %s" % host.as_location())
	print("")
	print("ISP: %s" % host.isp)
	print("Organization: %s" % host.org)
	print("ASN: %s" % host.asn)
	print("")
	#
	#print(json_data['data'][0])
	port_service = Port_Service(json_data['data'][0])
	print("* Service Overview\n %s" % ('-'*30))
	for json_port in json_data['data']:
		port_service = Port_Service(json_port)
		if len(shodan.settings['Match_On_Ports']) > 0:
			if int(port_service.port) not in shodan.settings['Match_On_Ports']:
				continue
		if len(shodan.settings['Filter_Out_Ports']) > 0:
			if int(port_service.port) in shodan.settings['Filter_Out_Ports']:
				continue
		print("* %s " % port_service.as_string())
		if "ssh" in port_service._json:
			print("- SSH service present")

		if shodan.settings['Out_Service_Data']:
			serv_data = port_service._json['data'].split('\n')
			# clean up empty lines & prefix each line with '[*] '
			serv_data = ["[*] %s" % l for l in serv_data if len(l) > 0 ]
			print('\n'.join(serv_data))
			
		if shodan.settings['Out_Service_Module']:
			if "_shodan" in port_service._json and "module" in port_service._json["_shodan"]:
				serv_module = port_service._json["_shodan"]["module"]
				if serv_module in port_service._json:
					serv_data = json.dumps(port_service._json[serv_module], indent=4).split('\n')
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
		print("Shodan API not available, please run 'shodan init <api-key>'")

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
		#print(shodan.get_cache())
		#if shodan.cache_data is not None and args.out_data:
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
	parser.add_argument('-fp', '--filter-ports', dest='filter_out_ports', help='Filter out ports, comma separated list')

	args = parser.parse_args()
	main(args)
