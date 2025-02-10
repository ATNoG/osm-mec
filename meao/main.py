import json
import logging
import os

from callbacks import load_callback_functions
from kafka import KafkaConsumer, KafkaProducer
from utils.db import DatabaseInitializer

logging.basicConfig(level=logging.INFO)


def main():
    while True:
        kafka_producer_config = json.loads(os.environ.get("KAFKA_PRODUCER_CONFIG", '{"bootstrap_servers": "localhost:9092"}'))
        kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))
        producer = KafkaProducer(
            **kafka_producer_config,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        consumer = KafkaConsumer(
            **kafka_consumer_config,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )

        callbacks = load_callback_functions()

        topics = list(callbacks.keys())
        consumer.subscribe(topics=topics)

        logging.info(f"Listening for messages on topics: {topics}")
        try:
            for message in consumer:
                logging.info(f"Received message: {message.value}")
                topic = message.topic
                if topic in callbacks:
                    callback_function = callbacks[topic]
                    response = callback_function(message.value)
                    producer.send("responses", value=response)
                    logging.info(f"Sent response: {response}")

        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            producer.close()
            consumer.close()
            logging.info(f"Restarting Kafka...")


if __name__ == "__main__":
    DatabaseInitializer.initialize_database()
    main()
