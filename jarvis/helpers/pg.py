from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

con = connect(dbname='memory')
con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)


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
	
	cur = cur or con.cursor()
	cur.execute("INSERT INTO {} ({}) VALUES ({}) RETURNING id;".format(model, keys, vals))
	return cur.fetchone()[0]


def find_one(model, query, cur=None):
	formatted_query = keyify(query, connector='AND')
	
	cur = cur or con.cursor()
	cur.execute("SELECT * FROM {} WHERE {} LIMIT 1;".format(model, formatted_query))
	return cur.fetchone()[0]
		

def upsert(model, data, unique_to=None):
	cur = con.cursor()
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
	return connector.join(['{} = {}'.format(k, v) for k, v in d.items()])
	

def error(msg=''):
	raise BaseException(msg)