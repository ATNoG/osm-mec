import logging
import json
import os

# thread
import threading

from src.utils.db import DatabaseInitializer
from src.meao import MEAO
import src.api as api

from src.utils.nbi_k8s_connector import NBIConnector

def main():
    os.makedirs(os.environ.get("KUBECTL_CONFIG_PATH"), exist_ok=True)
    
    domain = os.environ.get("DOMAIN", "DEFAULT_DOMAIN")
    nbi_k8s_connector = NBIConnector(
        os.environ.get("OSM_HOSTNAME"),
        os.environ.get("KUBECTL_COMMAND"),
        os.environ.get("KUBECTL_CONFIG_PATH")
    )

    kafka_producer_config = json.loads(os.environ.get("KAFKA_PRODUCER_CONFIG", '{"bootstrap_servers": "localhost:9092"}'))
    kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

    DatabaseInitializer.initialize_database()
    meao = MEAO(domain, nbi_k8s_connector, kafka_producer_config=kafka_producer_config, kafka_consumer_config=kafka_consumer_config)

    # Flask API
    threading.Thread(target=api.run, args=(meao,)).start()
    # Start MEAO
    meao.run()
    
if __name__ == "__main__":
    main()
