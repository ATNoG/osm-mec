import threading
import time
import json

from cherrypy.process import plugins

from utils.db import DB
from utils.kafka import KafkaUtils, producer

containers = {}

class SendMECAppsThread(plugins.SimplePlugin):
    """Background thread that sends MEC Apps information"""

    def __init__(self, bus):
        super().__init__(bus)
        self.t = None

    def start(self):
        """Plugin entrypoint"""
        self.t = threading.Thread(target=send_mec_apps)
        self.t.daemon = True
        self.t.start()


def send_mec_apps():
    while True:
        try:
            mec_apps = DB._list("appis")
            for mec_app in mec_apps:
                if '_id' in mec_app:
                    mec_app['_id'] = str(mec_app['_id'])

            KafkaUtils.send_message(
                producer,
                "meao-oss",
                {"mec_apps": mec_apps},
            )
            
            time.sleep(5)
        except Exception as e:
            raise e