import threading
import time

from src.utils.db import DB
from src.utils.kafka.kafka_utils import KafkaUtils

class MECAppsInstancesThread:
    """Background thread that sends MEC Apps information"""

    def __init__(self, producer, mec_apps: dict, appis: dict):
        self.producer = producer
        self.mec_apps = mec_apps
        self.appis = appis
        self.t = None

    def start(self):
        """Plugin entrypoint"""
        self.t = threading.Thread(target=self.send_mec_apps, args=())
        self.t.daemon = True
        self.t.start()

    def send_mec_apps(self):
        while True:
            try:
                # Get the MEC Apps from the database
                mec_apps = {}
                for mec_app in DB._list("app_pkgs"):
                    [ mec_app.pop(k, None) for k in ['appd',] if k in mec_app ]
                    if '_id' in mec_app:
                        mec_app['_id'] = str(mec_app['_id'])
                    mec_apps[mec_app['_id']] = mec_app

                # Get the MEC Apps Instances from the database
                appis = {}
                for appi in DB._list("appis"):
                    if '_id' in appi:
                        appi['_id'] = str(appi['_id'])
                    appis[appi['appi_id']] = appi

                # Update the dictionaries
                self.mec_apps.clear()
                self.mec_apps.update(mec_apps)
                self.appis.clear()
                self.appis.update(appis)

                # Send the MEC Apps information to Kafka
                KafkaUtils.send_message(self.producer, "mec-apps", self.mec_apps)
                KafkaUtils.send_message(self.producer, "appis", self.appis)
                
                time.sleep(5)
            except Exception as e:
                raise e
            