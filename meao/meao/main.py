import logging
import json
import os

from src.utils.db import DatabaseInitializer
from src.meao import MEAO

if __name__ == "__main__":
    kafka_producer_config = json.loads(os.environ.get("KAFKA_PRODUCER_CONFIG", '{"bootstrap_servers": "localhost:9092"}'))
    kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

    DatabaseInitializer.initialize_database()
    meao = MEAO(kafka_producer_config=kafka_producer_config, kafka_consumer_config=kafka_consumer_config)
    meao.run()
