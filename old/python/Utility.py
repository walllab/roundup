import time
import os
import re

import execute


#
# Run one command, and report if anything goes wrong,
# terminating at the time.
#
def runOrReportFailure(command):
	#
	try:
		message = execute.run("%s 2>&1" % command)
		return (1, message)
	except Exception, e:
		return (0, str(e))

		
# last line
