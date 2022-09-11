import re
import json

class Condition:
	UNKNOWN = "unknown"
	# // simple comparison conditions
	EXISTS = "exists"
	HAS_VALUE = "has-value"
	NO_VALUE = "no-value" # same as IS_EMPTY
	IS_EMPTY = "is-empty"
	IS_NULL = "is-null"
	IS_TYPE = "is-type"
	TYPE = "type" # same as IS_TYPE
	NULL = "null" # same as IS_NULL
	# // complex comparison conditions
	IS = "is" # as equals but case sensitive
	EQUALS = "equals"
	VALUE = "value" # same as EQUALS
	CONTAINS = "contains" # contains in string or list item
	HAS = "has" # has list item
	STARTS = "starts"
	BEGINS = "begins" # same as STARTS
	ENDS = "ends"

	LEN = "len" # len ==
	MIN_LEN = "min-len"
	MAX_LEN = "max-len"
	NUM_GREATER_THEN = "gt"
	NUM_GREATER_EQUAL_LTHEN = "gte"
	NUM_LESS_THEN = "lt"
	NUM_LESS_EQUAL_THEN = "lte"
	NUM_EQUAL = "eq"
	REGEX = "regex"

	@staticmethod
	def _is_valid_type(str_type):
		if "str" != type(str_type).__name__:
			return False

		# // simple comparison conditions
		if Condition.EXISTS == str_type:
			return True
		if Condition.HAS_VALUE == str_type:
			return True
		if Condition.IS_NULL == str_type or Condition.NULL == str_type:
			return True
		if Condition.IS_EMPTY == str_type or Condition.NO_VALUE == str_type:
			return True
		if Condition.IS_TYPE == str_type:
			return True
		if Condition.TYPE == str_type:
			return True
		# // complex comparison conditions
		if Condition.EQUALS == str_type or Condition.IS == str_type:
			return True
		if Condition.VALUE == str_type:
			return True
		if Condition.CONTAINS == str_type or Condition.HAS == str_type:
			return True
		if Condition.STARTS == str_type or Condition.BEGINS == str_type:
			return True
		if Condition.ENDS == str_type:
			return True
		if Condition.LEN == str_type:
			return True
		if Condition.MIN_LEN == str_type:
			return True
		if Condition.MAX_LEN == str_type:
			return True
		if Condition.REGEX == str_type:
			return True
		if Condition.NUM_GREATER_THEN == str_type:
			return True
		if Condition.NUM_GREATER_EQUAL_THEN == str_type:
			return True
		if Condition.NUM_LESS_THEN == str_type:
			return True
		if Condition.NUM_LESS_EQUALTHEN == str_type:
			return True
		if Condition.NUM_EQUAL == str_type:
			return True
	@staticmethod
	def has_negation_operator(condition):
		if 'str' != type(condition).__name__:
			return False
		if condition.startswith("!"):
			return True
		if condition.lower().startswith("not-"):
			return True
		return False
	@staticmethod
	def is_case_sensitive(condition):
		if 'str' != type(condition).__name__:
			return False
		if len(condition) == 0:
			return False
		if Condition.has_negation_operator(condition):
			if Condition.strip_negation_operator(condition)[0].isupper():
				return True
		elif condition[0].isupper():
				return True
		return False
	@staticmethod
	def strip_negation_operator(condition):
		if not Condition.has_negation_operator(condition):
			return condition
		if condition.lower().startswith("!"):
			return condition[1:]
		if condition.lower().startswith("not-"):
			return condition[4:]
		return condition
class Compare:
	@staticmethod
	def _cast_str_num_as_int(str_num):
		if "str" == type(str_num).__name__ and str_num.isnumeric():
			return int(str_num)
		return str_num
	@staticmethod
	def _is_number(num):
		if "int" == type(num).__name__:
			return True
		if "str" == type(num).__name__ and num.isnumeric():
			return True
		return False
	@staticmethod
	def _is_int(num):
		if "list" == type(num).__name__ and len(num) > 0:
			for i in range(len(num)):
				if "int" != type(num[i]).__name__:
					return False
			return True
		return "int" == type(num).__name__
	@staticmethod
	def num_is_greater_then(value, num, negated_match=False):
		value_num = Compare._cast_str_num_as_int(value)
		greater_num = Compare._cast_str_num_as_int(num)
		# // both numbers must be of type 'int'
		if not Compare._is_int([value_num, greater_num]):
			return False
		if value_num > greater_num:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def num_is_greater_equal_then(value, num, negated_match=False):
		value_num = Compare._cast_str_num_as_int(value)
		greater_equal_num = Compare._cast_str_num_as_int(num)
		# // both numbers must be of type 'int'
		if not Compare._is_int([value_num, greater_equal_num]):
			return False
		if value_num >= greater_equal_num:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def num_is_less_then(value, num, negated_match=False):
		value_num = Compare._cast_str_num_as_int(value)
		less_num = Compare._cast_str_num_as_int(num)
		# // both numbers must be of type 'int'
		if not Compare._is_int([value_num, less_num]):
			return False
		if value_num < less_num:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def num_is_less_equal_then(value, num, negated_match=False):
		value_num = Compare._cast_str_num_as_int(value)
		less_equal_num = Compare._cast_str_num_as_int(num)
		# // both numbers must be of type 'int'
		if not Compare._is_int([value_num, less_equal_num]):
			return False
		if value_num <= less_equal_num:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def num_is_equal(value, num, negated_match=False):
		value_num = Compare._cast_str_num_as_int(value)
		equal_num = Compare._cast_str_num_as_int(num)
		# // both numbers must be of type 'int'
		if not Compare._is_int([value_num, equal_num]):
			return False
		if value_num == equal_num:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def is_length(value, num, negated_match=False):
		if value is None:
			return False
		if "str" == type(value).__name__ and value.lower() == "null":
			return False
		num_len = Compare._cast_str_num_as_int(num)
		if not Compare._is_int(num_len):
			return False
		if "str" == type(value).__name__:
			if len(value) == num_len:
				if negated_match:
					return False
				return True
		if "int" == type(value).__name__:
			if len(str(value)) == num_len:
				if negated_match:
					return False
				return True
		if "list" == type(value).__name__ or "OrderedDict" == type(value).__name__ or "dict" == type(value).__name__:
			if len(value) == num_len:
				if negated_match:
					return False
				return True
		if negated_match:
			return True
		return False
	@staticmethod
	def min_length(value, num, negated_match=False):
		if value is None:
			return False
		if "str" == type(value).__name__ and value.lower() == "null":
			return False
		min_len = Compare._cast_str_num_as_int(num)
		if not Compare._is_int(min_len):
			return False
		if "str" == type(value).__name__:
			if len(value) >= min_len:
				if negated_match:
					return False
				return True
		if "int" == type(value).__name__:
			if len(str(value)) >= min_len:
				if negated_match:
					return False
				return True
		if "list" == type(value).__name__ or "OrderedDict" == type(value).__name__ or "dict" == type(value).__name__:
			if len(value) == min_len:
				if negated_match:
					return False
				return True
		if negated_match:
			return True
		return False
	@staticmethod
	def max_length(value, num, negated_match=False):
		if value is None:
			return False
		if "str" == type(value).__name__ and value.lower() == "null":
			return False
		max_len = Compare._cast_str_num_as_int(num)
		if not Compare._is_int(max_len):
			return False
		if "str" == type(value).__name__:
			if len(value) <= max_len:
				if negated_match:
					return False
				return True
		if "int" == type(value).__name__:
			if len(str(value)) <= max_len:
				if negated_match:
					return False
				return True
		if "list" == type(value).__name__ or "OrderedDict" == type(value).__name__ or "dict" == type(value).__name__:
			if len(value) == max_len:
				if negated_match:
					return False
				return True
		if negated_match:
			return True
		return False
	@staticmethod
	def is_null(value, negated_match=False):
		if value is None:
			if negated_match:
				return False
			return True
		if "str" == type(value).__name__ and value.lower() == "null":
			if negated_match:
				return False
			return True
		return False
	@staticmethod
	def has_value(value, negated_match=False):
		if value is None:
			if negated_match:
				return True
			return False
		if "str" == type(value).__name__ or "list" == type(value).__name__ or "OrderedDict" == type(value).__name__ or "dict" == type(value).__name__:
			if len(value) > 0:
				if negated_match:
					return False
				return True
			if negated_match:
				return True
			return False
		if "int" == type(value).__name__:
			if negated_match:
				return False
			return True
		if negated_match:
			return False
		return True
	@staticmethod
	def is_type(value, match_type, negated_match=False):
		if "str" != type(match_type).__name__:
			return False
		if "string" == match_type.lower() and "str" == type(value).__name__:
			if negated_match:
				return False
			return True
		if value is None and (match_type.lower() == "null" or "nonetype" == type(match_type).__name__.lower()):
			if negated_match:
				return False
			return True
		if "bool" == type(value).__name__ and (("true" == match_type.lower() and value) or ("false" == match_type.lower() and not value)):
			if negated_match:
				return False
			return True
		if "json" == match_type.lower() and "dict" == type(value).__name__:
			if negated_match:
				return False
			return True
		if "number" == match_type.lower() and Compare._is_number(value):
			if negated_match:
				return False
			return True
		if match_type.lower() == type(value).__name__.lower():
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def is_empty(value, negated_match=False):
		if value is None:
			if negated_match:
				return False
			return True
		if "str" == type(value).__name__:
			if len(value) == 0:
				if negated_match:
					return False
				return True
		if "list" == type(value).__name__:
			if len(value) == 0:
				if negated_match:
					return False
				return True
		if "dict" == type(value).__name__:
			if len(value) == 0:
				if negated_match:
					return False
				return True
		if "OrderedDict" == type(value).__name__:
			if len(value) == 0:
				if negated_match:
					return False
				return True
		if "int" == type(value).__name__:
			if negated_match:
				return True
			return False
		return False
	@staticmethod
	def equals(match_on, value, case_sensitive_match=False, negated_match=False):
		if "bool" == type(match_on).__name__ and "str" == type(value).__name__:
			if ("true" == value.lower() and match_on) or ("false" == value.lower() and not match_on):
				if negated_match:
					return False
				return True
			if negated_match:
				return True
			return False
		if "bool" == type(match_on).__name__ and "bool" == type(value).__name__:
			if match_on == value:
				if negated_match:
					return False
				return True
			if negated_match:
				return True
			return False
		if "str" == type(match_on).__name__ and "str" == type(value).__name__:
			if case_sensitive_match:
				if match_on == value:
					if negated_match:
						return False
					return True
			elif match_on.lower() == value.lower():
				if negated_match:
					return False
				return True
			if negated_match:
				return True
			return False
		if "int" == type(match_on).__name__ and Compare._is_number(value):
			if match_on	== Compare._cast_str_num_as_int(value):
				if negated_match:
					return False
				return True
			if negated_match:
				return True
			return False
		if negated_match:
			return True
		return False
	@staticmethod
	def contains(match_on, value, negated_match=False):
		found_match = None
		if "str" == type(match_on).__name__:
			found_match = value.lower() in match_on.lower()
		elif "list" == type(match_on).__name__:
			for item in match_on:
				if "str" == type(item).__name__ and "str" == type(value).__name__:
					found_match = False
					#if value.lower() == item.lower():
					if value.lower() in item.lower():
						found_match = True
						break
				elif "int" == type(item).__name__ and "int" == type(value).__name__:
					found_match = False
					if value == item:
						found_match = True
						break
		elif "OrderedDict" == type(match_on).__name__ or "dict" == type(match_on).__name__:
			if "str" == type(value).__name__:
				found_match = False
				for key in match_on:
					if value.lower() in key.lower():
						found_match = True
						break
		if found_match is None:
			return False
		if found_match:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def has(match_on, value, negated_match=False):
		found_match = None
		if "list" == type(match_on).__name__:
			for item in match_on:
				if "str" == type(item).__name__ and "str" == type(value).__name__:
					found_match = False
					if value.lower() == item.lower():
						found_match = True
						break
				#elif "int" == type(item).__name__ and "int" == type(value).__name__:
				elif "int" == type(item).__name__ and Compare._is_number(value):
					print("Compare.has")
					found_match = False
					if Compare._cast_str_num_as_int(value) == item:
						found_match = True
						break
		elif "OrderedDict" == type(match_on).__name__ or "dict" == type(match_on).__name__:
			if "str" == type(value).__name__:
				found_match = False
				for key in match_on:
					if value.lower() == key.lower():
						found_match = True
						break
		if found_match is None:
			return False
		if found_match:
			if negated_match:
				return False
			return True
		if negated_match:
			return True
		return False
	@staticmethod
	def starts(match_on, value, negated_match=False):
		if "str" == type(match_on).__name__:
			if "str" == type(value).__name__:
				if match_on.lower().startswith(value).lower():
					if negated_match:
						return False
					return True
				if negated_match:
					return True
				return False
			if "int" == type(value).__name__:
				if match_on.startswith(str(value)):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
			if negated_match:
				return True
			return False
		if "int" == type(match_on).__name__:
			if "str" == type(value).__name__:
				if str(match_on).lower().startswith(value.lower()):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
				return False
			if "int" == type(value).__name__:
				if str(match_on).startswith(str(value)):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
			if negated_match:
				return True
			return False
		return False
	@staticmethod
	def ends(match_on, value, negated_match=False):
		if "str" == type(match_on).__name__:
			if "str" == type(value).__name__:
				if match_on.lower().endswith(value.lower()):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
				return False
			if "int" == type(value).__name__:
				if match_on.endswith(str(value)):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
			if negated_match:
				return True
			return False
		if "int" == type(match_on).__name__:
			if "str" == type(value).__name__:
				if str(match_on.lower()).endswith(value.lower()):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
				return False
			if "int" == type(value).__name__:
				if str(match_on).endswith(str(value)):
					if negated_match:
						return False
					return True
				if negated_match:
					return True
			if negated_match:
				return True
			return False
		return False
	@staticmethod
	def match_on_regex(match_on, pattern, negated_match=False):
		data = match_on
		if "dict" == type(match_on).__name__:
			data = str(json.dumps(match_on))
		try:
			if re.match(pattern, data):
				if negated_match:
					return False
				return True
			if negated_match:
				return True
			return False
		except Exception as e:
			pass
		return False
