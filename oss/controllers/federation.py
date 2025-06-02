import cherrypy
from utils.kafka.kafka_utils import KafkaUtils
from utils.db import DB, db_federation
from . import kafka_producer_config
from urllib.parse import urlparse
from views.federation import FederationView


def is_valid_url(url):
    parsed = urlparse(url)
    return all([parsed.scheme in ("http", "https"), parsed.netloc])

class FederationController:
    def __init__(self):
        """
        Initializes the FederationController with Kafka producer configuration.
        :param kafka_producer_config: Configuration for the Kafka producer.
        """
        self.producer = KafkaUtils.create_producer(kafka_producer_config)

    @cherrypy.tools.json_out()
    def new_federation(self, federation_endpoint: str, authentication_endpoint: str, client_id: str, client_secret: str):
        """
        Creates a new federation configuration.
        :param federation_endpoint: The endpoint for the federation.
        :param authentication_endpoint: The endpoint for authentication.
        :param client_id: The client ID for the federation.
        :param client_secret: The client secret for the federation.
        
        /federation/ (POST)
        """

        if not all([is_valid_url(authentication_endpoint), is_valid_url(federation_endpoint)]):
            cherrypy.response.status = 400
            return {"status": "error", "message": "Invalid URL format for federation or authentication endpoint."}
        
        msg_id = KafkaUtils.send_message(
            self.producer,
            "new_federation",
            {
                "federation_endpoint": federation_endpoint,
                "auth_endpoint": authentication_endpoint,
                "client_id": client_id,
                "client_secret": client_secret
            }
        )
        response = KafkaUtils.wait_for_response(msg_id)

        if response["status"] != 201:
            cherrypy.response.status = response["status"]
            return {"status": "error", "message": response.get("message", "Failed to create federation.")}

        cherrypy.response.status = 201
        return {"status": "success", "message": "Federation created successfully."}
    
    def get_federation(self, federation_id: str):
        """
        Retrieves a federation configuration by its ID.
        :param federation_id: The ID of the federation to retrieve.
        
        /federation/{federation_id} (GET)
        """
        if not DB._exists(federation_id, "federations", db=db_federation):
            cherrypy.response.status = 404
            return {"status": "error", "message": "Federation not found."}

        federation = DB._get(federation_id, "federations", db=db_federation)
        return FederationView._get(federation)

    @cherrypy.tools.json_out()
    def list_federations(self):
        """
        Lists all federations.
        
        /federation/ (GET)
        """

        federations = DB._list("federations", db=db_federation)
        return [FederationView._list(federation) for federation in federations]
    
    @cherrypy.tools.json_out()
    def delete_federation(self, federation_id: str):
        """
        Deletes a federation configuration.
        :param federation_id: The ID of the federation to delete.
        
        /federation/{federation_id} (DELETE)
        """
        if not DB._exists(federation_id, "federations", db=db_federation):
            cherrypy.response.status = 404
            return {"status": "error", "message": "Federation not found."}

        msg_id = KafkaUtils.send_message(
            self.producer,
            "delete_federation",
            {"federation_id": federation_id}
        )
        response = KafkaUtils.wait_for_response(msg_id)

        if response["status"] != 200:
            cherrypy.response.status = response["status"]
            return {"status": "error", "message": response.get("message", "Failed to delete federation.")}

        DB._delete(federation_id, "federations", db=db_federation)
        cherrypy.response.status = 200
        return {"status": "success", "message": "Federation deleted successfully."}
    