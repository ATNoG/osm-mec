import os
import json
import cherrypy
import cherrypy_cors
from app_routes import set_routes
from utils.cherrypy_utils import jsonify_error
from utils.kafka.callbacks.error_handler import callback as error_handler
from utils.kafka.callbacks.get_metrics import callback as get_metrics
from utils.threads import (KafkaConsumerThread,
                           WebSocketServiceThread)


def main():
    cherrypy_cors.install()

    kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

    KafkaConsumerThread(cherrypy.engine, kafka_consumer_config, "responses", error_handler).subscribe()
    # KafkaConsumerThread(cherrypy.engine, kafka_consumer_config, "meh-metrics", get_metrics).subscribe()   # TODO: Update for new metrics format
    WebSocketServiceThread(cherrypy.engine).subscribe()

    dispatcher = set_routes()

    config = {
        "/": {
            "request.dispatch": dispatcher,
            "error_page.default": jsonify_error,
            "cors.expose.on": True,
            # "tools.auth_basic.on": True,
            "tools.auth_basic.realm": "localhost",
        }
    }

    cherrypy.tree.mount(root=None, config=config)
    cherrypy.config.update(
        {
            "server.socket_host": "0.0.0.0",
            "server.socket_port": int(os.getenv("OSS_PORT")),
        }
    )
    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    main()
