import redis
from jarvis.helpers.configs import config

cache = redis.StrictRedis.from_url(config('REDIS_URL'))