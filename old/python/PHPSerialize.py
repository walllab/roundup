import types, string
import re

"""
Serialize class for the PHP serialization format.

@version v0.3 BETA
@author Scott Hurring; scott at hurring dot com
@copyright Copyright (c) 2005 Scott Hurring
@license http://opensource.org/licenses/gpl-license.php GNU Public License
$Id: PHPSerialize.py,v 1.1 2005/04/06 03:58:53 cvs Exp $

Most recent version can be found at:
http://hurring.com/code/python/phpserialize/

Usage:
# Create an instance of the serialize engine
s = PHPSerialize()
# serialize some python data into a string
serialized_string = s.serialize(data)

Please see README.txt for more information.
"""

class PHPSerialize(object):
	"""
	Class to serialize data using the PHP Serialize format.

	Usage:
	s = PHPSerialize()
	serialized_string = s.serialize(data)
	"""

	def __init__(self):
		self.phpIntegerStringRE = re.compile('^(0|(-?[1-9]\d*))$')
		pass

	def serialize(self, data):
		return self._serialize(data)

	def _serializeKey(self, data):
		"""
		Serialize data, as a PHP array key.  This means converting strings which are integers, e.g. "1234",
		to integers, and truncating float values to integers.
		Uses type() to figure out what type to serialize a thing as...
From the php manual (http://us2.php.net/manual/en/language.types.array.php):
 A key may be either an integer or a string. If a key is the standard representation of an integer, it will be interpreted as such (i.e. "8" will be interpreted as 8, while "08" will be interpreted as "08"). Floats in key are truncated to integer. There are no different indexed and associative array types in PHP; there is only one array type, which can both contain integer and string indices.

 Using TRUE as a key will evaluate to integer  1 as key. Using FALSE as a key will evaluate to integer 0 as key. Using NULL as a key will evaluate to the empty string. Using the empty string as key will create (or overwrite) a key with the empty string and its value; it is not the same as using empty brackets.

 You cannot use arrays or objects as keys. Doing so will result in a warning: Illegal offset type.

 This code snippet gives a taste of how keys serialize:
echo serialize(array(array() => 'array()', true => 'true', false => 'false', "+8" => "+8", "8" => "8", "08" => "08", "1.5e10" => "1.5e10", "1e2" => "1e2", "-8" => "-8", "-0" => "-0", NULL => 'NULL'));
result> a:10:{i:1;s:4:"true";i:0;s:5:"false";s:2:"+8";s:2:"+8";i:8;s:1:"8";s:2:"08";s:2:"08";s:6:"1.5e10";s:6:"1.5e10";s:3:"1e2";s:3:"1e2";i:-8;s:2:"-8";s:2:"-0";s:2:"-0";s:0:"";s:4:"NULL";}
		"""

		# Integer => integer
		if type(data) is types.IntType or type(data) is types.LongType:
			return "i:%s;" % data

		# Floating Point => int, Boolean => int
		elif type(data) is types.FloatType or type(data) is types.BooleanType:
			return "i:%s;" % int(data)

		# String => string or int if string is an int.
		elif type(data) is types.StringType:
			if self.phpIntegerStringRE.search(data):
				return "i:%s;" % int(data)
			else:
				return "s:%i:\"%s\";" % (len(data), data);

		# None / NULL => empty string
		elif type(data) is types.NoneType:
			return "s:0:\"\";"

		# I dont know how to serialize this
		else:
			raise Exception("Unknown / Unhandled key type (%s)!" % type(data))
		
	def _serialize(self, data):
		"""
		Serialize data recursively.
		Uses type() to figure out what type to serialize a thing as...
		"""

		# Integer => integer
		if type(data) is types.IntType:
			return "i:%s;" % data

		# Floating Point => double
		elif type(data) is types.FloatType or type(data) is types.LongType:
			return "d:%s;" % data

		# String => string
		elif type(data) is types.StringType:
			return "s:%i:\"%s\";" % (len(data), data);

		# None / NULL
		elif type(data) is types.NoneType:
			return "N;";

		# Tuple and List => array
		# The 'a' array type is the only kind of list supported by PHP.
		# array keys are automagically numbered up from 0
		elif type(data) is types.ListType or type(data) is types.TupleType:
			i = 0
			out = []
			# All arrays must have keys
			for k in data:
				out.append(self._serializeKey(i))
				out.append(self._serialize(k))
				i += 1
			return "a:%i:{%s}" % (len(data), "".join(out))

		# Dict => array
		# Dict is the Python analogy of a PHP array
		elif type(data) is types.DictType:
			out = []
			for k in data:
				out.append(self._serializeKey(k))
				out.append(self._serialize(data[k]))
			return "a:%i:{%s}" % (len(data), "".join(out))

		# Boolean => bool
		elif type(data) is types.BooleanType:
			if data: b = 1
			else: b = 0
			return "b:%i;" % (b)

		# I dont know how to serialize this
		else:
			raise Exception("Unknown / Unhandled data type (%s)!" % type(data))

	def _serialize2(self, data):
		"""
		Serialize data recursively.
		Uses type() to figure out what type to serialize a thing as...
		"""

		# stackTypes: 'v' == regular value, 'a' == end of array, 'k' == array key
		out = ''
		stack = [(data, 'v')]
		while stack:
			(data, stackType) = stack.pop()
			if stackType == 'a':
				out += '}'

			elif stackType == 'k':
				# Integer => integer
				if type(data) is types.IntType or type(data) is types.LongType:
					out += "i:%s;" % data

				# Floating Point => int, Boolean => int
				elif type(data) is types.FloatType or type(data) is types.BooleanType:
					out += "i:%s;" % int(data)

				# String => string or int if string is an int.
				elif type(data) is types.StringType:
					if self.phpIntegerStringRE.search(data):
						out += "i:%s;" % int(data)
					else:
						out += "s:%i:\"%s\";" % (len(data), data);

				# None / NULL => empty string
				elif type(data) is types.NoneType:
					out += "s:0:\"\";"

				# I dont know how to serialize this
				else:
					raise Exception("Unknown / Unhandled key type (%s)!" % type(data))

			elif stackType == 'v':
				# Integer => integer
				if type(data) is types.IntType:
					out += "i:%s;" % data
				
				# Floating Point => double
				elif type(data) is types.FloatType or type(data) is types.LongType:
					out += "d:%s;" % data
				
				# String => string
				elif type(data) is types.StringType:
					out += "s:%i:\"%s\";" % (len(data), data);
				
				# None / NULL
				elif type(data) is types.NoneType:
					out += "N;";

				# Boolean => bool
				elif type(data) is types.BooleanType:
					out += "b:%i;" % (data)


				# Tuple and List => array
				# The 'a' array type is the only kind of list supported by PHP.
				# array keys are automagically numbered up from 0
			        elif type(data) is types.ListType or type(data) is types.TupleType:
					out += "a:%i:{" % (len(data))
					stack.append((None, 'a'))
					for i in xrange(len(data)-1, -1, -1):
						stack.append((data[i], 'v'))
						stack.append((i, 'k'))

				# Dict => array
				# Dict is the Python analogy of a PHP array
			        elif type(data) is types.DictType:
					out += "a:%i:{" % (len(data))
					stack.append((None, 'a'))
					for k, v in data.iteritems():
						stack.append((v, 'v'))
						stack.append((k, 'k'))


				# I dont know how to serialize this
		                else:
					raise Exception("Unknown / Unhandled value type (%s)!" % type(data))

			else:
				raise Exception("Unknown / Unhandled stack type (%s)!" % type(data))

		return out

# last line emacs python mode bug fix
