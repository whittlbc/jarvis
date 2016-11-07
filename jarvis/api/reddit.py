from abstract_api import AbstractApi
import jarvis.helpers.db as db
import time


class Reddit(AbstractApi):
	
	def __init__(self):
		self.slug = __name__.split('.').pop()
		AbstractApi.__init__(self, self.slug, wrapper=True)

	def unique_post(self, subreddit=None):
		if not subreddit: return None
		
		# Get all ids for content shown to the current user in the past.
		prev_content_ids = db.content_ids_for_service(self.slug)
			
		if not prev_content_ids:
			return next(self.subreddit(subreddit).hot(limit=1))
		else:
			last_batch_entry = None
			
			while True:
				if last_batch_entry:
					params = {'after': last_batch_entry.name}
				else:
					params = None
					
				limit = 10
				batch = self.subreddit(subreddit).hot(limit=limit, params=params)
				
				i = 0
				for post in batch:
					if post.id not in prev_content_ids:
						db.add_service_user_content(post.id, self.slug)
						return post
					elif i == limit - 1:
						last_batch_entry = post
					
					i += 1
					
				# Let's not overstay our welcome with Reddit's API.
				time.sleep(1)