import datetime
import threading
import uuid
from src.utils.appd_validation import *
from src.utils.capture_io import CaptureIO
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.file_management import *
from src.utils.osm import get_osm_client, get_vnf_descriptor
import time
import random
import yaml
import copy

@handle_exceptions
def callback(meao, message):
    app_pkg_id = message.get("app_pkg_id")
    vim_id = message.get("vim_id")
    name = message.get("name")
    description = message.get("description")
    config = yaml_string_to_dict(message.get("config", "") or "")
    wait = message.get("wait")
    original_domain = message.get("original_domain", meao.domain)

    if app_pkg_id and name and description:
        app_pkg = DB._get(id=app_pkg_id, collection="app_pkgs")
        ns_pkg_id = app_pkg.get("ns_pkg_id")
        vnf_pkg_id = app_pkg.get("vnf_pkg_id")
        migration_policy = app_pkg.get("migration_policy")

        vnf_pkg_descriptor = get_vnf_descriptor(vnf_pkg_id)
        if not vnf_pkg_descriptor:
            return {"status": 404, "error": "Error getting the VNF descriptor"}

        # Get kdus and select the nodes for those who are enabled
        kdus = {kdu["name"]: kdu for kdu in vnf_pkg_descriptor.get("kdu", [])}
        
        config = default_config(config, str(app_pkg["appd_id"] + "-vnf"), kdus.keys())
        # Remove the KDUs that are not enabled
        for vnf in config.get("additionalParamsForVnf"):
            for kdu in vnf.get("additionalParamsForKdu"):
                kdus[kdu["kdu_name"]]["enable"] = kdu.get("enable", True)
                kdus[kdu["kdu_name"]]["node-selector"] = kdu.get("node-selector", None)

        # Select the nodes for the active KDUs
        kdu_nodes = {}
        for kdu_name, kdu in kdus.items():
            if kdu.get("enable"):
                _pre_node_selector = kdu.get("node-selector") or {}
                pre_selected_node = _pre_node_selector.get("kubernetes.io/hostname", None)
                kdu_nodes[kdu_name] = select_node(infrastructure_info=meao.infrastructure_info, vim_id=vim_id, pre_selected_node=pre_selected_node)
                if not kdu_nodes[kdu_name]:
                    return {"status": 404, "error": "No nodes available to satisfy all the requirements"}
                kdu["status"] = "instantiating"
            else:
                kdu["status"] = "disabled"

        # Get the needed network services
        needed_instances = join_by_cluster(kdus.values(), kdu_nodes)

        # O id da mec-app tem de ser diferente do id da network service (O que faz com que não exista uma NS principal e permite ter um código mais geral)
        appi_id = str(uuid.uuid4())

        # Launch each network service in each cluster going firstly to the domain of this MEAO
        instances = {}
        for domain, clusters in sorted(needed_instances.items(), key=lambda x: (x != meao.domain, x)):
            for cluster, _kdus in clusters.items():
                # Use the default config as base
                cluster_config = copy.deepcopy(config)

                # Extract the names of KDUs to enable
                ns_kdus = {kdu["name"]: kdu for kdu in _kdus}

                # Create a custom config for each cluster
                for vnf in cluster_config.get("additionalParamsForVnf", []):
                    for kdu in vnf.get("additionalParamsForKdu", []):
                        kdu_name = kdu.get("kdu_name")
                        if kdu_name in ns_kdus:
                            kdu["enable"] = True
                            kdu["node-selector"] = {"kubernetes.io/hostname": kdu_nodes.get(kdu_name, {}).get("node")}
                        else:
                            kdu["enable"] = False
                            kdu.pop("node-selector", None)
                
                # Convert the config to a YAML string
                cluster_config = dict_to_yaml_string(cluster_config)

                with CaptureIO() as out:
                    meao.nbi_k8s_connector.callNBI(
                        meao.nbi_k8s_connector.nbi_client.ns.create,
                        nsd_name=ns_pkg_id,
                        nsr_name=name,
                        account=meao.infrastructure_info[cluster]["vim-account"],
                        description=description,
                        config=cluster_config,
                        wait=wait,
                    )

                instance_id = out[0]
                vnf_id = meao.nbi_k8s_connector.callNBI(
                    meao.nbi_k8s_connector.nbi_client.vnf.list,
                    ns=instance_id
                )[0]["_id"]

                for kdu_name in ns_kdus:
                    instances.setdefault(domain, {}).setdefault(cluster, {"ns_id": instance_id, "vnf_id": vnf_id, "kdus": {}})
                    instances[domain][cluster]["kdus"][kdu_name] = kdu_nodes[kdu_name]["node"]

                    # Update the nodes allocated resources in the database
                    DB._general_update_by("resources", {"cluster": cluster, "node": kdu_nodes[kdu_name]["node"]}, {"$inc": {"allocated-cpu": migration_policy.get(kdu_name, {}).get("cpu-criteria", {}).get("allocated-cpu", 0), "allocated-mem": migration_policy.get(kdu_name, {}).get("mem-criteria", {}).get("allocated-mem", 0)}})

        # Add the appi to the database
        db_id = DB._add(
            collection="appis",
            data={
                "appi_id": appi_id,
                "kdus": kdus,
                "name": name,
                "description": description,
                "config": config,
                "app_pkg_id": app_pkg_id,
                "vnf_pkg_id": vnf_pkg_id,
                "ns_pkg_id": ns_pkg_id,
                "migration_policy": migration_policy,
                "instances": instances,
                "operational-status": "init",
                "config-status": "init",  
                "details": "",
                "domain": original_domain,
                "created-at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
        )
        
        thread = threading.Thread(target=check_appi_instantiation, args=(meao, {"_id": db_id, "appi_id": appi_id, "kdus": kdus, "instances": instances, "domain": meao.domain},))
        thread.start()
        
        if original_domain and original_domain != meao.domain:  # If the appi is being instantiated in a different domain, send the message to the federator
            thread.join()

        return {"status": 201, "appi_id": appi_id}


def select_node(infrastructure_info: dict, vim_id: str = None, pre_selected_node: str = None, strategy: str = 'random'):
    """
    Select a node based on the given strategy."
    """
    
    # If there is not infrastructure available, it is not possible to select a node
    if infrastructure_info == {}:
        return None
    
    # If there is no vim_id, apply the strategy to all nodes, otherwise filter by vim_id
    nodes = []
    for cluster_id, cluster_data in infrastructure_info.items():
        if vim_id and cluster_data.get("vim-account") != vim_id:
            continue
        domain = cluster_data.get("domain")
        for node_name, node_data in cluster_data.get("nodeSpecs", {}).items():
            if pre_selected_node and node_name != pre_selected_node:
                continue
            nodes.append((domain, cluster_id, node_name, node_data))
    
    if nodes == []:
        return None
    
    # Strategy to select the node
    if strategy == 'random':
        domain, cluster_id, node_name = random.choice(nodes)[:3]
    # elif strategy == 'max_memory':
    #     return max(nodes, key=lambda x: x[2].get("memory_size", 0))[:3]
    # elif strategy == 'max_cpu':
    #     return max(nodes, key=lambda x: x[2].get("num_cpu_cores", 0))[:3]
    # else:
    #     raise ValueError("Invalid strategy. Choose from 'random', 'max_memory', or 'max_cpu'.")
    
    return {"domain": domain, "cluster": cluster_id, "node": node_name}


def default_config(config: dict = {}, member_vnf_index: str = None, kdus: set = set()):
    """
    Set default values for the configuration.
    """

    config["additionalParamsForVnf"] = [
        item for item in config.get("additionalParamsForVnf", [])
        if item.get("member-vnf-index") == member_vnf_index
    ]
    
    # If it doesn't exist, create a new entry
    if len(config["additionalParamsForVnf"]) == 1:
        vnf_entry = config["additionalParamsForVnf"][0]
    elif len(config["additionalParamsForVnf"]) < 1:
        vnf_entry = {
            "member-vnf-index": member_vnf_index,
        }
        config["additionalParamsForVnf"].append(vnf_entry)
    else:
        raise ValueError("The config contains multiple entries for the same member-vnf-index")
    
    # Set default values for the VNF entry
    vnf_entry["additionalParamsForKdu"] = [
        item for item in vnf_entry.get("additionalParamsForKdu", [])
        if item.get("kdu_name") in kdus
    ]
    
    # Check if there are multiple entries for the same kdu_name
    kdus_with_params = [kdu["kdu_name"] for kdu in vnf_entry.get("additionalParamsForKdu", [])]
    len_kdus_with_params = len(kdus_with_params)
    kdu_with_params = set(kdus_with_params)
    if len_kdus_with_params != len(kdu_with_params):
        raise ValueError("The config contains multiple entries for the same kdu_name")
    
    # Ensure each kdu is present under additionalParamsForKdu
    for kdu_name in kdus:
        if kdu_name not in kdus_with_params:
            # Append default structure for the KDU
            vnf_entry["additionalParamsForKdu"].append({
                "kdu_name": kdu_name,
                "enable": True,
            })

    return config

def yaml_string_to_dict(yaml_string: str):
    """
    Convert a YAML string to a dictionary.
    """
    try:
        result =  yaml.safe_load(yaml_string)
        return result if result is not None else {}
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}")

def dict_to_yaml_string(data: dict) -> str:
    """
    Convert a dictionary to a YAML string.
    """
    try:
        yaml_string = "" if data == {} else yaml.dump(data, default_flow_style=False)
        return yaml_string
    except yaml.YAMLError as e:
        raise ValueError(f"Error converting to YAML: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}")
    
def join_by_cluster(kdus: list, nodes: dict):
    """
    Join the data by domain and cluster to create the network services structure.
    """
    result = {}
    for kdu in kdus:
        if not kdu.get("enable"):
            continue
        if not result.get(nodes[kdu["name"]]["domain"]):
            result[nodes[kdu["name"]]["domain"]] = {}
        if not result[nodes[kdu["name"]]["domain"]].get(nodes[kdu["name"]]["cluster"]):
            result[nodes[kdu["name"]]["domain"]][nodes[kdu["name"]]["cluster"]] = []
        result[nodes[kdu["name"]]["domain"]][nodes[kdu["name"]]["cluster"]].append(kdu)
    return result


def check_appi_instantiation(meao, appi: dict):
    """
    Wait for the MEC app instantiation to finish.
    """

    # Get the existing clusters and network services and init the status
    clusters = [(domain, cluster, instance) for domain, clusters in appi["instances"].items() for cluster, instance in clusters.items()]
    config_status = True
    operational_status = True
    
    while True:
        clusters_to_remove = []
        for index, cluster in enumerate(clusters):
            if cluster[0] != appi["domain"]:
                # Not implemented yet. It needs federation
                continue

            # Get the NS instance status
            ns_instance = meao.nbi_k8s_connector.callNBI(
                meao.nbi_k8s_connector.nbi_client.ns.get,
                name=cluster[2]["ns_id"]
            )

            # If the NS instance is not in init state, it already has a status so check if it is running or failed and update the kdus accordingly
            if ns_instance and (ns_instance['operational-status'] != "init" or ns_instance['config-status'] != "init"):
                clusters_to_remove.append(index)

                # Update if any config status or operational status failed
                if ns_instance['operational-status'] != "running":
                    operational_status = False
                if ns_instance['config-status'] != "configured":
                    config_status = False

                # Update each kdu running in the cluster status
                for kdu_name in cluster[2]["kdus"]:
                    appi["kdus"][kdu_name]["status"] = "running" if ns_instance["operational-status"] == "running" and ns_instance['config-status'] == "configured" else "failed"
        
        # Remove the clusters that are already deployed
        [clusters.pop(i) for i in clusters_to_remove]

        # If there are no more clusters to check, break the loop, else wait a bit and check again
        if len(clusters) <= 0: break
        time.sleep(1)
    
    # If no clusters are left update the appi status (operational and config) to running or failed, depending if a single kdu failed or if all are running
    DB._update(
        id=appi["_id"],
        collection="appis",
        data={
            "kdus": appi["kdus"],
            "operational-status": "running" if operational_status else "failed",
            "config-status": "configured" if config_status else "failed",
            "details": "Instantiation was successful" if operational_status and config_status else "Failed to deploy some artifacts",
        }
    )
    
