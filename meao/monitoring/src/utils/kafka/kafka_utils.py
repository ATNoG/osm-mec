import json
import os
import uuid

from kafka import KafkaConsumer, KafkaProducer

class KafkaUtils:
    @staticmethod
    def create_consumer(config: dict = {}, topics: list = []):
        consumer = KafkaConsumer(
            **config,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
        consumer.subscribe(topics=topics)
        return consumer
    
    @staticmethod
    def create_producer(config: dict = {}):
        producer = KafkaProducer(
            **config,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        return producer

    @staticmethod
    def send_message(producer, topic, message):
        #  inject a unique message id
        msg_id = str(uuid.uuid4())
        message["msg_id"] = msg_id
        producer.send(topic, message)
        return msg_id

    @staticmethod
    def consume_messages(consumer, callback):
        for message in consumer:
            response = message.value
            callback(response)
