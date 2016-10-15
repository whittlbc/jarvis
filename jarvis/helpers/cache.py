import redis
from jarvis.helpers.configs import configs


cache = redis.StrictRedis.from_url(configs.REDIS_URL)