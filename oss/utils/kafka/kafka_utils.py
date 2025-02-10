import json
import os
import uuid

from cherrypy import HTTPError
from kafka import KafkaConsumer, KafkaProducer

from .callbacks.error_handler import responses

kafka_producer_config = json.loads(os.environ.get("KAFKA_PRODUCER_CONFIG", '{"bootstrap_servers": "localhost:9092"}'))
kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

producer = KafkaProducer(
    **kafka_producer_config,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

class KafkaUtils:
    @staticmethod
    def create_consumer(topics):
        consumer = KafkaConsumer(
            **kafka_consumer_config,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
        consumer.subscribe(topics=topics)
        return consumer

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
