import json
import logging
import os

from src.callbacks import load_callback_functions
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.threads.mec_apps_instances_thread import MECAppsInstancesThread
from src.utils.threads.infrastructure_info_thread import InfrastructureInfoThread

from src.utils.db import DB

logging.basicConfig(level=logging.INFO)

class MEAO:
    def __init__(self, nbi_k8s_connector, kafka_producer_config, kafka_consumer_config):
        self.nbi_k8s_connector = nbi_k8s_connector

        self.kafka_producer_config = kafka_producer_config
        self.kafka_consumer_config = kafka_consumer_config

        self.callbacks = load_callback_functions()
        self.topics = list(self.callbacks.keys())

        self.producer = KafkaUtils.create_producer(config=self.kafka_producer_config)
        self.consumer = KafkaUtils.create_consumer(config=self.kafka_consumer_config, topics=self.topics)

        self.mec_apps = {}
        self.appis = {}
        self.infrastructure_info = {}
    
    def get_mec_apps(self):
        if not self.mec_apps:
            return {}
        return self.mec_apps
    
    def get_mec_apps_instances(self):
        if not self.appis:
            return {}
        return self.appis
    
    def get_infrastructure_info(self):
        return self.infrastructure_info

    def run(self):
        logging.info(f"Listening for messages on topics: {self.topics}")

        MECAppsInstancesThread(self.producer, self.mec_apps, self.appis).start()
        InfrastructureInfoThread(self.producer, self.nbi_k8s_connector, self.infrastructure_info).start()

        try:
            for response in KafkaUtils.consume_messages(self.consumer, self, self.callbacks, max_workers=10):
                if response:
                    logging.info(f"Sending response: {response}")
                    KafkaUtils.send_message(self.producer, "responses", response)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            self.producer.close()
            self.consumer.close()
            logging.info(f"Restarting Kafka...")
