from jarvis.core.responder import respond
import jarvis.helpers.responses as r


def greeting(m):
	respond(r.random_greeting())


def whatup(m):
	respond(r.random_whatup())


def resp_new_memory(x, y):
	respond('Got it! Remembering {} as {}.'.format(x, y), with_audio=True)


def remember(mem_val):
	respond(mem_val, with_audio=True)
	
	
def forget(memory):
	respond('Forgetting {}.'.format(memory))
	
	
def list_memories(mem_map):
	if not mem_map:
		respond('You haven\'t told me to remember anything yet!')
	else:
		keys = list(mem_map)
		keys.sort()
		
		mem_str = ''
		
		for k in keys:
			mem_str += "{}: {}\n".format(k, mem_map[k])
			
		respond(mem_str.strip())
