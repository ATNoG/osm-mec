import hashlib
import json
import logging
import orjson
import os
import subprocess
import yaml
import requests
import warnings
import time
from osmclient import client
from osmclient.common.exceptions import ClientException, OsmHttpException

DOMAIN = "IT_AVEIRO"

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
        self.files_hash = {}
    
    def get_clusters(self):
        return self.callNBI(self.nbi_client.k8scluster.list)

    def _hash_credentials(self, credentials):
        """Generate a hash for the given credentials"""
        return hashlib.blake2b(orjson.dumps(credentials, option=orjson.OPT_SORT_KEYS), digest_size=16).hexdigest()
    
    def save_credentials(self, cluster_id, credentials):
        """Save the credentials to a file"""
        hash_value = self._hash_credentials(credentials)
        if self.files_hash.get(cluster_id) == hash_value:
            return
        
        self.files_hash[cluster_id] = hash_value
        path = os.path.join(self.kubectl_config_path, cluster_id)
        with open(path, "w", buffering=1_048_576) as file:
            yaml.dump(credentials, file)
    
    
    def getNodeSpecs(self, cluster_id):
        """
        Interacts with the Kubernetes API to get information relating to the cluster's nodes and the corresponding cadvisor pods
        """
        nodeSpecs = {}

        command = (
            "{} --kubeconfig={} get nodes -o=json".format(
                self.kubectl_command,
                os.path.join(self.kubectl_config_path, cluster_id),
            )
        )
        try:
            # execute the kubectl command and capture the output
            node_info = json.loads(subprocess.check_output(command.split()))
        except subprocess.CalledProcessError as e:
            # handle any errors if the command fails
            print("Error executing kubectl command:", e)
            return nodeSpecs
        
        for node in node_info["items"]:
            nodeSpecs[node["metadata"]["labels"]["kubernetes.io/hostname"]] = {
                "num_cpu_cores": round(int(node["status"]["allocatable"]["cpu"]), 2),
                "memory_size": round(int(node["status"]["allocatable"]["memory"][:-2])/1024, 2),
            }

        command = (
            "{} --kubeconfig={} -n cadvisor get pods -o=json".format(
                self.kubectl_command,
                os.path.join(self.kubectl_config_path, cluster_id),
            )
        )
        try:
            # execute the kubectl command and capture the output
            cadvisor_pods = json.loads(subprocess.check_output(command.split()))
        except subprocess.CalledProcessError as e:
            # handle any errors if the command fails
            print("Error executing kubectl command:", e)
            return nodeSpecs

        for cadvisor_pod in cadvisor_pods["items"]:
            if "nodeName" in cadvisor_pod["spec"]:
                nodeSpecs[cadvisor_pod["spec"]["nodeName"]]["cadvisor"] = cadvisor_pod["metadata"]["name"]

        return nodeSpecs
    

    def get_kdu_pods(self, cluster_id: str, namespace: str, ns_id: str, kdu_name: str, node: str = None):
        pods = []

        # get all associated kubernetes pods
        command = (
            "{} --kubeconfig={} --namespace={} get pods -l osm.etsi.org/ns-id={} -l osm.etsi.org/kdu-name={} {} -o=json".format(
                self.kubectl_command,
                os.path.join(self.kubectl_config_path, cluster_id),
                namespace,
                ns_id,
                kdu_name,
                f"--field-selector=spec.nodeName={node}" if node else "",
            )
        )

        try:
            # Execute the kubectl command and capture the output
            pods = json.loads(subprocess.check_output(command.split())).get("items", [])
        except subprocess.CalledProcessError as e:
            return pods

        return pods
    
    def migrate(self, ns_id, vnf_id, kdu_id, kdu_index, node):
        """
        Interacts with OSM's NBI to schedule a migration operation between two nodes within the same cluster

        Parameters
        ----------
        ns_id : str
            the ID of the ns instance
        vnf_id : str
            the ID of the vnf instance
        kdu_id : str
            the ID of the kdu instance
        kdu_index : str
            the index of the kdu instance
        node : str
            the name of the node to which the kdu instance will be migrated
        """

        try:
            data = {
                "vnfInstanceId": vnf_id,
                "targetHostK8sLabels": {
                    "kubernetes.io/hostname": node,
                },
                "vdu": {
                    "vduId": kdu_id,
                    "vduCountIndex": kdu_index,
                }
            }

            url = f"http://{self.osm_hostname}/osm/nslcm/v1/ns_instances/{ns_id}/migrate"
            self.call_nbi_api(url, method="POST", data=data)

        except Exception as e:
            print("ERROR: {}".format(e))
    

    def ns_scale(self, ns_id: str, data: dict):
        """
        Interacts with OSM's NBI to disable a kdu instance

        Parameters
        ----------
        ns_id : str
            the ID of the ns instance
        data : dict
            contains the kdu instance ID and the scaling action
        """

        url = f"http://{self.osm_hostname}/osm/nslcm/v1/ns_instances/{ns_id}/scale"
        response = self.call_nbi_api(url, method="POST", data=data)
        if not response:
            return {"error": "Failed to disable kdu instance"}
        return response

    def delete_network_service(self, ns_id: str, wait: bool = False):
        """
        Interacts with OSM's NBI to delete a network service instance
        Parameters
        ----------
        ns_id : str
            the ID of the ns instance
        wait : bool
            whether to wait for the operation to complete (default is False)
        """
        self.callNBI(self.nbi_client.ns.delete, ns_id, wait=wait)

    def getOperationState(self, op_id):
        """
        Interacts with OSM's NBI to obtain the status of an nslcmop

        Parameters
        ----------
        op_id : str
            the ID of the nslcmop
        """
        try:
            return self.callNBI(self.nbi_client.ns.get_op, op_id)["operationState"]
        except Exception as e:
            print("Error finding nslcmop:", e)
            return "NOT FOUND"
        
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
            except Exception as e:
                print(f"An error occurred: {e}")
                self.nbi_client = client.Client(host=self.osm_hostname, port=9999, sol005=True)
                tries += 1
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
                self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
                tries += 1
        return {"error": "Failed to call NBI API"}
