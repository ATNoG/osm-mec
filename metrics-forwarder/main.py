import json
import os
from src.forwarder import MetricsForwarder

def main():
    domain = os.environ.get("DOMAIN", "DEFAULT_DOMAIN")
    kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

    # Start the metrics forwarder
    forwarder = MetricsForwarder(domain=domain, kafka_consumer_config=kafka_consumer_config)
    forwarder.run()
    
if __name__ == "__main__":
    main()
