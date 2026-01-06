import json
import os
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading

from kafka import KafkaConsumer, KafkaProducer

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
        if not "msg_id" in message:
            message["msg_id"] = str(uuid.uuid4())
        producer.send(topic, message)
        return message.pop("msg_id", None)

    @staticmethod
    def consume_messages(consumer, data, callbacks: dict, max_workers=5):
        result_queue = Queue()
        executor = ThreadPoolExecutor(max_workers=max_workers)

        def consume_and_submit():
            for message in consumer:
                if message.topic in callbacks:
                    # if message.topic == "responses":
                    #     logging.info(f"Received response from topic {message.topic}: {message.value}")
                    logging.info(f"Received message from topic {message.topic}: {message.value}")
                    callback_function = callbacks[message.topic]
                    future = executor.submit(KafkaUtils._process_message, callback_function, data, message.value)
                    future.add_done_callback(lambda fut: result_queue.put(fut.result()))

        threading.Thread(target=consume_and_submit, daemon=True).start()

        while True:
            result = result_queue.get()
            yield result
    
    @staticmethod
    def _process_message(callback_function, data, message_value):
        return callback_function(data, message_value)
