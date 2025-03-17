import os
from src.utils.nbi_k8s_connector import NBIConnector
from src.meao import MEAO
from flask import Flask, jsonify
import json

app = Flask(__name__)
meao: MEAO = None

def main():
    nbi_k8s_connector = NBIConnector(
        os.environ.get("OSM_HOSTNAME"),
        os.environ.get("KUBECTL_COMMAND"),
        os.environ.get("KUBECTL_CONFIG_PATH")
    )

    kafka_producer_config = json.loads(os.environ.get("KAFKA_PRODUCER_CONFIG", '{"bootstrap_servers": "localhost:9092"}'))
    kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

    meao = MEAO(
        nbi_k8s_connector,
        os.environ.get("RAW_METRICS_KAFKA_TOPIC"),
        os.environ.get("UE_LATENCY_KAFKA_TOPIC"),
        os.environ.get("MEH_METRICS_KAFKA_TOPIC"),
        int(os.environ.get("SEND_CONTAINER_INFO_FREQ")),
        kafka_consumer_config,
        kafka_producer_config
    )

    meao.start()

    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
