import json
import numpy as np
import os
from jarvis.helpers.cache import cache
from jarvis.helpers.configs import config
from definitions import formulas_dir
from jarvis.helpers.s3 import download
from db_helper import where
from models import Formula, UserFormula


def connect(sid, user):
	update_user_socket_ids(user.uid, sid, onconnect=True)
	maybe_fetch_remote_user_formulas(user.id)
	
	
def disconnect(sid, user):
	update_user_socket_ids(user.uid, sid)
	maybe_remove_cached_user_formulas(user.id)


def update_user_socket_ids(user_uid, sid, onconnect=False):
	# Fetch current socket_ids for user_uid in cache
	user_sids = cache.hget(config('USER_CONNECTIONS'), user_uid) or []
	
	# return if user_sids already blank and disconnecting
	if not user_sids and not onconnect:
		return
	
	if user_sids:
		try:
			user_sids = json.loads(user_sids) or []
		except:
			user_sids = []
			print 'Error parsing JSON from cache'
	
	if onconnect:
		user_sids.append(sid)
	else:
		user_sids = [x for x in user_sids if x != sid]
	
	# unique them just in case
	user_sids = list(np.unique(user_sids))
	
	# Update cache with new sids for user
	cache.hset(config('USER_CONNECTIONS'), user_uid, json.dumps(user_sids))
	

# Fetch user formulas from S3 if not cached locally
def maybe_fetch_remote_user_formulas(user_id):
	formula_ids = [uf.formula_id for uf in where(UserFormula, {'user_id': user_id})]
	
	if formula_ids:
		formula_uids = [f.uid for f in where(Formula, {'id': formula_ids})]
	
		# find formulas not cached yet
		formulas_to_fetch = [uid for uid in formula_uids if not os.path.exists('{}/{}.py'.format(formulas_dir, uid))]
	
		if formulas_to_fetch:
			print 'Fetching {} formula(s) for user from S3...'.format(len(formulas_to_fetch))
	
			for formula_uid in formulas_to_fetch:
				# Should prolly break this out into a worker of some sorts with a callback
				download(
					'{}/{}.py'.format(config('S3_FORMULAS_DIR'), formula_uid),  # S3 file path
					'{}/{}.py'.format(formulas_dir, formula_uid)  # download path
				)
			
			print 'Done fetching formula(s) for user.'
	else:
		print 'No formulas associated with user.'
		

def maybe_remove_cached_user_formulas(user_id):
	print
	# This is gonna be a tough query -- come back to this later
	# Query DB to get a list of formulas uids that ONLY this user is associated with.
	# user_specific_formula_uids = ['myformulauid']
	#
	# # Remove these formulas
	# [os.remove('{}/{}.py'.format(formulas_dir, formula_uid)) for formula_uid in user_unique_formulas]