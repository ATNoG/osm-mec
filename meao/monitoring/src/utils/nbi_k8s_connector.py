import json
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
        self.kubectl_command = kubectl_command
        self.kubectl_config_path = kubectl_config_path
        self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
        kubectl_config = None
        while not kubectl_config:
            kubectl_config = self.getKubeConfig()
        with open(self.kubectl_config_path, 'w') as file:
            yaml.dump(kubectl_config["credentials"], file)
    
    def getKubeConfig(self):
        """
        Interacts with OSM's NBI to get the kube config to be used by the kubectl command to interact with the cluster
        """
        kubectl_config = None
        try:
            kubectl_config = self.callNBI(self.nbi_client.k8scluster.list)[0]
        except Exception as e:
            print("ERROR: Could not get kube config: {}".format(e))
            time.sleep(5)

        return kubectl_config
    
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
            print("Error executing kubectl command:", e)
        pod_status = {pod['metadata']['name']: pod['status']['phase'] for pod in pods}
        return pod_status
    
    def getNodeSpecs(self):
        """
        Interacts with the Kubernetes API to get information relating to the cluster's nodes and the corresponding cadvisor pods
        """
        nodeSpecs = {}

        command = (
            "{} --kubeconfig={} get nodes -o=json".format(
                self.kubectl_command,
                self.kubectl_config_path,
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
                "num_cpu_cores": int(node["status"]["allocatable"]["cpu"]),
                "memory_size": int(node["status"]["allocatable"]["memory"][:-2])/pow(1024,2),
            }

        command = (
            "{} --kubeconfig={} -n cadvisor get pods -o=json".format(
                self.kubectl_command,
                self.kubectl_config_path,
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
            print('ERROR: Error calling OSM ns_instances endpoint')
            return containerInfo
        elif len(ns_instances) < 1:
            print('INFO: No deployed ns instances')
            return containerInfo
        elif 'code' in ns_instances[0].keys():
            print('ERROR: Error calling OSM ns_instances endpoint')
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
                print("Error executing kubectl command:", e)
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
                        for mec_app in mec_apps:
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
        print("MIGRATING CONTAINER TO NODE {}".format(node))
        print("CONTAINER ID: {}".format(cName))
        print("NETWORK SERVICE ID: {}".format(container["ns_id"]))
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
            print("ERROR: {}".format(e))

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
            except (OsmHttpException) as e:
                print(f"An error occurred: {e}")
                self.nbi_client = client.Client(host=self.osm_hostname, port=9999,sol005=True)
                tries += 1
            except Exception as e:
                print(f"An error occurred: {e}")
                return None