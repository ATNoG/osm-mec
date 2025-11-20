import os
import json
import cherrypy
import logging
from app_routes import set_routes
from utils.cherrypy_utils import jsonify_error
from utils.kafka.callbacks.error_handler import callback as error_handler
from utils.kafka.callbacks.get_metrics import callback as get_metrics
from utils.threads import (KafkaConsumerThread,
                           WebSocketServiceThread)

logging.basicConfig(level=logging.INFO)

# CORS configuration
def cors_tool():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    cherrypy.response.headers["Access-Control-Allow-Headers"] = (
        "Origin, X-Requested-With, Content-Type, Accept, Authorization"
    )
    cherrypy.response.headers["Access-Control-Allow-Credentials"] = "true"
cherrypy.tools.cors = cherrypy.Tool("before_handler", cors_tool)

# Handle OPTIONS requests for CORS preflight
def handle_options_requests():
    if cherrypy.request.method == "OPTIONS":
        cherrypy.response.status = 200
        cherrypy.response.body = [b""]
        cherrypy.serving.request.handler = None  # Skip normal handler
cherrypy.tools.auto_options = cherrypy.Tool("before_handler", handle_options_requests)

def main():
    kafka_consumer_config = json.loads(os.environ.get("KAFKA_CONSUMER_CONFIG", '{"bootstrap_servers": "localhost:9092", "group_id": "monitoring", "auto_offset_reset": "latest"}'))

    KafkaConsumerThread(cherrypy.engine, kafka_consumer_config, "responses", error_handler).subscribe()
    KafkaConsumerThread(cherrypy.engine, kafka_consumer_config, "meh-metrics", get_metrics).subscribe()
    WebSocketServiceThread(cherrypy.engine).subscribe()

    dispatcher = set_routes()

    config = {
        "/": {
            "request.dispatch": dispatcher,
            "error_page.default": jsonify_error,
            "tools.auth_basic.realm": "localhost",
        }
    }

    cherrypy.tree.mount(root=None, config=config)
    cherrypy.config.update(
        {
            "tools.cors.on": True,
            "tools.auto_options.on": True,
            "server.socket_host": "0.0.0.0",
            "server.socket_port": int(os.getenv("OSS_PORT")),
        }
    )
    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    main()
