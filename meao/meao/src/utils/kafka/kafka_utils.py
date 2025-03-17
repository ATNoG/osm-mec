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
        if not "msg_id" in message:
            message["msg_id"] = str(uuid.uuid4())
        producer.send(topic, message)

    @staticmethod
    def consume_messages(consumer, callbacks: dict):
        for message in consumer:
            print("Received Message: ", message)
            if message.topic in callbacks:
                callback_function = callbacks[message.topic]
                response = callback_function(message.value)
                yield response
