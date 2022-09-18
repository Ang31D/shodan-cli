import argparse
from collections import OrderedDict
import os
import json
from datetime import datetime, date, timezone

def json_prettify(json_data):
	json_type = type(json_data).__name__
	if "dict" == json_type:
		return json.dumps(json_data, indent=4)
	if "str" == json_type:
		return json.dumps(json.loads(json_data), indent=4)
	return json_data
def json_minify(json_data):
	json_type = type(json_data).__name__
	if "dict" == json_type:
		return json.dumps(json_data)
	if "str" == json_type:
		return json.dumps(json.loads(json_data))
	return json_data

def host_template_definition():
	definition_json_string = """
	{
		"region_code": "",
		"tags": [],
		"ip": null,
		"area_code": null,
		"domains": [],
		"hostnames": [],
		"country_code": "",
		"org": "",
		"data": [],
		"asn": "",
		"city": "",
		"latitude": null,
		"isp": "",
		"longitude": null,
		"last_update": "",
		"country_name": "",
		"ip_str": "",
		"os": null,
		"ports": []
	}
	"""
	return json.loads(definition_json_string)

def define_host_by_service(service_json):
	host_json = host_template_definition()

	host_json["ip_str"] = service_json["ip_str"]
	host_json["last_update"] = service_json["timestamp"]
	host_json["ip"] = '' if 'ip' not in service_json else service_json['ip']
	host_json["org"] = '' if 'org' not in service_json else service_json['org']
	host_json["asn"] = '' if 'asn' not in service_json else service_json['asn']
	host_json["isp"] = '' if 'isp' not in service_json else service_json['isp']

	if "location" in service_json:
		host_json["region_code"] = '' if 'region_code' not in service_json["location"] else service_json["location"]['region_code']
		host_json["area_code"] = '' if 'area_code' not in service_json["location"] else service_json["location"]['area_code']
		host_json["country_code"] = '' if 'country_code' not in service_json["location"] else service_json["location"]['country_code']
		host_json["city"] = '' if 'city' not in service_json["location"] else service_json["location"]['city']
		host_json["latitude"] = '' if 'latitude' not in service_json["location"] else service_json["location"]['latitude']
		host_json["longitude"] = '' if 'longitude' not in service_json["location"] else service_json["location"]['longitude']

	#host_json["tags"]: append unique service_json["tags"]
	#host_json["domains"]: append unique service_json["domains"]
	#host_json["hostnames"]: append unique service_json["hostnames"]
	#host_json["ports"]: append unique service_json["port"]
	#host_json["data"]: append service_json

	return host_json

def update_host_by_service(host_json, service_json):
	host_last_update = datetime.strptime(host_json["last_update"], '%Y-%m-%dT%H:%M:%S.%f')
	service_timestamp = datetime.strptime(service_json["timestamp"], '%Y-%m-%dT%H:%M:%S.%f')
	if service_timestamp > host_last_update:
		host_json["last_update"] = service_json["timestamp"]
	if "tags" in service_json:
		for tag in service_json["tags"]:
			if tag not in host_json["tags"]:
				host_json["tags"].append(tag)
	if "domains" in service_json:
		for domain in service_json["domains"]:
			if domain not in host_json["domains"]:
				host_json["domains"].append(domain)
	if "hostnames" in service_json:
		for hostname in service_json["hostnames"]:
			if hostname not in host_json["hostnames"]:
				host_json["hostnames"].append(hostname)
	if "port" in service_json:
		if service_json["port"] not in host_json["ports"]:
			host_json["ports"].append(service_json["port"])
	host_json["data"].append(service_json)
	return host_json
def populate_hosts(file):
	hosts = OrderedDict()

	if not os.path.isfile(file):
		return

	max_lines = 0
	with open(file, "r") as f:
		for i, line in enumerate(f):
			if max_lines != 0 and i >= max_lines:
				break

			service_json = json.loads(line.strip())
			if "ip_str" not in service_json:
				continue

			if service_json["ip_str"] not in hosts:
				hosts[service_json["ip_str"]] = define_host_by_service(service_json)

			host_json = hosts[service_json["ip_str"]]
			host_json = update_host_by_service(host_json, service_json)
			hosts[host_json["ip_str"]] = host_json
	return hosts
def main(args):
	hosts = OrderedDict()

	if not os.path.isfile(args.file):
		return

	hosts = populate_hosts(args.file)
	#print("host.count: %s" % len(hosts))
	max_hosts = 0
	host_index = 0
	for host_ip in hosts:
		if max_hosts != 0 and host_index >= max_hosts:
			break
		host_json = hosts[host_ip]
		#print(host_json)
		print(json_minify(host_json))
		#print(json_prettify(host_json))
		if args.cache_dir is not None:
			out_file = "host.%s.json" % host_ip
			cache_file = os.path.join(args.cache_dir, out_file)
			with open(cache_file, "w") as f:
				f.write(json.dumps(host_json))

		host_index += 1

if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Convert Shodan service results download to host files")

	parser.add_argument('-f', dest='file', help="Input file hosting the service(s) results")
	parser.add_argument('--cache-dir', dest='cache_dir', metavar="<path>", default='shodan-data', help="define custom cache directory to output to, default './shodan-data' in current directory")
	args = parser.parse_args()
	main(args)
