import pyvona
from configs import configs

voice = pyvona.create_voice(configs.IVONA_ACCESS_KEY, configs.IVONA_SECRET_KEY)
