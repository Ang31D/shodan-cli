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
		# Setup the Shodan API connection
		self._api = Shodan(get_api_key())

	def lookup_host_ip(self, host_ip, history=False):
		data = self._api.host(host_ip, history=history)
		return data

class ShodanSettings:
	def __init__(self, args):
		self.settings = OrderedDict()
		self.settings['Use_Cache'] = False
		self.settings['Cache_Dir'] = "shodan-data"
		self.settings['Target'] = None
		self.settings['Fetch_History'] = False
		self.settings['Out_Data'] = False
		self.init(args)

	def init(self, args):
		self.settings['Use_Cache'] = args.cache
		if args.cache_dir is not None:
			self.settings['Cache_Dir'] = args.cache_dir

		self.settings['Target'] = args.target
		self.settings['Fetch_History'] = args.fetch_history

		self.settings['Out_Data'] = args.out_data

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
		self.hostnames = json_data['hostnames']
		self.domains = json_data['domains']
		self.country = "%s - %s" % (json_data['country_code'], json_data['country_name'])
		self.city = json_data['city']
		self.geo = "%s, %s (long, lat)" % (json_data['longitude'], json_data['latitude'])
		self.isp = json_data['isp']
		self.org = json_data['org']
class Port_Service:
	def __init__(self, json_data):
		self._json = json_data
		self.port = json_data['port']
		self.transport = json_data['transport']
		#self.product = json_data['product']
		#self.version = json_data['version']
		self.product = '' if 'product' not in json_data else json_data['product']
		self.version = '' if 'version' not in json_data else json_data['version']

def main(args):
	#host = "119.45.94.71"

	shodan = ShodanEx(args)

	if shodan.use_cache:
		# re-cache data
		if not shodan.settings['Out_Data']:
			print('[*] re-caching data...')
			shodan.cache_host_ip()
			return
		# cache data if not exists
		if not shodan.cache_exists:
			print('[*] caching data...')
			shodan.cache_host_ip()
		#print(shodan.get_cache())
		#if shodan.cache_data is not None and args.out_data:
		if shodan.settings['Out_Data']:
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
			print("Ports: %s" % ", ".join([str(int) for int in shodan.host_ports])) # convert int to str
			print("Tags: %s" % ','.join(json_data['tags']))
			host = Shodan_Host(json_data)
			print("Host.ip: %s" % host.ip)
			print("Host.hostnames: %s" % ','.join(host.hostnames))
			print("Host.country: %s" % host.country)
			print("Host.city: %s" % host.city)
			print("Host.geo: %s" % host.geo)
			print("Host.ISP: %s" % host.isp)
			print("Host.Org: %s" % host.org)

			print("Host.Org: %s" % host.org)
			#print(json_data['data'][0])
			port_service = Port_Service(json_data['data'][0])
			print("Host.Service.port: %s/%s - %s # %s" % (port_service.transport.upper(), port_service.port, port_service.product, port_service.version))
			if "ssh" in port_service._json:
				print("SSH service")
				print(json.dumps(port_service._json['ssh'], indent=4, sort_keys=True))
			for json_port in json_data['data']:
				port_service = Port_Service(json_port)
				print("Host.Service.port: %s/%s - %s # %s" % (port_service.transport.upper(), port_service.port, port_service.product, port_service.version))
				#if "cobalt_strike_beacon" in json_port:

if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Shodan Cli in python")

	parser.add_argument('-t', dest='target', required=True, help='Host or IP address of the target to lookup')
	parser.add_argument('-c', '--cache', dest='cache', action='store_true', help="Use cached data if exists or re-cache if '-O' is not specified.")
	parser.add_argument('-C', '--cache-dir', dest='cache_dir', default='shodan-data', help="store cache to directory, default 'shodan-data'")
	parser.add_argument('-H', '--history', dest='fetch_history', action='store_true', help="Fetch host history")
	parser.add_argument('-O', '--out-data', dest='out_data', action='store_true', help="Output data to console")

	args = parser.parse_args()
	main(args)
