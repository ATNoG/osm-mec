import json
import os
import uuid

from kafka import KafkaConsumer, KafkaProducer
from cherrypy import HTTPError

from .callbacks.error_handler import responses

class KafkaUtils:
    @staticmethod
    def create_consumer(config: dict = {}, topics: list = [], seek_to_end: bool = True):
        consumer = KafkaConsumer(
            **config,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
        consumer.subscribe(topics=topics)

        if seek_to_end:
            # Only consume new messages
            consumer.poll(timeout_ms=1000)
            for tp in consumer.assignment():
                consumer.seek_to_end(tp)

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


    @staticmethod
    def wait_for_response(msg_id=None):
        if msg_id and msg_id not in responses:
            responses[msg_id] = None

            # poll until response is received
            while responses[msg_id] is None:
                pass

            response = responses.pop(msg_id)

            if response.get("error"):
                raise HTTPError(response["status"], response["error"])
            return response
        else:
            raise HTTPError(400, "msg_id not found")
