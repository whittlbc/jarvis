# from config import DevelopmentConfig
# configs = DevelopmentConfig()
import os
import re


def config(key):
	val = os.environ.get(key)
	
	if val and re.match('true', val, re.I):
		val = True
	elif val and re.match('false', val, re.I):
		val = False
		
	return val