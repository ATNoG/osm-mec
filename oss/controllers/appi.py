import cherrypy
from utils.cherrypy_utils import is_valid_uuid
from utils.cherrypy_utils import is_valid_id
from utils.db import DB
from utils.kafka import KafkaUtils, producer
from utils.osm import get_osm_client
from views.appi import AppiView
import json


class AppiController:
    def __init__(self):
        self.topics = ["terminate_app_pkg"]
        self.producer = producer
        self.consumer = KafkaUtils.create_consumer(self.topics)
        self.collection = "appis"

    @cherrypy.tools.json_out()
    def list_appis(self):
        """
        /appis (GET)
        """
        return [AppiView._list(appi) for appi in get_osm_client().ns.list()]

    @cherrypy.tools.json_out()
    def get_appi(self, appi_id):
        """
        /appis/{appi_id} (GET)
        """
        if not is_valid_uuid(appi_id):
            raise cherrypy.HTTPError(404, "App instance not found")
        return AppiView._get(get_osm_client().ns.get(appi_id))
    
    @cherrypy.tools.json_out()
    def list_mec_appis(self):
        """
        /mec-appis (GET)
        """
        mec_appis = DB._list(self.collection)
        for mec_appi in mec_appis:
            if '_id' in mec_appi:
                mec_appi['_id'] = str(mec_appi['_id'])
        return mec_appis
    
    @cherrypy.tools.json_out()
    def get_mec_appi(self, appi_id):
        """
        /mec-appis/{appi_id} (GET)
        """
        if not is_valid_id(appi_id) or not DB._exists(appi_id, self.collection):
            raise cherrypy.HTTPError(404, "App instance not found")
        
        mec_appi = DB._get(appi_id, self.collection)
        if '_id' in mec_appi:
            mec_appi['_id'] = str(mec_appi['_id'])

        return mec_appi

    def terminate_appi(self, appi_id, wait=False):
        """
        /appis/{appi_id} (POST)
        """
        if not is_valid_uuid(appi_id):
            raise cherrypy.HTTPError(404, "App instance not found")
        wait = str(wait).lower() == "true"
        msg_id = KafkaUtils.send_message(
            self.producer,
            "terminate_app_pkg",
            {
                "appi_id": appi_id,
                "wait": wait,
            },
        )
        response = KafkaUtils.wait_for_response(msg_id)

        cherrypy.response.status = response["status"]
