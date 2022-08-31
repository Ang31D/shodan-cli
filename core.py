import json
import os

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
	def get_json_path(self, json_dict, path):
		json_data = json_dict
	
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

	def match_on_rule(self, json_dict, rule):
		print("[match_on_rule] %s" % rule._definition)
		enable_rule_on = rule.enable_on
		if enable_rule_on is not None:
			print("Rule requirement found '%s', checking requirements..." % enable_rule_on)
			
			rule_condition = JsonCondition.simple_definition(enable_rule_on)
			print("JsonCondition.simple_definition: %s" % rule_condition._definition)
			if not self.match_on_condition(json_dict, rule_condition):
				if self._debug:
					print("[*] Skipping Rule '%s'!" % rule.name)
				return False
			print("Rule requirement found '%s', checking requirements..." % enable_rule_on)
			
	def match_on_condition(self, json_dict, condition):
		print("[*] match_on_condition() : checking condition '%s' (loose match: %s) # derived from simple definition '%s'" % (condition.as_string(), str(condition.loose_match).lower(), str(condition.derived_from_simple).lower()))

		if not condition.definition_is_valid:
			if self._debug:
				print("[!] match_on_condition() : invalid path or compare definition (%s), seems to be 'null'" % condition.as_string())
			return False
		pass

	def match_on_conditions(self, json_dict, condition_rules):
		if len(condition_rules) == 0:
			return True

		for custom_condition in condition_rules:
			if ':' in custom_condition and len(custom_condition.split(':')) == 2:
				path = custom_condition.split(':')[0].strip().lower()
				field_condition = custom_condition.split(':')[1].strip().lower()

				if self.match_on_condition_old(service._json, path, field_condition):
					return True
		return False

	#def match_on_condition(self, json_dict, path, field_condition):
	def match_on_condition_old(self, json_dict, condition_rule):
		if ':' not in condition_rule or len(condition_rule.split(':')) != 2:
			return False

		if ':' in condition_rule and len(condition_rule.split(':')) == 2:
			path = condition_rule.split(':')[0].strip().lower()
			field_condition = condition_rule.split(':')[1].strip().lower()

		path_exists, path_value = JsonRuleEngine.get_json_path(json_dict, path)
	
		path_type = type(path_value).__name__
		#if path_type == "NoneType" or path_type is None:
		if path_type == "NoneType" or path_value is None:
			path_type = "null"
		elif path_type == "dict":
			path_type = "json"
		elif path_type == "bool":
			if field_condition.startswith("value="):
				if path_value:
					path_value = "true"
				else:
					path_value = "false"
				#path_type = str(path_value).lower()
		if self._debug:
			print("- match_on_condition() condition '%s:%s', path.exists: %s, data.type: %s" % (path, field_condition, path_exists, path_type))
	
		if field_condition == "exists" or field_condition == "not-exists" or field_condition == "exist" or field_condition == "not-exist":
			if field_condition.startswith("exist") and path_exists:
				return True
			if field_condition.startswith("not-exist") and not path_exists:
				return True
		if field_condition == "has-value" or field_condition == "no-value" or field_condition == "not-null":
			#if (field_condition == "has-value" or field_condition == "not-null") and path_type != "null" and path_type != "bool" and path_value is not None and len(path_value) != 0:
			if (field_condition == "has-value" or field_condition == "not-null") and path_type != "null" and path_type != "bool" and path_value is not None:
				if (path_type == "str" or path_type == "list") and len(path_value) != 0:
					return True
				else:
					return True
			if field_condition == "no-value" and (path_type == "null" or path_value is None or len(path_value) == 0):
				return True
		#if not path_exists:
		#	return False
	
		if field_condition.startswith("equal=") or field_condition.startswith("value=") or field_condition.startswith("not-equal=") or field_condition.startswith("equals=") or field_condition.startswith("not-equals="):
			condition_value = field_condition.split("=")[1]
			if not field_condition.startswith("not-") and condition_value == path_value:
				return True
			if field_condition.startswith("not-") and condition_value != path_value:
				return True
	
		if field_condition.startswith("contains=") or field_condition.startswith("not-contains=") or field_condition.startswith("has=") or field_condition.startswith("not-has="):
			condition_value = field_condition.split("=")[1]
			if not field_condition.startswith("not-") and path_type == "str" and condition_value in path_value.lower():
				return True
			if field_condition.startswith("not-") and path_type == "str" and condition_value not in path_value.lower():
				return True
		if field_condition.startswith("starts=") or field_condition.startswith("not-starts=") or field_condition.startswith("ends=") or field_condition.startswith("not-ends="):
			condition_value = field_condition.split("=")[1]
			if not field_condition.startswith("not-") and path_type == "str" and path_value.lower().startswith(condition_value):
				return True
			if field_condition.startswith("not-") and path_type == "str" and not path_value.lower().startswith(condition_value):
				return True
	
		if field_condition.startswith("type=") or field_condition.startswith("not-type="):
			condition_value = field_condition.split("=")[1]
			if not field_condition.startswith("not-") and condition_value == path_type:
				return True
			if field_condition.startswith("not-") and condition_value != path_type:
				return True
	
		if field_condition.startswith("len=") or field_condition.startswith("not-len=") or field_condition.startswith("min-len=") or field_condition.startswith("max-len="):
			condition_value = field_condition.split("=")[1].strip()
			if self._debug and path_value is not None:
				print("%s(type: %s): %s, data.len: %s" % (field_condition, type(condition_value).__name__, condition_value, len(path_value)))
			if type(condition_value).__name__ == "str" and condition_value.isnumeric():
				condition_value = int(condition_value)
				if field_condition.startswith("len=") and path_type != "null" and len(path_value) == condition_value:
					return True
				if field_condition.startswith("not-len=") and path_type != "null" and len(path_value) != condition_value:
					return True
				if field_condition.startswith("min-len=") and path_type != "null" and len(path_value) >= condition_value:
					return True
				if field_condition.startswith("max-len=") and path_type != "null" and len(path_value) <= condition_value:
					return True
		if self._debug:
			print("***************************************\n%s\n***************************************" % path_value)
		return False

class JsonRule:
	def __init__(self, json_rule):
		self._definition = json_rule
		self._conditions = []
		self._init_conditions()
		#self._condition = JsonCondition(definition)
		#print(type(self._condition).__name__)
	def _init_conditions(self):
		if "conditions" in self._definition:
			for json_condition in self._definition["conditions"]:
				self._conditions.append(JsonCondition(json_condition))
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

class JsonCondition:
	def __init__(self, json_condition):
		self._definition = json_condition
	
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
		if ':' in definition and len(definition.split(':')) == 2:
			condition_json["path"] = definition.split(':')[0].strip().lower()
			match_condition = definition.split(':')[1].strip().lower()
			if len(match_condition) > 0:
				if '=' in match_condition:
					condition_json["compare"] = match_condition.split('=')[0].strip().lower()
					condition_json["match_on"] = match_condition.split('=')[1].strip().lower()
				else:
					condition_json["compare"] = self._condition = match_condition.split('=')[0].strip().lower()
		return JsonCondition(condition_json)

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
			#definition_string = "%s=%s (loose match: %s)" % (definition_string, match_on, str(self.loose_match).lower())
			definition_string = "%s=%s" % (definition_string, match_on)
		return definition_string
	@property
	def definition_is_valid(self):
		# // required fields
		if self.path is None or self.compare is None:
			return False
		valid_compare_without_match_on = ["exists", "not-exists", "exist", "not-exist", "has-value", "no-value", "not-null"]
		if self.compare not in valid_compare_without_match_on:
			return False

		return True
	@property
	def path(self):
		return self._get_definition("path")
	@property
	def compare(self):
		return self._get_definition("compare")
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

	def _init_definition(self):
		if ':' in self._definition and len(self._definition.split(':')) == 2:
			self._json_path = self._definition.split(':')[0].strip().lower()

			match_condition = self._definition.split(':')[1].strip().lower()
			if len(match_condition) == 0:
				return
			if '=' in match_condition:
				self._condition = match_condition.split('=')[0].strip().lower()
				self._match_on = match_condition.split('=')[1].strip().lower()
			else:
				self._condition = match_condition.split('=')[0].strip().lower()

#rule_definition = JsonCondition("_shodan.module:value=http")

def get_json_from_file(file_path):
	if os.path.isfile(file_path):
		with open(file_path, 'r') as f:
			return json.load(f)
	return None
def get_dummy_json_rules():
	json_string = """
[{
  "name": "shodan-http-module",
  "description": "match on http module for shodan host",
  "owner": {
    "researcher": "Kim Bokholm",
    "company": "NTT Security"
  },
  "enable_on": "_shodan:exists=module",
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
  ]
}]
"""
	return json.loads(json_string)

if __name__ == '__main__':
	data_dir = "/home/angeld/Workspace/coding/shodan-py/shodan-data/"
	json_file = "host.91.193.75.239.json"
	file_path = os.path.join(data_dir, json_file)
	
	json_rules = get_dummy_json_rules()

	json_data = get_json_from_file(file_path)

	engine = JsonRuleEngine(json_rules)
	for rule in engine.rules:
		print("Rule: %s (by: %s / %s)\n\t%s" % (rule.name, rule.owner["researcher"], rule.owner["company"], rule.description))
		for condition in rule.conditions:
			print("definition: %s" % condition._definition)
			if condition.match_on is None:
				print("skipping match on value")

	print("")
	#print(json_data)
	#engine.match_on_conditions(json_data)
	print("")
	engine.match_on_rule(json_data, engine.rules[0])
	#print(json.dumps(engine._json))
	#data = json.dumps(engine._json, indent=4)
	#print(data)
	#json_rule = JsonRule.template_definition()
	#print("")
	#print(json.dumps(json_rule, indent=4))
