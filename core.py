import json
import os
from collections import OrderedDict
import re
import hashlib

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
	field_type = type(json_data).__name__

	if field_type != 'dict':
		return False, None

	#if "." not in path and path in json_dict:
	#	return json_dict[path]

	path_fields = path.split('.')
	# // override if '|' is used as path separator instead
	if "|" in path:
		path_fields = path.split('|')
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

		#if field_type != 'dict':
		#	return False, None
	return False, None

def json_path_exists(json_dict, path):
	path_exists, path_value = get_json_path(json_dict, path)
	return path_exists

# // Return a SHA-256 hash of the given string
def hash_string(string):
	return hashlib.sha256(string.encode('utf-8')).hexdigest()

class JsonRuleEngine:
	def __init__(self, json_data):
		self._json = json_data
		self._debug = True
		self._rules = []
		self._init_rules()

	def reset(self):
		self._init_rules()
	def _init_rules(self):
		self._rules = []
		for json_rule in self._json:
			self._rules.append(JsonRule(self, json_rule))
	@property
	def rules(self):
		return self._rules

	def match_on_conditions(self, json_dict, conditions):
		for condition in conditions:
			if not self.match_on_condition(json_dict, condition):
				return False
		return True
	def match_on_condition(self, json_dict, condition):
		if condition.is_extended:
			return self.match_on_extended_conditions(json_dict, condition)

		if self._debug:
			if condition.derived_from_simple:
				if self._debug:
					print("[*] match_on_condition() : checking condition '%s' (loose match: %s) # derived from simple definition" % (condition.as_string(), str(condition.loose_match).lower()))
			else:
				if self._debug:
					print("[*] match_on_condition() : checking condition '%s' (loose match: %s)" % (condition.as_string(), str(condition.loose_match).lower()))

		if not condition.definition_is_valid:
			return False
		if condition.is_simple_compare:
			if self.match_on_simple_condition(json_dict, condition):
				return True
		elif condition.is_complex_compare:
			if self.match_on_complex_condition(json_dict, condition):
				return True
		return False
	def match_on_extended_conditions(self, json_dict, condition):
		if not condition.is_extended:
			return False
		for extended_condition in condition.extended_conditions:
			if not self.match_on_condition(json_dict, extended_condition):
				return False
		return True

	def match_on_simple_condition(self, json_dict, condition):
		path_exists, path_value = get_json_path(json_dict, condition.path)

		if condition.COMPARE_EXISTS == condition.compare:
			if condition.is_negate:
				return not path_exists
			return path_exists
		if condition.COMPARE_IS_NULL == condition.compare or condition.COMPARE_NULL == condition.compare:
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
			return self.match_on_complex_condition_value(json_dict, condition, condition.match_on)
		
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
			if match_on_value == "null" and path_value is not None:
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

			if path_type == "int" and match_on_type == "str" and match_on_value.isnumeric():
				if path_value == int(match_on_value):
					if condition.is_negate:
						return False
					return True

			if path_value is not None and path_value == match_on_value:
				if condition.is_negate:
					return False
				return True

		if condition.COMPARE_CONTAINS == condition.compare or condition.COMPARE_HAS == condition.compare:
			if path_value is None:
				if condition.is_negate:
					return True
				return False
			
			if ("str" == path_type or "list" == path_type) and match_on_value is not None:
				if match_on_value.lower() in path_value.lower():
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

		if condition.COMPARE_REGEX == condition.compare:
			if match_on_value is None or "str" != match_on_type:
				return False
			if path_value is not None:
				if re.match(path_value, string_date):
					return True
				if condition.is_negate:
					return True

		return False
class ReportTemplate:
	def __init__(self, parent, json_template):
		self._parent = parent # JsonRule
		self._definition = json_template
		self._id = self._definition['id']
		self._template_dependency = self._definition['template_dependency']
		self._field_requirement = self._definition['field_requirement']
		self._field_match = []
		self._data = self._definition['data']

	@property
	def id(self):
		return self._id
	@property
	def template_dependency(self):
		return self._template_dependency
	@property
	def field_requirement(self):
		return self._field_requirement
	@property
	def data(self):
		return self._data

	@staticmethod
	def template_definition():
		definition_json_string = """
		    {
      "id": null,
      "template_dependency": null,
      "field_requirement": null,
      "data": []
    }
		"""
	@property
	def has_requirements(self):
		if "str" != type(self.field_requirement).__name__ or len(self.field_requirement) == 0:
			return False
		return True

	def check_requirements(self):
		if not self.has_requirements:
			return True
		for field_id in self.field_requirement.split(","):
			if not self._parent.field_exists(field_id.strip()):
				return False

			field = self._parent.get_field(field_id.strip())
			if field.value is None:
				return False
		return True

	@property
	def has_dependencies(self):
		if "str" != type(self.template_dependency).__name__ or len(self.template_dependency) == 0:
			return False
		return True
	def check_dependencies(self):
		# // no dependencies to evaluate
		if not self.has_dependencies:
			return True
		if self._template_dependency is None or "str" != type(self._template_dependency).__name__ or len(self._template_dependency) == 0:
			return True

class JsonRule:
	def __init__(self, parent, json_rule):
		self._parent = parent # JsonRuleEngine
		self._definition = json_rule
		self._conditions = []
		#self._fields = []
		self._fields = OrderedDict()
		self._data_template = None
		self._data = None
		self._templates = []
		self._init_conditions()
		self._init_fields()
		#self._init_data_template()
		self._init_templates()

	def check_requirements(self, json_data):
		# // no requirements to evaluate
		if not self.has_requirements:
			return True
		for enable_on_definition in self.requirement_definitions:
			condition = JsonCondition.simple_definition(self, enable_on_definition)
			if not self._parent.match_on_condition(json_data, condition):
				return False
		return True

	def check_conditions(self, json_data):
		# // no conditions to evaluate
		if not self.has_conditions:
			return True
		for condition in self.conditions:
			# // any condition evaluated as true is enough
			if self._parent.match_on_condition(json_data, condition):
				return True
		return False

	def _init_templates(self):
		self._templates = []
		if self._definition["templates"] is not None:
			for template in self._definition["templates"]:
				self._templates.append(ReportTemplate(self, template))

	def _init_conditions(self):
		self._conditions = []
		if "conditions" in self._definition:
			for json_condition in self._definition["conditions"]:
				if "_definition" in json_condition:
					pass
				else:
					self._conditions.append(JsonCondition(self, json_condition))
	def _reset_fields(self):
		self._init_fields()
	def _init_fields(self):
		self._fields = OrderedDict()
		fields = self._definition["fields"]
		for field in fields:
			if field['id'] not in self._fields:
				self._fields[field['id']] = ConditionalField(self, field)
	def field_exists(self, field_id):
		return field_id in self.fields
	def get_field(self, field_id):
		if field_id in self.fields:
			return self.fields[field_id]
		return None
	def _init_data_template(self):
		template = self._definition["data"]["template"]
		self._data_template = ''.join(template)

	@staticmethod
	def template_definition():
		definition_json_string = """
		{
  "id": null,
  "name": null,
  "description": null,
  "owner": {
    "researcher": null,
    "company": null
  },
  "enable_on": null,
  "conditions": [],
  "fields": [],
  "data": null
}
		"""
		return json.loads(definition_json_string)

	@property
	def id(self):
		if "id" in self._definition:
			return self._definition["id"]
		return None
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
	def owner_researcher(self):
		if len(self.owner) > 0:
			return self.owner["researcher"]
		return ""
	@property
	def owner_company(self):
		if len(self.owner) > 0:
			return self.owner["company"]
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
	COMPARE_NULL = "null"
	# // simple complex conditions
	COMPARE_IS = "is" # as equals but case sensitive
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
	COMPARE_REGEX = "regex"
	# // add support for gt (>), gte (>=), lt (<), lte (>=), eq (==)
	COMPARE_NUM_GREATER_THEN = "gt"
	COMPARE_NUM_GREATER_THEN_EQUAL = "gte"
	COMPARE_NUM_LESS_THEN = "lt"
	COMPARE_NUM_LESS_THEN_EQUAL = "lte"
	COMPARE_NUM_EQUAL = "eq"
	
	def __init__(self, parent, json_condition):
		self._parent = parent # JsonRule
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
      "_definition": null,
      "_extended": null
    }
		"""
		return json.loads(definition_json_string)
	@staticmethod
	def simple_definition(parent, definition):
		json_condition = JsonCondition.template_definition()
		json_condition["_definition"] = definition

		# // '<path>=<match_on>' translates to '<path>:<COMPARE_EQUALS>=<match_on>'
		if ':' not in json_condition["_definition"] and '=' in json_condition["_definition"]:
			path = definition.split('=')[0].strip()
			match_on = definition.split('=')[1].strip()
			json_condition["_definition"] = "%s:%s=%s" % (path, JsonCondition.COMPARE_EQUALS, match_on)
			definition = json_condition["_definition"]
		# // '<path>' translates to '<path>:<COMPARE_EXISTS>'
		if ':' not in json_condition["_definition"]:
			json_condition["_definition"] = "%s:%s" % (json_condition["_definition"], JsonCondition.COMPARE_EXISTS)
			definition = json_condition["_definition"]

		if ':' in definition and len(definition.split(':')) == 2:
			json_condition["path"] = definition.split(':')[0].strip().lower()
			match_condition = definition.split(':')[1].strip().lower()
			if len(match_condition) > 0:
				if '=' in match_condition:
					json_condition["compare"] = match_condition.split('=')[0].strip().lower()
					json_condition["match_on"] = match_condition.split('=')[1].strip().lower()
				else:
					json_condition["compare"] = match_condition.split('=')[0].strip().lower()
		return JsonCondition(parent, json_condition)

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
	#@property
	#def match_on_type(self):
	#	return type(self.match_on).__name__
	@property
	def has_multi_values(self):
		match_on = self._get_definition("match_on")
		if "str" != type(match_on).__name__:
			return False
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
	def is_extended(self):
		if "_extended" in self._definition and self._definition["_extended"] is not None:
			return True
		return False
	@property
	def extended_conditions(self):
		conditions = []
		if self.is_extended:
			for condition_definition in self._definition["_extended"].split(","):
				conditions.append(JsonCondition.simple_definition(self._parent, condition_definition.strip()))
		return conditions
	@property
	def extended_definitions(self):
		if self.is_extended:
			return self._definition["_extended"]
		return None
	

	@property
	def is_simple_compare(self):
		if self.COMPARE_EXISTS == self.compare:
			return True
		if self.COMPARE_HAS_VALUE == self.compare:
			return True
		if self.COMPARE_NO_VALUE == self.compare:
			return True
		if self.COMPARE_IS_NULL == self.compare or self.COMPARE_NULL == self.compare:
			return True
		return False
	@property
	def is_complex_compare(self):
		if self.COMPARE_IS == self.compare:
			return True
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
		if self.COMPARE_REGEX == self.compare:
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
		# // unknown compare definition
		if not self.is_simple_compare and not self.is_complex_compare:
			return False

		return True
class ConditionalField:
	def __init__(self, parent, json_field):
		self._parent = parent # JsonRule
		self._definition = json_field
		self._id = self._definition["id"]
		self._path = self._definition["path"]
		self._value = None
		self._conditions = []
		self._init_condition()

	def _init_condition(self):
		self._conditions = []
		if len(self._definition["condition"]) == 0:
			self._conditions.append(JsonCondition.simple_definition(self._parent, self._path))
			return
		for condition_definition in self._definition["condition"].split(","):
			self._conditions.append(JsonCondition.simple_definition(self._parent, condition_definition))

	@staticmethod
	def template_definition():
		definition_json_string = """
		    {
      "id": null,
      "path": null,
      "condition": null
    }
		"""
		return json.loads(definition_json_string)

	def check_conditions(self, json_data):
		# // no conditions to evaluate
		if not self.has_conditions:
			return True
		# // all conditions must be evaluated as true
		for condition in self.conditions:
			if not self._parent._parent.match_on_condition(json_data, condition):
				return False
		return True
	def evaluate(self, json_data):
		# // set field value based on evaluated condition
		if self.check_conditions(json_data):
			return self.init_value(json_data)
		return False
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
	def init_value(self, json_data):
		self._value = None
		path_exists, path_value = get_json_path(json_data, self.path)
		if path_exists is not None:
			self._value = path_value
			return True
		return False
	def reset_value(self):
		self._value = None

	@property
	def id(self):
		return self._id
	@property
	def path(self):
		return self._path
	@property
	def value(self):
		return self._value
	@property
	def conditions(self):
		return self._conditions

	@property
	def has_conditions(self):
		if len(self.conditions) > 0:
			return True

def get_json_from_file(file_path):
	if os.path.isfile(file_path):
		with open(file_path, 'r') as f:
			return json.load(f)
	return None

def run_rules_on_json_data(rule_engine, json_data):
	rule_engine.reset()
	for rule in rule_engine.rules:
		#rule._reset_fields()
		if run_rule_on_json(rule_engine, rule, json_data):
			#print("   //// Building report ////////")
			rule_report = build_rule_report(rule_engine, rule, json_data)
			if rule_report is not None:
				#print("// Rule(id: %s).Name: %s - get report template" % (rule.id, rule.name))
				filler = "*" * int((39 * 2))
				#print("RULE REPORT\n%s\n%s\n%s\n" % (filler,rule_report,filler))
				#print("RULE REPORT\n%s\n%s\n" % (filler,rule_report))
				print("%s\n" % rule_report)
			#return True
	return False
def run_rule_on_json(rule_engine, rule, json_data):
	rule_data = ""
	#print("// Rule(id: %s).Name: %s - get report template" % (rule.id, rule.name))
	#print(json_prettify(rule._definition))
	if not rule.check_requirements(json_data):
		#print("   - requirements  - 'not fullfilled'")
		return False
	if not rule.check_conditions(json_data):
		#print("   - conditions - 'NOT OK'")
		return False
	#print("   - requirements - 'fullfilled'")
	#print("   - conditions - 'OK'")
	return True

	#print("Rule: %s (by: %s / %s)\n\t%s" % (rule.name, rule.owner["researcher"], rule.owner["company"], rule.description))
	print("//// Building report ////////")
	rule_report = build_rule_report(rule_engine, rule, json_data)
	if rule_report is not None:
		print("// Rule(id: %s).Name: %s - get report template" % (rule.id, rule.name))
		filler = "*" * int((39 * 2))
		print("RULE REPORT\n%s\n%s\n%s" % (filler,rule_report,filler))

	else:
		print("Failed to get report for rule '%s' (id: %s)", (rule.name, rule.id))
	return False




#	field_refs_with_match = []
#	for field_id in rule.fields:
#		field = rule.fields[field_id]
#		if rule_engine._debug:
#			print("")
#			print("field id: %s, path: %s, condition: %s" % (field.id, field.path, field.as_conditions()))
#		field.reset_value()
#		if field.check_conditions(json_data):
#			if rule_engine._debug:
#				print("[*] Field '%s' - match 'OK'" % field.id)
#			if field.evaluate(json_data):
#				field_refs_with_match.append(field)
#		else:
#			if rule_engine._debug:
#				print("[*] Skipping Field - '%s' with condition '%s'!" % (field.id, field.as_conditions()))
#
#	if len(field_refs_with_match) > 0:
#		fields_data = format_rule_data_from_fields(rule_engine, rule, field_refs_with_match)
#		#if rule_data != rule._data_template:
#		#print("* Match on Rule: %s (id: %s, by: %s / %s)\n\t// %s" % (rule.name, rule.id, rule.owner["researcher"], rule.owner["company"], rule.description))
#		#print(fields_data)
#		if len(rule_data) > 0:
#			rule_data = "%s\n" % rule_data
#		rule_data = "%s%s" % (rule_data, fields_data)
#	print("* Match on Rule: %s (id: %s, by: %s / %s)\n\t// %s" % (rule.name, rule.id, rule.owner["researcher"], rule.owner["company"], rule.description))
#	rule_data = format_templated_rule_data(rule_engine, rule, rule_data)
#	print(rule_data)
#	return True
def build_rule_report(rule_engine, rule, json_data):
	report_template = get_rule_report_template(rule_engine, rule, json_data)
	if report_template is None:
		return None

	return format_rule_report_template(rule, report_template, json_data)
def get_rule_report_template(rule_engine, rule, json_data):
	evaluated_rule_fields = get_evaluated_rule_fields(rule, json_data)
	if len(evaluated_rule_fields) == 0:
		return None

	report_template = ''
	evaluated_template_data_chunks = OrderedDict()
	for template_chunk in rule._templates:
		if not template_chunk.check_requirements():
			continue
		evaluated_template_data_chunks[template_chunk.id] = template_chunk
	# // build output from evaluated template data chunks
	for template_chunk_id in evaluated_template_data_chunks:
		template_chunk = evaluated_template_data_chunks[template_chunk_id]
		if not template_chunk.has_dependencies:
			report_template = "%s%s" % (report_template, ''.join(template_chunk.data))
		else:
			dependent_templates_evaluated = True
			for dependent_template in template_chunk.template_dependency.split(","):
				if dependent_template not in evaluated_template_data_chunks:
					dependent_templates_evaluated = False
					break
			if dependent_templates_evaluated:
				report_template = "%s%s" % (report_template, ''.join(template_chunk.data))

	return report_template
def format_rule_report_template(rule, report_template, json_data):
	formatted_report_template = report_template

	valid_rule_refs = "id,name,description,owner.researcher,owner.company".split(",")

	refs = extract_refs_from_data(formatted_report_template)
	for ref in refs:
		if ":" not in ref:
			continue

		ref_type = ref.split(":")[0]
		ref_id = ref.split(":")[1]
		ref_value = None

		if "field" == ref_type:
			if rule.field_exists(ref_id):
				field = rule.get_field(ref_id)
				ref_value = str(field.value)

		elif "rule" == ref_type:
			if ref_id not in valid_rule_refs:
				continue
			path_exists, path_value = get_json_path(rule._definition, ref_id)
			if path_exists:
				ref_value = path_value
		elif "raw" == ref_type:
			ref = ref_id
			if ref_id in json_data:
				path_exists = True
				path_value = json_data[ref_id]
			else:
				path_exists, path_value = get_json_path(json_data, ref_id)
			if path_exists:
				ref_value = path_value

		if ref_value is not None:
			formatted_report_template = formatted_report_template.replace("[%s]" % ref, str(ref_value))

	return formatted_report_template.rstrip()

def get_evaluated_rule_fields(rule, json_data):
#def get_evaluated_rule_fields(rule_engine, rule, json_data):
	evaluated_rule_fields = []
	for field_id in rule.fields:
		field = rule.fields[field_id]
		if field.evaluate(json_data):
			evaluated_rule_fields.append(field)
	return evaluated_rule_fields
def extract_refs_from_data(data):
	ref_list = []
	refs = [x.group() for x in re.finditer( r'\[(.*?)\]', data)]
	for ref in refs:
		if ":" in ref:
			ref_type = ref[1:].split(":")[0]
			ref_id = ref[1:].split(":")[1][:-1]
		else:
			ref_type = "raw"
			ref_id = ref[1:][:-1]
		ref_list.append("%s:%s" % (ref_type, ref_id))
	return ref_list
def format_templated_rule_data(rule_engine, rule, rule_data):
	format_definition = rule._data_template

	field_refs = extract_refs_from_data(rule_data)

	return rule_data

def format_rule_data_from_fields(rule_engine, rule, field_refs):
	format_definition = rule._data_template
	rule_fields = []
	rule_field_list = "id,name,description,owner.researcher,owner.company".split(",")
	for path in rule_field_list:
		path_exists, path_value = get_json_path(rule._definition, path)
		if path_exists:
			rule_fields.append(["[rule:%s]" % path, path_value])
	
	for rule_field in rule_fields:
		if rule_field[0] in format_definition:
			format_definition = format_definition.replace(rule_field[0], rule_field[1])
	for field in field_refs:
		if field.value is not None:
			field_value_type = type(field.value).__name__
			if "bool" == field_value_type or "int" == field_value_type:
				field._value = str(field.value).lower()
			format_pattern = "[field:%s]" % field.id
			if format_pattern in format_definition:
				format_definition = format_definition.replace(format_pattern, field.value)
	return format_definition

def run_rules_on_json_file(rule_engine, json_file):
	if not os.path.isfile(json_file):
		print("ERROR - Missing 'json' file '%s'" % json_file)
		return
	#print("Running %s rules on %s" % (len(rule_engine.rules), json_file))
	json_data = get_json_data(json_file)
	if json_data is None:
		print("Failed to get json data from '%s'" % json_file)
		return

	if "list" == type(json_data).__name__:
		if len(json_data) == 0:
			print("Missing json data in '%s'" % json_file)
			return
		if len(json_data) > 0 and "dict" != type(json_data[0]).__name__:
			print("Unknown json data in '%s'" % json_file)
			return

		for json_item in json_data:
			if run_rules_on_json_data(rule_engine, json_item):
				break

	elif "dict" == type(json_data).__name__:
		print("run_rules_on_json_file() : json_data.type: dict")
		if run_rules_on_json_data(rule_engine, json_data):
			return

	else:
		print("Unknown json data in '%s'" % json_file)
		return

def get_json_data(file_path):
	json_data = get_json_from_file(file_path)
	if "dict" == type(json_data).__name__:
		if "data" in json_data:
			return json_data["data"]
		return json_data
	return None
def main(args):
	#root_dir = "/home/bob104/tools/shodan-cli"
	root_dir = "/home/angeld/Workspace/coding/shodan-py"
	root_dir2 = "/home/bob104/tools/shodan-cli"
	if os.path.isdir(root_dir2):
		root_dir = root_dir2
	
	data_dir = os.path.join(root_dir, "shodan-data")
	#data_dir = "/home/angeld/Workspace/coding/shodan-py/shodan-data"
	target = "91.195.240.94"
	json_filename = "host.%s.json" % target
	json_file = os.path.join(data_dir, json_filename)

	default_rule_filename = "rules.json"
	rules_file = os.path.join(root_dir, default_rule_filename)

	if args.custom_rule_file is not None:
		rules_file = args.custom_rule_file

	if args.custom_json_file is not None:
		json_file = args.custom_json_file
	elif args.custom_json_file_from_target_host is not None:
		json_filename = "host.%s.json" % args.custom_json_file_from_target_host
		json_file = os.path.join(data_dir, json_filename)

	if not os.path.isfile(rules_file):
		print("ERROR - Missing 'rules' file '%s'" % rules_file)
		return

	if not os.path.isfile(json_file):
		print("ERROR - Missing 'json' file '%s'" % json_file)
		return

	json_data = get_json_from_file(json_file)
	json_rules = get_json_from_file(rules_file)

	engine = JsonRuleEngine(json_rules)
	engine._debug = args.debug_mode

	run_rules_on_json_file(engine, json_file)

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Rule based Detection Engine for Json content")
	parser.add_argument('-d', '--debug', dest='debug_mode', action='store_true', help="Enabled debug mode")
	parser.add_argument('-r', '--rule-file', dest='custom_rule_file', help="Custom rules file")
	parser.add_argument('-j', '--json-file', dest='custom_json_file', help="Custom json file")
	parser.add_argument('-t', '--target', dest='custom_json_file_from_target_host', help="Target to json file")
	args = parser.parse_args()
	main(args)
