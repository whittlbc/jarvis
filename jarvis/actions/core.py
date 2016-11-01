from jarvis.core.responder import respond
import jarvis.helpers.responses as r
import jarvis.helpers.helpers as helpers


def greeting(m):
	respond(r.random_greeting(), with_audio=m.is_audio)


def whatup(m):
	respond(r.random_whatup(), with_audio=m.is_audio)


def resp_new_memory(memory, verb_phrase, attr_value, is_audio):
	if verb_phrase == 'as':
		verb_phrase = 'is'
		
	memory = helpers.perspective_swap(memory)
	attr_value = helpers.perspective_swap(attr_value)
		
	respond('Got it! Remembering that {} {} {}.'.format(memory, verb_phrase, attr_value), with_audio=is_audio)


def remember(memory, is_audio):
	memory = helpers.perspective_swap(memory)
	respond(memory, with_audio=is_audio)
	
	
def forget(memory, is_audio):
	respond('Forgetting {}.'.format(memory), with_audio=is_audio)
	
	
def list_memories(mem_map, is_audio):
	if not mem_map:
		respond('You haven\'t told me to remember anything yet!', with_audio=is_audio)
	else:
		keys = list(mem_map)
		keys.sort()
		
		mem_str = ''
		
		for k in keys:
			mem_str += "{}: {}\n".format(k, mem_map[k])
			
		respond(mem_str.strip(), with_audio=is_audio)
		
		
def trained_chat_resp(text, is_audio):
	respond(text, with_audio=is_audio)