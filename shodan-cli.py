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
		self.settings['Cache_Dir'] = "shodan_data"
		self.settings['Target'] = None
		self.settings['Fetch_History'] = False
		self.init(args)

	def init(self, args):
		self.settings['Use_Cache'] = args.use_cache
		if args.cache_dir is not None:
			self.settings['Cache_Dir'] = args.cache_dir

		self.settings['Target'] = args.target
		self.settings['Fetch_History'] = args.fetch_history

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
		return os.path.isfile(self.settings['Cache_File'])

	def get_cache(self):
		if self.cache_data is not None:
			return self.cache_data
		if not self.cache_exists:
			return None
		print("test")

		json_data = None
		with open(cache_file, 'r') as f:
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

def main(args):
	#host = "119.45.94.71"

	shodan = ShodanEx(args)

	if shodan.use_cache:
		if not shodan.cache_exists:
			shodan.cache_host_ip()
		#print(type(shodan.cache_data))
		if shodan.cache_data is not None and args.out_data:
			print(shodan.cache_data)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Shodan Cli in python")

	parser.add_argument('-t', dest='target', required=True, help='Host or IP address of the target to lookup')
	parser.add_argument('-c', '--use-cache', dest='use_cache', action='store_true', help="Use cached data if exists")
	parser.add_argument('-C', '--cache-dir', dest='cache_dir', default='shodan_data', help="store cache to directory, default 'shodan_data'")
	parser.add_argument('-H', '--history', dest='fetch_history', action='store_true', help="Fetch host history")
	parser.add_argument('-O', '--out-data', dest='out_data', action='store_true', help="Output data to console")

	args = parser.parse_args()
	main(args)
