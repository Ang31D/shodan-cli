# shodan-cli

Extract interesting information regarding a host from shodan using the host api.
<br>
<br>
The python script `shodan-cli.py` utilizes the shodan api ([https://shodan.readthedocs.io/](https://shodan.readthedocs.io/)) to fetch (cache down) host information scanned by shodan.
<br>
We can choose to fetch all historical data for the host or just the latest scan. From there we, filter and show host services information.
<br>
<br>
The python script `core.py` is a poc to detect content in json files based on rule condition(s) and to show templated output based on matched conditions.
<br>
<br>
Sample hosts from shodan `91.195.240.94` , `198.98.62.253`, `188.166.148.225`

## usage

```
Shodan Cli in python

options:
  -h, --help            show this help message and exit
  --api-info            Output API info and exit, use '-v' for verbose output
  --account-profile     Output Shodan Account Profile info and exit, use '-v' for verbose output
  -t TARGET             Host or IP address (or cache index) of the target to lookup
  -c, --cache           Use cached data if exists or re-cache if '-O' is not specified.
  -L, --list-cache      List cached hosts and exit. Use '-F' to re-cache, use '-t' for specific target
  --cache-dir <path>    define custom cache directory, default './shodan-data'
  -H, --history         Include host history
                        
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
  -mc <condition>, --match-json <condition>
                        Match on json condition; syntax '<json-path>:<condition>', supports comma-separated list
                        supported conditions:
                        - match on 'json path': exists, not-exists
                        - match on 'value': equals, not-equals, contains (has), not-contains, has-value, no-value, not-null
                        - match on 'type': type=<type>, not-type=<type>
                        - match on 'length': len=<length>, not-len=<length>, min-len=<length>, max-len=<length>
                        
  --sort-date           Output services by scan date
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
  --host-only           Only output host information, skip port/service information
                        
  -cf <condition>, --custom-field <condition>
                        Output field based on condition, see '-mc' for syntax
  -n, --no-dns          Never do DNS resolution/Always resolve
  --hide-hostname       Hide hostnames and domains from overview
  -v, --verbose         Enabled verbose mode
  --debug               Enabled debug mode
```
