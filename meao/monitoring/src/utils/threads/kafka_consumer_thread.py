import threading
import time
import json
import os

from src.utils.kafka.kafka_utils import KafkaUtils

class KafkaConsumerThread:
    """Background thread that consumes messages from Kafka"""

    def __init__(self, consumer_conf, topic, callback):
        self.consumer_conf = consumer_conf
        self.topic = topic
        self.callback = callback
        self.t = None

    def start(self):
        """Plugin entrypoint"""

        self.t = threading.Thread(
            target=consume_messages, args=(self.consumer_conf, self.topic, self.callback)
        )
        self.t.daemon = True
        self.t.start()


def consume_messages(config, topic, callback):
    """Background worker thread"""
    
    consumer = KafkaUtils.create_consumer(config=config, topics=[topic])
    while True:
        KafkaUtils.consume_messages(consumer, callback)
        time.sleep(0.2)
