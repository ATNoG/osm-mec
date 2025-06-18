import copy
import threading
import time
import logging
from src.utils.kafka.kafka_utils import KafkaUtils

class SendFederationContainersThread:
    """Background thread that sends MEC Apps information"""

    def __init__(self, producer, federation_container_to_app: dict, federation_container_to_app_topic: str, federation_send_freq: int):
        self.producer = producer

        self.federation_container_to_app = federation_container_to_app
        self.federation_container_to_app_topic = federation_container_to_app_topic
        self.federation_send_freq = federation_send_freq

        self.t = None

    def start(self):
        """Plugin entrypoint"""
        self.t = threading.Thread(target=self.send_cluster_metrics, args=())
        self.t.daemon = True
        self.t.start()
    
    def send_cluster_metrics(self):
        while True:
            try:
                message = {
                    "containers": self.federation_container_to_app,
                }

                # Kafka sending placeholder
                KafkaUtils.send_message(self.producer, self.federation_container_to_app_topic, message)
                logging.info("Sent message to Kafka topic {}: {}".format(self.federation_container_to_app_topic, message))

                time.sleep(self.federation_send_freq)

            except Exception as e:
                print("INFO: Exception while sending container info: ", e)
                continue
