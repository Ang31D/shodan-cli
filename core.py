import json
import os

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

def get_json_path(json_dict, path):
	json_data = json_dict
	# // TODO:
	# // check that json_dict is of 'dict' type
	field_type = type(json_data).__name__

	if field_type != 'dict':
		return False, None

	path_fields = path.split('.')
	index_of_last_field = len(path_fields)-1

	for i in range(len(path_fields)):
		field = path_fields[i]

		field_exists = field in json_data
		if not field_exists:
			return False, None

		json_data = json_data[field]
		field_type = type(json_data).__name__

		if index_of_last_field == i:
			return True, json_data
	return False, None

class JsonRuleEngine:
	def __init__(self, json_data):
		self._json = json_data
		self._debug = True
		self._rules = []
		self._init_rules()

	def _init_rules(self):
		for json_rule in self._json:
			self._rules.append(JsonRule(json_rule))
	@property
	def rules(self):
		return self._rules

	@staticmethod
	
	@staticmethod
	def json_path_exists(json_dict, path):
		path_exists, path_value = get_json_path(json_dict, path)
		return path_exists

	def match_on_rule(self, json_dict, rule):
		rule_definition = rule._definition
		if self._debug:
			print("[*] Checking requirements for rule '%s'" % rule.name)
		if rule.has_requirements:
			if not self.match_on_rule_requirements(json_dict, rule):
				if self._debug:
					print("[*] Skipping Rule - '%s'!" % rule.name)
				return False
		if self._debug:
			print("[*] Rule '%s' - requirements 'OK'" % rule.name)
		
		if self._debug:
			print("[*] Checking conditions for rule '%s'" % rule.name)
		if rule.has_conditions:
			if not self.match_on_rule_conditions(json_dict, rule):
				print("[!] Rule '%s' - conditions 'NOT OK'" % rule.name)
				return False
		if self._debug:
			print("[*] Rule '%s' - conditions 'OK'" % rule.name)

		return True
	def match_on_rule_requirements(self, json_dict, rule):
		if self._debug:
			print("[*] Rule '%s' - requirement definition '%s'" % (rule.name, rule.enable_on))
		if not rule.has_requirements:
			if self._debug:
				print("[*] Rule '%s' requirements - 'NONE'" % rule.name)
			return True
		
		#enable_on_definitions = rule.enable_on.split(",")
		for enable_on_definition in rule.requirement_definitions:
			condition = JsonCondition.simple_definition(enable_on_definition)
			if self._debug:
				print("[*] JsonCondition.simple_definition: \n%s" % json_prettify(condition._definition))
			else:
				if self._debug:
					print("[*] JsonCondition.simple_definition: %s" % json_minify(condition._definition))

			if not self.match_on_condition(json_dict, condition):
				if self._debug:
					print("[!] Rule '%s' - condition '%s' - 'NOT FULLFILLED'" % (rule.name, enable_on_definition))
				return False
		return True
	def match_on_rule_conditions(self, json_dict, rule):
		if self._debug:
			print("[*] Rule '%s' - conditions definition '%s'" % (rule.name, rule.as_conditions()))
		for rule_condition in rule.conditions:
			if not self.match_on_condition(json_dict, rule_condition):
				if self._debug:
					print("[!] match_on_rule_conditions() : rule condition - 'NOT OK' - %s" % rule_condition.as_string())
				return False
		if self._debug:
			print("[*] match_on_rule_conditions() : rule conditions - 'OK' - %s" % rule_condition.as_string())
		return True

	def match_on_field(self, json_dict, field):
		if self._debug:
			print("[*] Checking conditions for field '%s'" % field.id)
		if field.has_conditions:
			if not self.match_on_field_conditions(json_dict, field):
				if self._debug:
					print("[!] Field '%s' - conditions 'NOT OK'" % field.id)
				return False
		if self._debug:
			print("[*] Field '%s' - conditions 'OK'" % field.id)
		return True
	def match_on_field_conditions(self, json_dict, field):
		if self._debug:
			print("[*] Field '%s' - conditions definition '%s'" % (field.id, field.as_conditions()))
		for field_condition in field.conditions:
			if not self.match_on_condition(json_dict, field_condition):
				if self._debug:
					print("[!] match_on_field_conditions() : field condition - 'NOT OK' - %s" % field_condition.as_string())
				return False
		if self._debug:
			print("[*] match_on_field_conditions() : field conditions - 'OK' - %s" % field_condition.as_string())
		return True

	def match_on_conditions(self, json_dict, conditions):
		for condition in conditions:
			if not self.match_on_condition(json_dict, condition):
				if self._debug:
					print("[!] match_on_conditions() : condition 'NOT OK' - %s" % condition.as_string())
				return False
		return True
	def match_on_condition(self, json_dict, condition):
		if self._debug:
			if condition.derived_from_simple:
				if self._debug:
					print("[*] match_on_condition() : checking condition '%s' (loose match: %s) # derived from simple definition" % (condition.as_string(), str(condition.loose_match).lower()))
			else:
				if self._debug:
					print("[*] match_on_condition() : checking condition '%s' (loose match: %s)" % (condition.as_string(), str(condition.loose_match).lower()))

		if not condition.definition_is_valid:
			if self._debug:
				print("[!] match_on_condition() : invalid definition - condition (%s)" % condition.as_string())
			return False
		if condition.is_simple_compare:
			if self.match_on_simple_condition(json_dict, condition):
				if self._debug:
					print("[*] match_on_condition() : condition '%s' (type: simple) 'OK'" % condition.as_string())
				return True
			if self._debug:
				print("[!] match_on_condition() : condition '%s' (type: simple) 'NOT OK'" % condition.as_string())
		elif condition.is_complex_compare:
			if self.match_on_complex_condition(json_dict, condition):
				if self._debug:
					print("[*] match_on_condition() : condition '%s' (type: complex) 'OK'" % condition.as_string())
				return True
			if self._debug:
				print("[!] match_on_condition() : condition '%s' (type: complex) 'NOT OK'" % condition.as_string())
		else:
			if self._debug:
				print("[!] match_on_condition() : condition '%s' (type: unknown) 'NOT OK'" % condition.as_string())
		return False

	def match_on_simple_condition(self, json_dict, condition):
		path_exists, path_value = get_json_path(json_dict, condition.path)

		if condition.COMPARE_EXISTS == condition.compare:
			if condition.is_negate:
				return not path_exists
			return path_exists
		if condition.COMPARE_IS_NULL == condition.compare:
			if condition.is_negate:
				return path_value is not None
			return path_value is None

		if condition.COMPARE_NO_VALUE == condition.compare:
			if path_value is None:
				if condition.is_negate:
					return False
				return True
			
			path_type = type(path_value).__name__
			if (path_type == "str" or path_type == "list") and len(path_value) == 0:
				if condition.is_negate:
					return False
				return True
			elif path_type == "dict":
				if len(path_value.keys()) == 0:
					if condition.is_negate:
						return False
					return True
				#else:
				#	return True
			return False
		if condition.COMPARE_HAS_VALUE:
			if path_value is not None:
				path_type = type(path_value).__name__
				if (path_type == "str" or path_type == "list") and len(path_value) > 0:
					if condition.is_negate:
						return False
					return True
				elif path_type == "dict":
					if len(path_value.keys()) > 0:
						if condition.is_negate:
							return False
						return True
				return True
			return False

		return False
	def match_on_complex_condition(self, json_dict, condition):
		if not condition.has_multi_values:
			if not self.match_on_complex_condition_value(json_dict, condition, condition.match_on):
				return False
			return True
		else:
			for match_on_value in condition.match_on:
				if self.match_on_complex_condition_value(json_dict, condition, match_on_value):
					if self._debug:
						print("[*] match_on_complex_condition() : condition match '%s' 'OK' - %s" % (match_on_value, condition.as_string()))
					return True
			return False
	def match_on_complex_condition_value(self, json_dict, condition, match_on_value):
		path_exists, path_value = get_json_path(json_dict, condition.path)

		path_type = type(path_value).__name__
		if path_type == "NoneType" or path_value is None:
			path_type = "null"
		elif path_type == "bool":
			if field_condition.startswith("value="):
				if path_value:
					path_value = "true"
				else:
					path_value = "false"
				#path_type = str(path_value).lower()

		if not path_exists:
			return False

		match_on_type = type(match_on_value).__name__
		if condition.COMPARE_TYPE == condition.compare:
			if path_type == match_on_type:
				if condition.is_negate:
					return False
				return True
			else:
				if condition.is_negate:
					return True
				return False
		
		if condition.COMPARE_EQUALS == condition.compare or condition.COMPARE_VALUE == condition.compare:
			if path_value is not None and match_on_value == "null":
				if condition.is_negate:
					return False
				return True
			
			if (match_on_value == "null" or len(match_on_value) == 0) and ("str" == path_type or "list" == path_type):
				if len(path_value) == 0:
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if path_value is not None and path_value == match_on_value:
				if condition.is_negate:
					return False
				return True

		if condition.COMPARE_CONTAINS == condition.compare or condition.COMPARE_HAS == condition.compare:
			if path_value is None:
				if condition.is_negate:
					return True
				return False
			
			if "str" == path_type or "list" == path_type:
				if match_on_value in path_value:
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if "dict" == path_type:
				if len(path_value.keys()) == 0:
					if condition.is_negate:
						return True
					return False
				if len(path_value.keys()) > 0:
					if match_on_value in path_value.keys():
						if condition.is_negate:
							return False
						return True
					else:
						if condition.is_negate:
							return True
						return False
			return False

		if condition.COMPARE_STARTS == condition.compare or condition.COMPARE_BEGINS == condition.compare:
			if path_value is None:
				if condition.is_negate:
					return True
				return False

			if "str" == path_type:
				if path_value.startswith(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if "list" == path_type:
				if len(path_value) == 0:
					if condition.is_negate:
						return True
					return False
				if len(path_value) > 0:
					item_value = path_value[0]
					item_type = type(item_value).__name__
					if "str" == item_type:
						if item_value == match_on_value:
							if condition.is_negate:
								return False
							return True
						else:
							if condition.is_negate:
								return True
							return False

		if condition.COMPARE_ENDS == condition.compare:
			if path_value is None:
				if condition.is_negate:
					return True
				return False

			if "str" == path_type:
				if path_value.endswith(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if "list" == path_type:
				if len(path_value) == 0:
					if condition.is_negate:
						return True
					return False
				if len(path_value) > 0:
					item_value = path_value[-1]
					item_type = type(item_value).__name__
					if "str" == item_type:
						if item_value == match_on_value:
							if condition.is_negate:
								return False
							return True
						else:
							if condition.is_negate:
								return True
							return False

		if condition.COMPARE_LEN == condition.compare:
			if match_on_value is None or ("str" != match_on_type or "int" != match_on_type):
				return False
			if "str" == match_on_type or not match_on_value.isnumeric():
				return False

			if path_value is not None:
				if condition.is_negate:
					return True
			
			if "str" == path_type or "list" == path_type:
				if len(path_value) == int(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if "int" == path_type:
				if path_value == int(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False


		if condition.COMPARE_MIN_LEN == condition.compare:
			if path_value is None:
				if condition.is_negate:
					return True

			if match_on_value is None or ("str" != match_on_type and "int" != match_on_type):
				return False
			if "str" == match_on_type and not match_on_value.isnumeric():
				return False


			if "str" == path_type or "list" == path_type:
				if len(path_value) >= int(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if "int" == path_type:
				if path_value >= int(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False

		if condition.COMPARE_MAX_LEN == condition.compare:
			if match_on_value is None or ("str" != match_on_type and "int" != match_on_type):
				return False
			if "str" == match_on_type or not match_on_value.isnumeric():
				return False

			if path_value is not None:
				if condition.is_negate:
					return True

			if "str" == path_type or "list" == path_type:
				if len(path_value) <= int(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False
			if "int" == path_type:
				if path_value <= int(match_on_value):
					if condition.is_negate:
						return False
					return True
				else:
					if condition.is_negate:
						return True
					return False

		return False

class JsonRule:
	def __init__(self, json_rule):
		self._definition = json_rule
		self._conditions = []
		self._fields = []
		self._init_conditions()
		self._init_fields()

	def _init_conditions(self):
		if "conditions" in self._definition:
			for json_condition in self._definition["conditions"]:
				self._conditions.append(JsonCondition(json_condition))
	def _init_fields(self):
		fields = self._definition["fields"]
		for field in fields:
			self._fields.append(ConditionalField(field))

	@staticmethod
	def template_definition():
		definition_json_string = """
		{
  "name": null,
  "description": null,
  "owner": {
    "researcher": null,
    "company": null
  },
  "enable_on": null,
  "conditions": []
}
		"""
		return json.loads(definition_json_string)

	@property
	def name(self):
		if "name" in self._definition:
			return self._definition["name"]
		return ""
	@property
	def description(self):
		if "description" in self._definition:
			return self._definition["description"]
		return ""
	@property
	def owner(self):
		if "owner" in self._definition:
			return self._definition["owner"]
		return ""
	@property
	def conditions(self):
		return self._conditions
	
	@property
	def enable_on(self):
		if "enable_on" in self._definition:
			return self._definition["enable_on"]
		return None
	@property
	def fields(self):
		return self._fields
	@property
	def requirement_definitions(self):
		if self.enable_on is None:
			return []
		return self.enable_on.split(",")
	def as_conditions(self):
		definitions = []
		for condition in self.conditions:
			definitions.append(condition.as_string())
		return ','.join(definitions)

	@property
	def has_requirements(self):
		if self.enable_on is None:
			return False
		elif('str' == type(self.enable_on).__name__ and len(self.enable_on) == 0):
			return False
		return True
	@property
	def has_conditions(self):
		if len(self.conditions) > 0:
			return True

class JsonCondition:
	COMPARE_INVALID = "[INVALID]"
	# // simple comparison conditions
	COMPARE_EXISTS = "exists"
	COMPARE_HAS_VALUE = "has-value"
	COMPARE_NO_VALUE = "no-value"
	COMPARE_IS_NULL = "is-null"
	# // simple complex conditions
	COMPARE_EQUALS = "equals"
	COMPARE_VALUE = "value" # same as COMPARE_EQUALS
	COMPARE_TYPE = "type"
	COMPARE_CONTAINS = "contains" # contains in string or list
	COMPARE_HAS = "has" # same as COMPARE_CONTAINS
	COMPARE_STARTS = "starts"
	COMPARE_BEGINS = "begins" # same as COMPARE_STARTS
	COMPARE_ENDS = "ends"
	COMPARE_LEN = "len"
	COMPARE_MIN_LEN = "min-len"
	COMPARE_MAX_LEN = "max-len"
	def __init__(self, json_condition):
		self._definition = json_condition
		self._compare = self.COMPARE_INVALID
		self._is_negate = False
		self._init_compare_and_negate()

	def _init_compare_and_negate(self):
		_compare = self._get_definition("compare")
		if _compare is not None:
			if _compare.startswith("!"):
				_compare = _compare[1:]
				self._is_negate = True
			elif _compare.startswith("not-"):
				_compare = _compare[4:]
				self._is_negate = True
			self._compare = _compare
		else:
			self._compare = self.COMPARE_EXISTS

	@property
	def is_negate(self):
		return self._is_negate
	@staticmethod
	def template_definition():
		definition_json_string = """
		    {
      "path": null,
      "compare": null,
      "match_on": null,
      "loose_match": true,
      "_definition": null
    }
		"""
		return json.loads(definition_json_string)
	@staticmethod
	def simple_definition(definition):
		condition_json = JsonCondition.template_definition()
		condition_json["_definition"] = definition

		# // '<path>=<match_on>' translates to '<path>:<COMPARE_EQUALS>=<match_on>'
		if ':' not in condition_json["_definition"] and '=' in condition_json["_definition"]:
			path = definition.split('=')[0].strip()
			match_on = definition.split('=')[1].strip()
			condition_json["_definition"] = "%s:%s=%s" % (path, JsonCondition.COMPARE_EQUALS, match_on)
			definition = condition_json["_definition"]
		# // '<path>' translates to '<path>:<COMPARE_EXISTS>'
		if ':' not in condition_json["_definition"]:
			condition_json["_definition"] = "%s:%s" % (condition_json["_definition"], JsonCondition.COMPARE_EXISTS)
			definition = condition_json["_definition"]

		if ':' in definition and len(definition.split(':')) == 2:
			condition_json["path"] = definition.split(':')[0].strip().lower()
			match_condition = definition.split(':')[1].strip().lower()
			if len(match_condition) > 0:
				if '=' in match_condition:
					condition_json["compare"] = match_condition.split('=')[0].strip().lower()
					condition_json["match_on"] = match_condition.split('=')[1].strip().lower()
				else:
					condition_json["compare"] = match_condition.split('=')[0].strip().lower()
		return JsonCondition(condition_json)

	@property
	def path(self):
		return self._get_definition("path")
	@property
	def compare(self):
		return self._compare
	@property
	def match_on(self):
		if self.has_multi_values:
			return self._get_definition("match_on").split("|")
		return self._get_definition("match_on")
	@property
	def has_multi_values(self):
		match_on = self._get_definition("match_on")
		if match_on is not None and "|" in match_on:
			return True
		return False
	@property
	def loose_match(self):
		# true for case insensitive, false for case sensitive
		return self._get_definition("loose_match")
	def _get_definition(self, name):
		if name in self._definition:
			return self._definition[name]
		return None

	@property
	def is_simple_compare(self):
		if self.COMPARE_EXISTS == self.compare:
			return True
		if self.COMPARE_HAS_VALUE == self.compare:
			return True
		if self.COMPARE_NO_VALUE == self.compare:
			return True
		if self.COMPARE_IS_NULL == self.compare:
			return True
		return False
	@property
	def is_complex_compare(self):
		if self.COMPARE_EQUALS == self.compare:
			return True
		if self.COMPARE_VALUE == self.compare:
			return True
		if self.COMPARE_TYPE == self.compare:
			return True
		if self.COMPARE_CONTAINS == self.compare:
			return True
		if self.COMPARE_HAS == self.compare:
			return True
		if self.COMPARE_STARTS == self.compare:
			return True
		if self.COMPARE_BEGINS == self.compare:
			return True
		if self.COMPARE_ENDS == self.compare:
			return True
		if self.COMPARE_LEN == self.compare:
			return True
		if self.COMPARE_MIN_LEN == self.compare:
			return True
		if self.COMPARE_MAX_LEN == self.compare:
			return True
		return False

	@property
	def derived_from_simple(self):
		if "_definition" in self._definition:
			return True
		return False
	def as_string(self):
		definition_string = self.path
		definition_string = "%s:%s" % (definition_string, self.compare)
		match_on = self.match_on
		if match_on is not None:
			definition_string = "%s=%s" % (definition_string, match_on)
		return definition_string
	#def as_definition(self):
	#	definition_string = self.path
	#	definition_string = "%s:%s" % (definition_string, self.compare)
	#	match_on = self.match_on
	#	if self.match_on is not None:
	#		definition_string = "%s=%s" % (definition_string, self.match_on)
	#	return definition_string
	
	@property
	def definition_is_valid(self):
		# // required fields
		if self.path is None or self.compare is None:
			return False
		#// unknown compare definition
		if not self.is_simple_compare and not self.is_complex_compare:
			return False

		return True
class ConditionalField:
	def __init__(self, json_field):
		self._json = json_field
		self._id = self._json["id"]
		self._text = self._json["text"]
		self._path = self._json["path"]
		self._conditions = []
		self._init_condition()

	def _init_condition(self):
		for condition_definition in self._json["condition"].split(","):
			#self._conditions.append(JsonCondition(condition))
			condition = JsonCondition.simple_definition(condition_definition)
			self._conditions.append(condition)

	def as_conditions(self):
		definitions = []
		for condition in self.conditions:
			definitions.append(condition.as_string())
		return ','.join(definitions)
	
	def get_json(self, json_data):
		path_exists, path_value = get_json_path(json_data, self.path)
		if path_exists is not None:
			return path_value
		return None

	@property
	def id(self):
		return self._id
	@property
	def text(self):
		return self._text
	@property
	def path(self):
		return self._path
	@property
	def conditions(self):
		return self._conditions

	@property
	def has_conditions(self):
		if len(self.conditions) > 0:
			return True
		"""
"id": "shodan.id",
"text": "Shodan - ID:",
"path": "http.title",
"condition": "http.title:exists,http.title:min-len=1"
		"""

def get_json_from_file(file_path):
	if os.path.isfile(file_path):
		with open(file_path, 'r') as f:
			return json.load(f)
	return None
def get_dummy_json_rules():
	json_string = """
[
  {
    "name": "shodan-http-module",
    "description": "match on http module for shodan host",
    "owner": {
      "researcher": "Kim Bokholm",
      "company": "NTT Security"
    },
    "enable_on": "_shodan.id=79bf4931-f2b5-4fb1-8c7e-2c44c1066307",
    "conditions": [
      {
        "path": "_shodan.module",
        "compare": "exists",
        "match_on": null,
        "loose_match": true
      },
      {
        "path": "_shodan.module",
        "compare": "equals",
        "match_on": "http|https",
        "loose_match": true
      }
    ],
    "fields": [
      {
        "id": "shodan.id",
        "text": "Shodan - ID",
        "path": "_shodan.id",
        "condition": "_shodan.id"
      },
      {
        "id": "http.page.title",
        "text": "Page Title",
        "path": "http.title",
        "condition": "http.title:exists,http.title:min-len=1"
      },
      {
        "id": "http.response.header.host",
        "text": "'Host' Header",
        "path": "http.host",
        "condition": "http.host:exists,http.host:min-len=1"
      }
    ]
  }
]
"""
#"match_on": "http|https"
#"enable_on": "_shodan:exists=module",
#"enable_on": "_shodan:exists=module,_shodan.module:equals=http|https",
#"enable_on": "_shodan:exists=module,_shodan.module:begins=http",
	return json.loads(json_string)

def main(args):
	#data_dir = "/home/bob104/tools/shodan-cli/shodan-data"
	data_dir = "/home/angeld/Workspace/coding/shodan-py/shodan-data"
	target = "91.195.240.94"
	json_file = "host.%s.json" % target
	file_path = os.path.join(data_dir, json_file)
	if not os.path.isfile(file_path):
		print("ERROR - Missing file '%s'" % file_path)
		return

	json_data = get_json_from_file(file_path)
	json_rules = get_dummy_json_rules()

	engine = JsonRuleEngine(json_rules)
	engine._debug = args.debug_mode
	for rule in engine.rules:
		break
		print("Rule: %s (by: %s / %s)\n\t%s" % (rule.name, rule.owner["researcher"], rule.owner["company"], rule.description))
		if engine._debug:
			filler = "*" * int(((39 * 2 - len("rule definition")-1) / 2))
			print("%s rule definition %s" % (filler, filler))
			print(json_prettify(rule._definition))
			print("%s" % ("*" * 39 * 2))

		#for condition in rule.conditions:
		#	print("definition: %s" % condition._definition)
		#	if condition.match_on is None:
		#		print("skipping match on value")

	print("")
	json_services = json_data["data"]
	for json_service in json_services:
		#print(json_prettify(json_service))
		if not engine.match_on_rule(json_service, engine.rules[0]):
			if engine._debug:
				print("[*] Rule '%s' - match 'NOT OK'" % rule.name)
			continue
		#if engine._debug:
		#	print("[*] Rule '%s' - match 'OK'" % rule.name)
		print("Rule: %s (by: %s / %s)\n\t%s" % (rule.name, rule.owner["researcher"], rule.owner["company"], rule.description))
		filler = "*" * int(((39 * 2 - len("rule definition")-1) / 2))
		print("%s rule definition %s" % (filler, filler))
		print(json_prettify(rule._definition))
		print("%s" % ("*" * 39 * 2))

		found_match = False
		for field in rule.fields:
			if engine._debug:
				print("")
				print("field id: %s, path: %s, condition: %s" % (field.id, field.path, field.as_conditions()))
			if engine.match_on_field(json_service, field):
				#print("field id: %s, path: %s, text: '%s'" % (field.id, field.path, field.text))
				found_match = True
				if engine._debug:
					print("[*] Field '%s' - match 'OK'" % field.id)
				field_value = field.get_json(json_service)
				if field_value is not None:
					print("%s: %s" % (field.text, field_value))
				#print(field_value)
			else:
				if engine._debug:
					print("[*] Skipping Field - '%s' with condition '%s'!" % (field.id, field.as_conditions()))
			#break
		if found_match:
			break

		#break
	return
	#print(json.dumps(engine._json))
	#data = json.dumps(engine._json, indent=4)
	#print(data)
	#json_rule = JsonRule.template_definition()
	#print("")
	#print(json.dumps(json_rule, indent=4))
	print("")
	print("")
	print("")
	print("")
	service_count = 0
	stop_at = 3
	for service_json in json_services:
		service_count += 1
		for rule in engine.rules:
			if not engine.match_on_rule_requirements(service_json, rule):
				continue
			if not engine.match_on_rule(service_json, rule):
				continue
			print("[*] Rule '%s' - match 'OK'" % rule.name)
		if service_count == stop_at:
			break


if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Test - Json Rule Engine")
	parser.add_argument('-d', '--debug', dest='debug_mode', action='store_true', help="Enabled debug mode")
	args = parser.parse_args()
	main(args)
