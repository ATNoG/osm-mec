import logging
import os

from osmclient import client

def get_osm_client():
    return client.Client(host=os.getenv("OSM_HOSTNAME"), sol005=True)

def get_vnf_descriptor(vnf_pkg_id):
    try:
        vnf_descriptor = get_osm_client().vnfd.get(vnf_pkg_id)
    except Exception as e:
        logging.error(f"Error getting the VNF descriptor: {e}")
        vnf_descriptor = None
        
    return vnf_descriptor
