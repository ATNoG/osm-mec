import json
import logging
import os

from src.callbacks import load_callback_functions
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.threads.mec_apps_thread import SendMECAppsThread

logging.basicConfig(level=logging.INFO)

class MEAO:
    def __init__(self, kafka_producer_config, kafka_consumer_config):
        self.kafka_producer_config = kafka_producer_config
        self.kafka_consumer_config = kafka_consumer_config

        self.callbacks = load_callback_functions()
        self.topics = list(self.callbacks.keys())

        self.producer = KafkaUtils.create_producer(config=self.kafka_producer_config)
        self.consumer = KafkaUtils.create_consumer(config=self.kafka_consumer_config, topics=self.topics)
        

    def run(self):
        logging.info(f"Listening for messages on topics: {self.topics}")

        SendMECAppsThread(self.producer).start()

        try:
            for response in KafkaUtils.consume_messages(self.consumer, self.callbacks):
                print("Sending response: ", response)
                KafkaUtils.send_message(self.producer, "responses", response)

        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            self.producer.close()
            self.consumer.close()
            logging.info(f"Restarting Kafka...")
