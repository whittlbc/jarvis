from jarvis.helpers.configs import config
from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import DictCursor

con = connect(dbname=config('PG_DB_NAME'))
con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)


def cursor():
	return con.cursor(cursor_factory=DictCursor)


def insert_one(model, data, cur=None):
	keys, vals = [], []
	
	for k, v in data.items():
		keys.append(k)
		
		if isinstance(v, basestring):
			v = "'{}'".format(v)
		else:
			v = str(v)
		
		vals.append(v)
		
	keys = ', '.join(keys)
	vals = ', '.join(vals)
	
	cur = cur or cursor()
	cur.execute("INSERT INTO {} ({}) VALUES ({}) RETURNING id;".format(model, keys, vals))
	return cur.fetchone()[0]


def find_one(model, query, cur=None):
	formatted_query = keyify(query, connector=' AND ')
	
	cur = cur or cursor()
	cur.execute("SELECT * FROM {} WHERE {} LIMIT 1;".format(model, formatted_query))
	return cur.fetchone()
		

def find(model, query, returning='*', cur=None):
	formatted_query = keyify(query, connector=' AND ')
	
	cur = cur or cursor()
	cur.execute("SELECT {} FROM {} WHERE {};".format(returning, model, formatted_query))
	return cur.fetchall()


def upsert(model, data, unique_to=None):
	cur = cursor()
	unique_to = unique_to or data.keys()
	
	query = {k: data[k] for k in unique_to}
	
	record = find_one(model, query, cur=cur)
	
	if record:
		id = record['id']
	else:
		id = insert_one(model, data, cur=cur)
	
	cur.close()
	
	return id
	
	
def keyify(d, connector=''):
	groups = []
	
	for k, v in d.items():
		if isinstance(v, basestring) and v[0] != '(':
			v = "'{}'".format(v)
		elif isinstance(v, list) or isinstance(v, tuple):
			v = tuple(v)
		else:
			v = str(v)
			
		if isinstance(v, tuple) or (isinstance(v, basestring) and v[0] == '('):
			assoc = 'IN'
		else:
			assoc = '='
			
		if isinstance(v, tuple):
			# get rid of trailing comma
			v = '({})'.format(','.join(map(lambda x: str(x), v)))
		
		groups.append('{} {} {}'.format(k, assoc, v))
	
	return connector.join(groups)
	

def error(msg=''):
	raise BaseException(msg)