import logging
from src.callbacks import load_callback_functions
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.threads.federations_info_thread import FederationsInfoThread
from src.utils.threads.federations_original_appi_ids_thread import FederationsOriginalAppiIdsThread

logging.basicConfig(level=logging.INFO)

class MetricsForwarder:
    def __init__(self, domain: str, kafka_consumer_config: dict):
        self.domain = domain

        self.kafka_consumer_config = kafka_consumer_config

        self.callbacks = load_callback_functions()
        self.topics = list(self.callbacks.keys())

        self.consumer = KafkaUtils.create_consumer(config=self.kafka_consumer_config, topics=self.topics)
        self.producers = {} # Domain: Producer

        self.federated_domains_appis = {}  # Domain: Appis
        self.original_appi_ids = {}  # Local Appi ID: Original Appi ID

    def run(self):
        logging.info(f"Listening for messages on topics: {self.topics}")

        FederationsInfoThread(self.domain ,self.producers).start()
        FederationsOriginalAppiIdsThread(self.original_appi_ids).start()

        try:
            for response in KafkaUtils.consume_messages(self.consumer, self, self.callbacks, max_workers=10):
                if response:
                    logging.info(f"Sending response: {response}")
                    # KafkaUtils.send_message(self.producer, "responses", response)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            # self.producer.close()
            self.consumer.close()
            logging.info(f"Restarting Kafka...")
