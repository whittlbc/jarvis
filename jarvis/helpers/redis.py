import redis
from jarvis.helpers.configs import configs


redis_client = redis.StrictRedis.from_url(configs.REDIS_URL)