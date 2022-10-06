# shodan-cli

Extract interesting information regarding a host from shodan using the host api.
<br>
<br>
The python script `shodan-cli.py` utilizes the shodan api ([https://shodan.readthedocs.io/](https://shodan.readthedocs.io/)) to fetch (cache down) host information scanned by shodan.
<br>
We can choose to fetch all historical data for the host or just the latest scan. From there we, filter and show host service informations.
<br>
Refer to [https://datapedia.shodan.io/](https://datapedia.shodan.io/) for a description of the different fields.
<br>
<br>
The python script `core.py` is a poc to detect content in json files based on rule condition(s) and to show templated output based on matched conditions.
<br>
<br>
Sample hosts from shodan `91.195.240.94` , `198.98.62.253`, `188.166.148.225`

TODO

Expand arguments for threat rules

`Example`

```
* Cobalt Strike - Malleable C2 Profile
	'cobalt_strike_beacon'
* Potential cobaltstrike - Team Server (default port)
	'port=50050'
* Potential cobaltstrike - Team Server (by known data)
	'data:regex=\u0015\u0003\u0003\u0000\u0002\u0002\n'
* Potential cobaltstrike (http-headers)
	'data:regex=HTTP\/[0-9].[0-9] 404 Not Found\r\n,data:regex=Content-Type. text\/plain\r\n,data:regex=Content-Length. 0\r\n'
* Possible 'Tor' by known jarm hash
	'ssl.jarm=2ad2ad16d2ad2ad00042d42d000000332dc9cd7d90589195193c8bb05d84fa,hash=0'
* Tag: Tor
	'tags:has=tor'
```

Note: we should implement `async` to support callbacks (I think). Never used `async` but think that is what it´s used for.

## usage

```
Shodan Cli in python

options:
  -h, --help            show this help message and exit
  --api-info            Output API info and exit, use '-v' for verbose output
  --account-profile     Output Shodan Account Profile info and exit, use '-v' for verbose output
  -t TARGET             Host or IP address (or cache index) of the target to lookup. Use '-L' to list indexed cached targets (supports cache index range 'n,n-n,n')
  -c, --cache           Use cached data if exists or re-cache if '-O' is not specified.
  -L, --list-cache      List an overview of cached hosts and exit. Use '-F' to re-cache and '-t' for specific target. Use '-v' to list available ports and hostnames of the target.
                        Use '--host-only' to only show hostnames in verbose mode ('-v'), '--hide-hostname' to hide hostnames in verbose mode ('-v')
  -H, --history         Include host history when query shodan or when viewing cached target if available
  --cache-dir <path>    define custom cache directory, default './shodan-data' in current directory
                        
  -mp port[,port,...], --match-ports port[,port,...]
                        Match on port, comma-separated list of ports
  -ms service[,service,...], --match-service service[,service,...]
                        Match on service type, comma-separated list of services (ex. ssh,http,https)
  -mi id[,id,...], --match-shodan-id id[,id,...]
                        Match on shodan id, comma-separated list of IDs
  -mH host[,host,...], --match-hostname host[,host,...]
                        Match on hostname that was used to talk to the service, supports Unix shell-style wildcards. Comma-separated list of hosts
  -mC id[,id,...], --match-crawler id[,id,...]
                        Match on unique ID of the crawler, comma-separated list of crawler id
  -mI id[,id,...], --match-scan-id id[,id,...]
                        Match on unique scan ID that identifies the request that launched the scan, comma-separated list of IDs
  -fp port[,port,...], --filter-port port[,port,...]
                        Filter out port, comma-separated list of ports
  -fs service[,service,...], --filter-service service[,service,...]
                        Filter out service type, comma-separated list of services (ex. ssh,http,https)
  -fH host[,host,...], --filter-hostname host[,host,...]
                        Filter out hostname that was used to talk to the service, supports Unix shell-style wildcards. Comma-separated list of hosts
  -mc [<condition> ...], --match-json [<condition> ...]
                        Match on json condition; syntax '<json-path>[:[negation-operator]<condition>[=<value>]]', supports comma-separated list
                        supported conditions:
                        - 'exists': match if <json-path> exists
                        - 'is-null|null', 'is-empty|no-value', 'has-value': match on value of returned <json-path>
                        - 'is-type|type': match if defined type (<value>) == type of returned <json-path> value
                        - 'equals|value|is': match if <value> == value of returned <json-path>
                        - 'contains': match if value of returned <json-path> contains <value>
                        - 'has': match if <value> == value of returned <json-path> for 'list', 'OrderedDict' & 'dict' (json) 
                        - 'starts|begins', 'ends': match if value of returned <json-path> matches condition of <value> for 'str' & 'int'
                        - 'len', 'min-len', 'max-len': match if length of returned <json-path> matches condition (same length, greater then equal or less then equal) of <value> for 'str', 'int', 'list', 'OrderedDict' & 'dict'
                        - 'gt', 'gte', 'lt', 'lte', 'eq': match if number of returned <json-path> matches condition (greater then, greater equal then, less then, less equal then, equal) of <value>
                        supported conditional negation operators: '!' or 'not-'; when prefixed the condition match on negated condition ('false' as 'true' and vice verse)
                                example: -mc '_shodan:!exists', -mc _shodan.module:not-contains=http
                        default behaviours:
                        - By default match by 'case insensitive', 'case sensitive' match when 'condition' starts with an uppercase letter
                        - Missing condition as '<path>' defaults to '<path>:exists', only negated condition as '<path>:not' defaults to '<path>:not-exists'
                        
  --sort-date           Output services by scan date, default port and scan date
  --head num            output first number of services
  --tail num            output last number of services
  -d, --service-data    Output service details
  -m, --service-module  Output service module data
  --host-json           Output host json
  -sj, --service-json   Output service json
                        
  --time [<datetime range> ...]
                        List cached targets matching range
  --since <date-from>   List cached targets since (before) 'date-from'
  --after <after-date>  List cached targets after the given date, see 'date-format'
  --until <date-to>     List cached targets until 'date-to', from now and up to date
  --before <before-date>
                        List cached targets before 'date-format'
                        
                        supported date-formats:
                        - <year>-<month>-<day> / YYYY-DD-MM, ex 2021-03-20
                        - <number>.<pronom>.ago, ex 2.days.ago, 1.day.ago
                        - Apr 1 2021 / 2 weeks ago / 2.weeks.ago
                        number of Y(ear)(s), M(onth)(s), D(ay)(s), h(our)(s), m/min(s),minute(s), s/sec(s)/second(s)
  -F, --flush-cache     Flush cache from history, use '-t' to re-cache target data
  --rm                  Removes target from the cache
                        
  -cf <condition>, --custom-field <condition>
                        Output field based on condition, see '-mc' for syntax
  --cf-b64              Output field based on condition as base 64 (for safe output)
  -cf-csv <map-format>  Output the result using '-cf' as 'csv' format; format: <json-path>=<as_field_name>[,<json-path>=<as_field_name>,...][:<out_file>]
  -cf-json              Output the service result defined by '-cf' in flatten 'json' format as '{"blob"}: [<json-blob>]'
  -n, --no-dns          Never do DNS resolution/Always resolve
  --host-only           Only output host information, skip port/service information
  --hide-hostname       Hide hostnames and domains from overview
  --hide-vulns          Hide vulns information from overview and json output
  --threat-rule <file>  Tags services based on file with named (tag) defined custom conditions to match, same syntax as for '-mc'
  --threat-only         Filter out services not matching the '--threat-rule' match
  -v, --verbose         Enabled verbose mode
  --debug               Enabled debug mode
```

There are 2 modes `list` and `target`.

- `list`   through the `-L` option will list current hosts in the cache
- `target` through the `-t` option will output the host information and respective services

# service2host.py

We can convert downloaded results where the output is multiple services instead of a host.

getting services related to "tor" based on the following filter:  
`ssl.jarm:"2ad2ad16d2ad2ad00042d42d000000332dc9cd7d90589195193c8bb05d84fa" +hash:0 -ssl:Zoom`

To convert the "service" json as a "host" json we can utilize the "service2host.py" python script.

```
python3 service2host.py -f data/shodan-downloads/daafeb4b-7163-422e-985b-d4fd3bb787dd.json --cache-dir tmp/service_results/shodan-data/
```

This will take the `data/shodan-downloads/daafeb4b-7163-422e-985b-d4fd3bb787dd.json` as input and output the result to the `tmp/service_results/shodan-data/` directory.

We can now refer to the new cache directory holding the new "host" json files.

```
python3 shodan-cli.py -L --cache-dir tmp/service_results/shodan-data/ -n
```

<br>
<p>

If we want to filter the output of the cache we can use the `-mc` options.

```
python3 shodan-cli.py -L --cache-dir tmp/service_results/shodan-data/ -n -mc tags,tags:not-has=tor

python3 shodan-cli.py -L --cache-dir tmp/service_results/shodan-data/ -n -mc tags,tags:not-has=tor  -cf ip_str,tags,hostnames,port,ssl.cert.issuer.CN,ssl.cert.subject.CN
```

<br>
<p>

Output service information in json format by defined json nodes

```
python3 shodan-cli.py -t 20 -H -mc tags:min-len=1,cobalt_strike_beacon -cf _shodan.id,cobalt_strike_beacon.x86 -cf-json --tail 4  | tail -n 1 | jq -c '.blob | .[]'  | jq -s '.[0:2]'
python3 shodan-cli.py -t 20 -mc tags:min-len=1 -cf _shodan.id,ip_str,port,transport,product,tags -cf-json  | tail -n 1 | jq -c '.blob |.[]'
python3 shodan-cli.py -t 20 -mc tags:min-len=1 -cf _shodan.id,ip_str,port,transport,product,tags,data -cf-json -ms http,https  | tail -n 1 | jq '.blob'
```

example output

```bash
python3 shodan-cli.py -t 20 -mc tags:min-len=1 -cf _shodan.id,ip_str,port,transport,product,tags -cf-json  | tail -n 1 | jq -c '.blob |.[]'
```

```json
{"_shodan.id":"57e15f6e-e281-4b63-bfb6-a443e1587414","ip_str":"188.166.148.225","port":22,"product":"OpenSSH","tags":["cloud"],"transport":"tcp"}
{"_shodan.id":"fe639143-d432-4c3a-a5ed-829219322542","ip_str":"188.166.148.225","port":80,"product":"Apache httpd","tags":["cloud"],"transport":"tcp"}
{"_shodan.id":"a5138666-8a08-4689-817c-997169dbb60a","ip_str":"188.166.148.225","port":443,"product":"Cobalt Strike Beacon","tags":["cloud"],"transport":"tcp"}
{"_shodan.id":"9e71e5c4-88e4-4e52-97cc-dbf92cc21191","ip_str":"188.166.148.225","port":50050,"product":null,"tags":["cloud"],"transport":"tcp"}
```
	
example output 2

```bash
python3 shodan-cli.py -t 20 -mc tags:min-len=1 -cf _shodan.id,ip_str,port,transport,product,tags,data -cf-json -ms http,https  | tail -n 1 | jq '.blob'
```

```json
[
  {
    "_shodan.id": "fe639143-d432-4c3a-a5ed-829219322542",
    "data": "HTTP/1.1 200 OK\r\nDate: Sat, 17 Sep 2022 03:58:48 GMT\r\nServer: Apache/2.4.54 (Debian)\r\nLast-Modified: Sun, 30 Jan 2022 20:50:15 GMT\r\nETag: \"29cd-5d6d2d09dd9b0\"\r\nAccept-Ranges: bytes\r\nContent-Length: 10701\r\nVary: Accept-Encoding\r\nContent-Type: text/html\r\n\r\n",
    "ip_str": "188.166.148.225",
    "port": 80,
    "product": "Apache httpd",
    "tags": [
      "cloud"
    ],
    "transport": "tcp"
  },
  {
    "_shodan.id": "a5138666-8a08-4689-817c-997169dbb60a",
    "data": "HTTP/1.1 404 Not Found\r\nDate: Sat, 17 Sep 2022 04:45:00 GMT\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n\nCobalt Strike Beacon:\n  x86:\n    beacon_type: HTTPS\n    dns-beacon.strategy_fail_seconds: -1\n    dns-beacon.strategy_fail_x: -1\n    dns-beacon.strategy_rotate_seconds: -1\n    http-get.client:\n      Accept: */*\n      Host: www.amazon.com\n      session-token=\n      skin=noskin;\n      csm-hit=s-24KU11BB82RZSYGJ3BDK|1419899012996\n      Cookie\n    http-get.uri: remote.nedsecures.co.za,/s/ref=nb_sb_noss_1/167-3294888-0262949/field-keywords=books\n    http-get.verb: GET\n    http-post.client:\n      Accept: */*\n      Content-Type: text/xml\n      X-Requested-With: XMLHttpRequest\n      Host: www.amazon.com\n      sz=160x600\n      oe=oe=ISO-8859-1;\n      sn\n      s=3717\n      dc_ref=http%3A%2F%2Fwww.amazon.com\n    http-post.uri: /N4215/adj/amzn.us.sr.aps\n    http-post.verb: POST\n    maxgetsize: 1048576\n    port: 443\n    post-ex.spawnto_x64: %windir%\\sysnative\\rundll32.exe\n    post-ex.spawnto_x86: %windir%\\syswow64\\rundll32.exe\n    process-inject.execute:\n      CreateThread\n      SetThreadContext\n      CreateRemoteThread\n      RtlCreateUserThread\n    process-inject.startrwx: 64\n    process-inject.stub: 04e0a11be59147a8d73d2b3e9fea832c\n    process-inject.userwx: 64\n    proxy.behavior: 2 (Use IE settings)\n    server.publickey_md5: 108413980eba83aa8da7c9af94eb7e4e\n    sleeptime: 5000\n    useragent_header: Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko\n    uses_cookies: 1\n    watermark: 1996647057\n  x64:\n    beacon_type: HTTPS\n    dns-beacon.strategy_fail_seconds: -1\n    dns-beacon.strategy_fail_x: -1\n    dns-beacon.strategy_rotate_seconds: -1\n    http-get.client:\n      Accept: */*\n      Host: www.amazon.com\n      session-token=\n      skin=noskin;\n      csm-hit=s-24KU11BB82RZSYGJ3BDK|1419899012996\n      Cookie\n    http-get.uri: remote.nedsecures.co.za,/s/ref=nb_sb_noss_1/167-3294888-0262949/field-keywords=books\n    http-get.verb: GET\n    http-post.client:\n      Accept: */*\n      Content-Type: text/xml\n      X-Requested-With: XMLHttpRequest\n      Host: www.amazon.com\n      sz=160x600\n      oe=oe=ISO-8859-1;\n      sn\n      s=3717\n      dc_ref=http%3A%2F%2Fwww.amazon.com\n    http-post.uri: /N4215/adj/amzn.us.sr.aps\n    http-post.verb: POST\n    maxgetsize: 1048576\n    port: 443\n    post-ex.spawnto_x64: %windir%\\sysnative\\rundll32.exe\n    post-ex.spawnto_x86: %windir%\\syswow64\\rundll32.exe\n    process-inject.execute:\n      CreateThread\n      SetThreadContext\n      CreateRemoteThread\n      RtlCreateUserThread\n    process-inject.startrwx: 64\n    process-inject.stub: 04e0a11be59147a8d73d2b3e9fea832c\n    process-inject.userwx: 64\n    proxy.behavior: 2 (Use IE settings)\n    server.publickey_md5: 108413980eba83aa8da7c9af94eb7e4e\n    sleeptime: 5000\n    useragent_header: Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko\n    uses_cookies: 1\n    watermark: 1996647057\n",
    "ip_str": "188.166.148.225",
    "port": 443,
    "product": "Cobalt Strike Beacon",
    "tags": [
      "cloud"
    ],
    "transport": "tcp"
  },
  {
    "_shodan.id": "9e71e5c4-88e4-4e52-97cc-dbf92cc21191",
    "data": "\u0015\u0003\u0003\u0000\u0002\u0002\n",
    "ip_str": "188.166.148.225",
    "port": 50050,
    "product": null,
    "tags": [
      "cloud"
    ],
    "transport": "tcp"
  }
]
```

## MISC

`Parse http headers from a host json file`

```bash
cat shodan-data/host.91.193.75.239.json | jq -c '.data | .[] | select(._shodan.module | contains("http")) | select(.data | contains("22:02:51")) | .data' | sed 's/\\r\\n\\r\\n//g' | sed 's/^"//g' | sed 's/"$//g'  | jq -c -R 'split("\\r\\n")[1:]' | jq '.[] | {name: (. | split(": ")[0]), value: (. | split(": ")[1])}' | jq -cs '.[]'
```
```json
{"name":"Server","value":"squid"}
{"name":"Mime-Version","value":"1.0"}
{"name":"Date","value":"Sun, 07 Aug 2022 22:02:51 GMT"}
{"name":"Content-Type","value":"text/html"}
{"name":"Content-Length","value":"3131"}
{"name":"X-Squid-Error","value":"ERR_INVALID_URL 0"}
{"name":"Vary","value":"Accept-Language"}
{"name":"Content-Language","value":"en"}
{"name":"X-Cache","value":"MISS from est"}
{"name":"Via","value":"1.1 est (squid)"}
{"name":"Connection","value":"close"}
```
