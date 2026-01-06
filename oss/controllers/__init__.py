import importlib
import os
import json

kafka_producer_config = json.loads(os.environ.get("KAFKA_PRODUCER_CONFIG", '{"bootstrap_servers": "localhost:9092"}'))
kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))
domain = os.environ.get("DOMAIN", "ORIGIN")

def load_controllers():
    """
    Load controllers from controllers/ directory
    """

    controllers = {}
    for filename in os.listdir("controllers"):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            module = importlib.import_module(f"controllers.{module_name}")
            module_name = [name.capitalize() for name in module_name.split("_")]
            class_name = f"{''.join(module_name)}Controller"
            controllers[class_name] = getattr(module, class_name)

    return controllers
