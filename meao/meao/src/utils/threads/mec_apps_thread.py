import threading
import time
import json

from src.utils.db import DB
from src.utils.kafka.kafka_utils import KafkaUtils

class SendMECAppsThread:
    """Background thread that sends MEC Apps information"""

    def __init__(self, producer):
        self.producer = producer
        self.t = None

    def start(self):
        """Plugin entrypoint"""
        self.t = threading.Thread(target=send_mec_apps, args=(self.producer,))
        self.t.daemon = True
        self.t.start()


def send_mec_apps(producer):
    while True:
        try:
            mec_apps = DB._list("appis")
            for mec_app in mec_apps:
                if '_id' in mec_app:
                    mec_app['_id'] = str(mec_app['_id'])

            KafkaUtils.send_message(
                producer,
                "mec-apps",
                {"mec_apps": mec_apps},
            )
            
            time.sleep(5)
        except Exception as e:
            raise e
