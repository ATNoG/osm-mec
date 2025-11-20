import json
import os
import subprocess
import yaml
import requests
import warnings
import time
import logging
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

    def __init__(self, domain, osm_hostname, kubectl_command, kubectl_config_path) -> None:
        self.domain = domain
        self.osm_hostname = osm_hostname
        self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
        self.kubectl_command = kubectl_command
        self.kubectl_config_path = kubectl_config_path
    
    def get_pod_status(self, namespace):
        """
        Interacts with the Kubernetes API to get information relating to every pod in a specified namespace

        Parameters
        ----------
        namespace : str
            kubernetes namespace to collect information from
        """
        command = (
            "{} --kubeconfig={} get pods -n {} -o=json".format(
                self.kubectl_command,
                self.kubectl_config_path,
                namespace,
            )
        )
        try:
            # execute the kubectl command and capture the output
            pods = json.loads(subprocess.check_output(command.split()))['items']
        except subprocess.CalledProcessError as e:
            # handle any errors if the command fails
            logging.error(f"Error executing kubectl command at get_pod_status: {e}")
        pod_status = {pod['metadata']['name']: pod['status']['phase'] for pod in pods}
        return pod_status
    
    
    def processMigrationPolicy(self, migration_policy, nodeInfo):
        """
        Process the MEC application migration policy information obtained from the OSS

        Parameters
        ----------
        migration_policy : dict
            migration policy information
        nodeInfo : dict
            dictionary storing information relating to the node in which the MEC Application is deployed
        """
        if not migration_policy["enabled"]:
            return {
                "cpu_load_thresh": None,
                "mem_load_thresh": None,
                "mobility-migration-factor": None,
            }
        
        cpu_load_thresh = None
        mem_load_thresh = None
        mobility_migration_factor = None
        if "cpu-criteria" in migration_policy:
            cpu_load_thresh = (migration_policy["cpu-criteria"]["allocated-cpu"]/nodeInfo["num_cpu_cores"])*100
            cpu_surge_capacity = (migration_policy["cpu-criteria"]["cpu-surge-capacity"]/nodeInfo["num_cpu_cores"])*100
        
        if "mem-criteria" in migration_policy:
            mem_load_thresh = ((migration_policy["mem-criteria"]["allocated-mem"]/1024)/nodeInfo["memory_size"])*100
            mem_surge_capacity = ((migration_policy["mem-criteria"]["mem-surge-capacity"]/1024)/nodeInfo["memory_size"])*100

        if "mobility-criteria" in migration_policy:
            mobility_migration_factor = migration_policy["mobility-criteria"]["mobility-migration-factor"]

        return {
            "cpu_load_thresh": cpu_load_thresh,
            "cpu_surge_capacity": cpu_surge_capacity,
            "mem_load_thresh": mem_load_thresh,
            "mem_surge_capacity": mem_surge_capacity,
            "mobility-migration-factor": mobility_migration_factor,
        }

    def get_container_info(self, appis=None):
        """
        Interacts with both OSM's NBI and the Kubernetes API to get information relating to the every OSM-deployed container

        Parameters
        ----------
        nodeSpecs : dict
            dictionary storing information relating to the cluster's nodes
        appis : dict
            MEC Application Instances information received from the OSS
        """

        container_to_app = {}
        app_metrics = {}

        # iterate through each application instance
        for appi in appis.values():
            for domain, clusters in sorted(appi.get('instances', {}).items(), key=lambda x: (x[0] != self.domain, x)):
                if domain == self.domain:
                    for cluster_id, cluster in clusters.items():
                        for kdu, node in cluster["kdus"].items():
                            command = (
                                "{} --kubeconfig={} get pods -A -l osm.etsi.org/ns-id={} -l osm.etsi.org/kdu-name={} -o=json".format(
                                    self.kubectl_command,
                                    os.path.join(self.kubectl_config_path, cluster_id),
                                    cluster["ns_id"],
                                    kdu,
                                )
                            )

                            try:
                                # Execute the kubectl command and capture the output
                                k8s_info = json.loads(subprocess.check_output(command.split()))
                            except subprocess.CalledProcessError as e:
                                # Handle any errors if the command fails
                                logging.error(f"Error executing kubectl command at get_container_info: {e}")
                                continue
                                
                            for pod in k8s_info["items"]:
                                if (
                                    ("deletionGracePeriodSeconds" in pod["metadata"] and "deletionTimestamp" in pod["metadata"]) 
                                    or "nodeName" not in pod["spec"] 
                                    or "containerStatuses" not in pod["status"]
                                ):
                                    continue

                                # iterate through each container
                                containers = pod["status"]["containerStatuses"]
                                for container in containers:
                                    if "containerID" in container:
                                        # # store the container's information in the containerInfo dictionary associated to its ID
                                        container_to_app[container["containerID"].strip('"').split('/')[-1]] = {
                                            "domain": domain,
                                            "cluster_id": cluster_id,
                                            "node": node,
                                            "appi_id": appi.get("appi_id"),
                                            "kdu": kdu,
                                            "pod": pod["metadata"]["name"],
                                            "name": container['name'],
                                        }

                                        app_metrics.setdefault(appi.get("appi_id"), {}).setdefault(kdu, {"domain": domain, "cluster": cluster_id, "node": node, "pods": {}, "metrics": {}})["pods"].setdefault(pod["metadata"]["name"], {"containers": {}, "metrics": {}})["containers"][container["containerID"].strip('"').split('/')[-1]] = {"name": container['name'], "metrics": {}}

        return container_to_app, app_metrics

    def get_federation_container_info(self, appis=None):
        """
        Interacts with both OSM's NBI and the Kubernetes API to get information relating to the every OSM-deployed container

        Parameters
        ----------
        nodeSpecs : dict
            dictionary storing information relating to the cluster's nodes
        appis : dict
            MEC Application Instances information received from the OSS
        """
        
        container_to_app = {}

        # iterate through each application instance
        for appi_id, appi in appis.items():
            domain = appi.get('domain', None)
            for cluster_id, cluster in appi.get('instances', {}).items():
                for kdu, node in cluster["kdus"].items():
                    command = (
                        "{} --kubeconfig={} get pods -A -l osm.etsi.org/ns-id={} -l osm.etsi.org/kdu-name={} -o=json".format(
                            self.kubectl_command,
                            os.path.join(self.kubectl_config_path, cluster_id),
                            cluster["ns_id"],
                            kdu,
                        )
                    )

                    try:
                        # Execute the kubectl command and capture the output
                        k8s_info = json.loads(subprocess.check_output(command.split()))
                    except subprocess.CalledProcessError as e:
                        # Handle any errors if the command fails
                        logging.error(f"Error executing kubectl command at get_federation_container_info: {e}")
                        continue
                        
                    for pod in k8s_info["items"]:
                        if (
                            ("deletionGracePeriodSeconds" in pod["metadata"] and "deletionTimestamp" in pod["metadata"]) 
                            or "nodeName" not in pod["spec"] 
                            or "containerStatuses" not in pod["status"]
                        ):
                            continue

                        # iterate through each container
                        containers = pod["status"]["containerStatuses"]
                        for container in containers:
                            if "containerID" in container:
                                # # store the container's information in the containerInfo dictionary associated to its ID
                                container_to_app[container["containerID"].strip('"').split('/')[-1]] = {
                                    "domain": domain,
                                    "cluster_id": cluster_id,
                                    "appi_id": appi_id,
                                    "kdu": kdu,
                                    "pod": pod["metadata"]["name"],
                                    "name": container['name'],
                                    "node": node,
                                }

        return container_to_app

    def getContainerInfo(self, nodeSpecs, mec_apps=None):
        """
        Interacts with both OSM's NBI and the Kubernetes API to get information relating to the every OSM-deployed container

        Parameters
        ----------
        nodeSpecs : dict
            dictionary storing information relating to the cluster's nodes
        mec_apps : dict
            MEC Application information received from the OSS
        """
        # this resets the value of the self._apiResource variable, avoiding a bug in the osmclient
        self.callNBI(self.nbi_client.__init__, host=self.osm_hostname, port=9999,sol005=True)

        # get all ns instances
        ns_instances = self.callNBI(self.nbi_client.ns.list)
        
        containerInfo = {}

        if ns_instances == None:
            logging.error(f'Error: Error calling OSM ns_instances endpoint')
            return containerInfo
        elif len(ns_instances) < 1:
            logging.info(f'No deployed ns instances')
            return containerInfo
        elif 'code' in ns_instances[0].keys():
            logging.error(f'Error: Error calling OSM ns_instances endpoint')
            return containerInfo

        # iterate through each ns instance
        for ns_instance in ns_instances:
            if ("deployed" not in ns_instance["_admin"]
                or "K8s" not in ns_instance["_admin"]["deployed"]
                or not ns_instance["_admin"]["deployed"]["K8s"]
                or len(ns_instance["_admin"]["deployed"]["K8s"]) == 0
            ):
                continue
            ns_id = ns_instance["_id"]

            # get all associated vnf instances
            vnf_ids = ns_instance["constituent-vnfr-ref"]
            vnf_instances = {}
            for vnf_id in vnf_ids:
                vnfContent = self.callNBI(self.nbi_client.vnf.get, vnf_id)
                if vnfContent:
                    vnf_instances[vnfContent["member-vnf-index-ref"]] = vnfContent["_id"]

            # get all associated kdu instances
            kdu_instances = ns_instance["_admin"]["deployed"]["K8s"]                
            namespace = kdu_instances[0]["namespace"]

            # get all associated kubernetes pods
            command = (
                "{} --kubeconfig={} --namespace={} get pods -l osm.etsi.org/ns-id={} -o=json".format(
                    self.kubectl_command,
                    self.kubectl_config_path,
                    namespace,
                    ns_id,
                )
            )
            try:
                # Execute the kubectl command and capture the output
                k8s_info = json.loads(subprocess.check_output(command.split()))
            except subprocess.CalledProcessError as e:
                # Handle any errors if the command fails
                logging.error(f"Error executing kubectl command at getContainerInfo: {e}")
                return containerInfo

            # iterate through each kdu instance
            for kdu in kdu_instances:
                kdu_instance = kdu["kdu-instance"]
                member_vnf_index = kdu["member-vnf-index"]
                vnf_id = vnf_instances[member_vnf_index]
                
                # iterate through each kubernetes pod
                for pod in k8s_info["items"]:
                    if (
                        ("deletionGracePeriodSeconds" in pod["metadata"] and "deletionTimestamp" in pod["metadata"]) 
                        or "nodeName" not in pod["spec"] 
                        or "containerStatuses" not in pod["status"]
                    ):
                        continue

                    # find the corresponding mec app and process its migration policy
                    nodeName = pod["spec"]["nodeName"]
                    migration_policy = None
                    if mec_apps:
                        for mec_app in mec_apps.values():
                            if (mec_app["appi_id"] == ns_id
                                and mec_app["vnf_id"] == vnf_id
                                and mec_app["kdu_id"] == kdu_instance
                                and nodeName in nodeSpecs
                            ):
                                migration_policy = self.processMigrationPolicy(mec_app["migration_policy"], nodeSpecs[nodeName])
                                break

                    # iterate through each container
                    containers = pod["status"]["containerStatuses"]
                    for container in containers:
                        if "containerID" in container:
                            # store the container's information in the containerInfo dictionary associated to its ID
                            containerInfo[container["containerID"].strip('"').split('/')[-1]] = {
                                "ns_id": ns_id,
                                "vnf_id": vnf_id,
                                "kdu_id": kdu_instance,
                                "node": nodeName,
                                "migration_policy": migration_policy,
                            }

        return containerInfo
    
    def migrate(self, cName, container, node):
        """
        Interacts with OSM's NBI to schedule a migration operation

        Parameters
        ----------
        cName : str
            the migrating container's ID
        container : dict
            information relating to the migrating container, obtained from the containerInfo dictionary
        node: str
            name of the migration target node
        """
        try:
            return self.callNBI(
                self.nbi_client.ns.migrate,
                container["ns_id"],
                migrate_dict = {
                    "vnfInstanceId": container["vnf_id"],
                    "targetHostK8sLabels": {
                        "kubernetes.io/hostname": node,
                    },
                    "vdu": {
                        "vduId": container["kdu_id"],
                        "vduCountIndex": 0,
                    }
                })
        except Exception as e:
            logging.error(f"Error: {e}")

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
            logging.error(f"Error finding nslcmop: {e}")
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
            except (OsmHttpException) as e:
                logging.error(f"An error occurred: {e}")
                self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
                tries += 1
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                return None