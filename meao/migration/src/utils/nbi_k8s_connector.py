import json
import os
import subprocess
import yaml
import requests
import warnings
import time
from osmclient import client
from osmclient.common.exceptions import ClientException, OsmHttpException

class NBIConnector:
    """
    This class provides functions for simplifying interactions with OSM's NBI and the Kubernetes API

    ...

    Attributes
    ----------
    osm_hostname : str
        IP address to be used to communicate with OSM's NBI
    kubectl_command : str
        path to kubectl command
    kubectl_config_path : str
        path to store the kube config to be used by the kubectl command to interact with the cluster
    nbi_client : osmclient.Client
        instance of OSM Client to be used to communicate with OSM's NBI
    """

    def __init__(self, osm_hostname, kubectl_command, kubectl_config_path) -> None:
        self.osm_hostname = osm_hostname
        self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
        self.kubectl_command = kubectl_command
        self.kubectl_config_path = kubectl_config_path


    def callNBI(self, func, *args, **kwargs):
        """
        Function to simplify interactions with OSM's NBI

        Parameters
        ----------
        func : callable
            the function that will be executed within the `callNBI` method.
        
        *args : tuple
            positional arguments that will be passed to the `func` when it is called.
            
        **kwargs : dict
            keyword arguments that will be passed to the `func` when it is called.
        """
        tries = 0
        while tries < 5:
            try:
                return func(*args, **kwargs)
            except (OsmHttpException) as e:
                print(f"An error occurred: {e}")
                self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
                tries += 1
            except Exception as e:
                print(f"An error occurred: {e}")
                return None
    

    def call_nbi_api(self, url, method="GET", data=None):
        """
        Function to simplify interactions with OSM's NBI

        Parameters
        ----------
        url : str
            the URL of the API endpoint to be called.
        
        method : str
            the HTTP method to be used for the request (default is "GET").
        
        data : dict
            the data to be sent in the request body (default is None).
        """
        tries = 0
        while tries < 5:
            try:
                headers = {"Authorization": f"Bearer {self.nbi_client.get_token().get('id', '')}"}
                response = requests.request(method, url, headers=headers, json=data, verify=False)
                return {"status": response.status_code, "message": response.text}
            except Exception as e:
                # logging.info(f"An error occurred at call_nbi_api: {e}")
                self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
                tries += 1
        return {"error": "Failed to call NBI API"}
