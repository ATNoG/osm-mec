import yaml
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.osm import get_osm_client
from src.utils.capture_io import CaptureIO
from src.utils.kafka.kafka_utils import KafkaUtils
import time
import requests

@handle_exceptions
def callback(meao, message):
    # Get the data from the message
    appi_id = message.get("appi_id", None)
    kdu_id = message.get("kdu_id", None)
    domain = message.get("domain", None)
    cluster = message.get("cluster_id", None)
    node = message.get("node", None)
    
    # Check if there is any missing data
    if not appi_id or not kdu_id or not domain or not cluster or not node:
        return {"status": 400, "error": "Missing required parameters: appi_id, kdu_id, domain, cluster_id, node"}
    
    # Get the mec_apps, appis and node specs from the database
    mec_apps = meao.get_mec_apps()
    appis = meao.get_mec_apps_instances()
    node_specs = {**meao.get_infrastructure_info(), **meao.federation_infrastructure_info}

    # Check if the data is valid
    if appi_id not in appis:
        return {"status": 404, "error": "Appi ID {} not found".format(appi_id)}
    
    if appis[appi_id]["operational-status"] == "init" or appis[appi_id]["config-status"] == "init":
        return {"status": 400, "error": "Appi {} is not in a valid state to migrate".format(appi_id)}

    if appis[appi_id]["kdus"][kdu_id]["status"] != "running":
        return {"status": 400, "error": "KDU {} is not in running state".format(kdu_id)}
    
    if kdu_id not in appis[appi_id]["kdus"]:
        return {"status": 404, "error": "KDU ID {} not found".format(kdu_id)}

    if not appis[appi_id]["kdus"][kdu_id]["enable"]:
        return {"status": 400, "error": "KDU ID {} is not enabled".format(kdu_id)}
    
    if cluster not in node_specs or domain != node_specs[cluster]["domain"]:
        return {"status": 404, "error": "Cluster {} at Domain {} does not exist".format(cluster, domain)}

    if node not in node_specs[cluster].get("nodeSpecs", None):
        return {"status": 404, "error": "Node {} not found".format(node)}
    
    if domain != meao.domain and domain not in meao.federations_context_id:
        return {"status": 404, "error": "Domain {} not found in federations".format(domain)}

    # Check if the kdu instance exists and where it is running
    kdu_instance = next(({"domain": _domain, "cluster": _cluster, "node": appis[appi_id]["instances"][_domain][_cluster]["kdus"][_kdu], "kdu": _kdu} for _domain in appis[appi_id]["instances"] for _cluster in appis[appi_id]["instances"][_domain] for _kdu in appis[appi_id]["instances"][_domain][_cluster]["kdus"] if _kdu == kdu_id), None)

    if not kdu_instance:
        return {"status": 404, "error": "KDU Instance {} not found".format(kdu_id)}

    # TODO: This is for test purposes
    # ##################################################################################################
    try:
        request_body = {"name": "migration-init", "message": "MEAO Migration Init", "value": None}
        alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
        if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
    except Exception as e:
        print(f"Failed to send request: {e}")
    # ##################################################################################################
    
    # update the appi kdu instance status to migrating
    DB._update(appis[appi_id]["_id"], "appis", {'details': "Migrating", f"kdus.{kdu_id}.status": "migrating"})

    # Allocate the resources in the new node
    kdu_resources = {
        "allocated-cpu": appis[appi_id]["migration_policy"].get(kdu_id, {}).get("cpu-criteria", {}).get("allocated-cpu", 0),
        "allocated-mem": appis[appi_id]["migration_policy"].get(kdu_id, {}).get("mem-criteria", {}).get("allocated-mem", 0),
    }

    # Select a strategy to migrate the kdu instance
    if kdu_instance["domain"] != domain or kdu_instance["cluster"] != cluster:
        error = migrate_cluster(meao, mec_apps[appis[appi_id]["app_pkg_id"]], appis[appi_id], kdu_id, domain, cluster, node)
    elif kdu_instance["node"] != node:
        error = migrate_node(meao, mec_apps[appis[appi_id]["app_pkg_id"]], appis[appi_id], kdu_id, domain, cluster, node)
    else:
        DB._update(appis[appi_id]["_id"], "appis", {'details': "Migration Completed", f"kdus.{kdu_id}.status": "running"})
        return {"status": 200, "message": "KDU {} is already running in the desired location.".format(kdu_id)}
    
    # If the migration was not successful, return
    if error: return error
    
    # Update the resources in the database for the new node
    if domain == meao.domain:
        DB._general_update_by("resources", {"cluster": cluster, "node": node}, {"$inc": kdu_resources})
    
    # Remove the resources from the old node if it was in the domain
    if kdu_instance["domain"] == meao.domain:
        DB._general_update_by("resources", {"cluster": kdu_instance["cluster"], "node": kdu_instance["node"]}, {"$inc": {k: -v for k, v in kdu_resources.items()}})

    # TODO: This is for test purposes
    # ##################################################################################################
    try:
        request_body = {"name": "migration-done", "message": "MEAO Migration Done", "value": None}
        alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
        if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
    except Exception as e:
        print(f"Failed to send request: {e}")
    # ##################################################################################################

    DB._update(appis[appi_id]["_id"], "appis", {'details': "Migrated with success", f"kdus.{kdu_id}.status": "running"})
    return {"status": 200, "message": "KDU {} migrated to cluster {} at node {}.".format(kdu_id, cluster, node)}


def migrate_cluster(meao, mec_appd, appi, kdu_id, domain, cluster, node):
    # Check if the new cluster already has a running network service
    if appi.get("instances", {}).get(domain, {}).get(cluster, None): # There is already a Network service in the cluster, I need to enable the kdu there
        error = enable_new_kdu(meao, domain, cluster, node, mec_appd, appi, kdu_id)
        if error: return error
    else: # There is no network service in the cluster, create a new one
        error = new_network_service(meao, domain, cluster, node, appi, kdu_id)
        if error: return error

    # TODO: This is for test purposes
    # ##################################################################################################
    try:
        request_body = {"name": "migration-ready", "message": "MEAO Migration Ready", "value": None}
        alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
        if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
    except Exception as e:
        print(f"Failed to send request: {e}")
    # ##################################################################################################
    
    # TODO: This is for test purposes
    # ##################################################################################################
    old_instance = next(({"domain": _domain, "cluster": _cluster, "ns_id": appi["instances"][_domain][_cluster]["ns_id"]} for _domain in appi["instances"] for _cluster in appi["instances"][_domain] for _kdu in appi["instances"][_domain][_cluster]["kdus"] if _kdu == kdu_id), None)
    if old_instance["domain"] != domain:    # If there is a domain change, warn the user equipment (UE) about the change
        if kdu_id == "mec-test-server" and old_instance.get("cluster") != cluster:
            # Warn the application that the domain has changed so it needs to update the network interface
            print("Warning the UE about the cluster change, so it can update the network interface...")
            try:
                new_mec = "mec1" if cluster == "3c3c08f5-14b4-432c-b691-12531f3487b5" else "mec2"
                requests.post(f"http://10.255.41.239:8000/switchMEC/{new_mec}", timeout=5)
            except requests.RequestException as e:
                print(f"Failed to notify application about interface switch: {e}")
    # ##################################################################################################
    
    # Disable the old kdu
    disable_old_kdu(meao, domain, cluster, node, mec_appd, appi, kdu_id)
    
    # Update the appi in the database to reflect the changes
    DB._update(appi["_id"], "appis", {"instances": appi["instances"]})


def migrate_node(meao, mec_app, appi, kdu_id, domain, cluster, node):
    # Get the ns and vnf ids from the appi
    ns_id = appi["instances"][domain][cluster]["ns_id"]
    vnf_id = appi["instances"][domain][cluster]["vnf_id"]

    if domain == meao.domain:
        # Get the kdu instance of the kdu_id from the ns instance
        ns_instance = meao.nbi_k8s_connector.callNBI(meao.nbi_k8s_connector.nbi_client.ns.get, ns_id)
        kdu_instance_index, kdu_instance = next((index, kdu) for index, kdu in enumerate(ns_instance["_admin"]["deployed"]["K8s"]) if kdu["kdu-name"] == kdu_id and kdu["member-vnf-index"] == str(mec_app["appd_id"] + "-vnf"))

        if not kdu_instance:
            return {"status": 404, "error": "KDU Instance {} not found".format(kdu_id)}

        # Migrate the kdu instance to the new node
        # TODO: This is for test purposes
        # ##################################################################################################
        try:
            request_body = {"name": f"node-inst-init", "message": "MEAO instance Creation Init"}
            alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
            if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
        except Exception as e:
            print(f"Failed to send request: {e}")
        # ##################################################################################################
        meao.nbi_k8s_connector.migrate(ns_id, vnf_id, kdu_instance["kdu-instance"], kdu_instance_index, node)

        # Wait for the new kdu to be running
        wait_for_kdu_node(meao, ns_id, kdu_id, node)
        # TODO: This is for test purposes
        # ##################################################################################################
        try:
            request_body = {"name": f"node-inst-done", "message": "MEAO instance Creation done"}
            alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
            if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
        except Exception as e:
            print(f"Failed to send request: {e}")
        # ##################################################################################################
    else:
        msg_id = KafkaUtils.send_message(
            meao.producer,
            "federation_migrate_node",
            {
                "federation_context_id": meao.federations_context_id.get(domain),
                "mec_appd_id": mec_app["appd_id"],
                "ns_id": ns_id,
                "vnf_id": vnf_id,
                "kdu_id": kdu_id,
                "node": node,
            }
        )

        # wait for the new network service to be fully running
        response = meao.wait_for_response(msg_id)
        if int(response["status"]) != 200:
            return {"status": int(response["status"]), "error": response["message"]}
    
    # TODO: This is for test purposes
    # ##################################################################################################
    try:
        request_body = {"name": "migration-ready", "message": "MEAO Migration Ready", "value": None}
        alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
        if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
    except Exception as e:
        print(f"Failed to send request: {e}")
    # #################################################################################################

    # Change the appi instance to the new node and update the database
    appi["instances"][domain][cluster]["kdus"][kdu_id] = node
    DB._update(appi["_id"], "appis", {"instances": appi["instances"]})

def wait_for_kdu_node(meao, ns_id: str, kdu_id: str, node: str):
    # Here OSM is updating the database after the updated helm chart is fully running (even though the old one might still not have been fully deleted). The problem here is when to inform the new node to the client?
    while True:
        ns_instance = meao.nbi_k8s_connector.callNBI(meao.nbi_k8s_connector.nbi_client.ns.get, ns_id)
        kdu_instance = next(kdu for kdu in ns_instance["_admin"]["deployed"]["K8s"] if kdu["kdu-name"] == kdu_id)
        if kdu_instance["enable"] and kdu_instance["operation"] == "upgrade" and kdu_instance["status"] == "Upgrade complete" and kdu_instance["node-selector"]["kubernetes.io/hostname"] == node:
            break
        time.sleep(0.01)  # Sleep for 0.01 seconds to avoid busy waiting

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


def new_network_service(meao, domain, cluster, node, appi, kdu_id):
    config = appi.get("config", {})

    # Create a custom config for the new cluster with only the kdu to be migrated
    for vnf in config.get("additionalParamsForVnf", []):
        for kdu in vnf.get("additionalParamsForKdu", []):
            kdu_name = kdu.get("kdu_name")
            if kdu_name == kdu_id:
                kdu["enable"] = True
                kdu["node-selector"] = {"kubernetes.io/hostname": node}
            else:
                kdu["enable"] = False
                kdu.pop("node-selector", None)

    if domain == meao.domain:
        # Instantiate and wait for the new network service to be fully running
        with CaptureIO() as out:
            get_osm_client().ns.create(
                nsd_name=appi.get("ns_pkg_id"),
                nsr_name=appi.get("name"),
                account=meao.infrastructure_info[cluster]["vim-account"],
                description=appi.get("description"),
                config=dict_to_yaml_string(config),
                wait=True,  # Wait for the NS to be fully running
            )
        ns_id = out[0]
        vnf_id = get_osm_client().vnf.list(ns=ns_id)[0]["_id"]
    else:
        # TODO: This is for test purposes
        # ##################################################################################################
        try:
            request_body = {"name": "artefact-onboard-init", "message": "MEAO Artefact Onboard Init", "value": None}
            alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
            if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
        except Exception as e:
            print(f"Failed to send request: {e}")
        # ##################################################################################################

        message = {
            "federation_context_id": meao.federations_context_id.get(domain),
            "app_pkg_id": appi.get("app_pkg_id"),
            "vim_id": meao.federation_infrastructure_info[cluster]["vim-account"],
            "config": dict_to_yaml_string(config),
        }

        # Upload the needed artefact to the partner domain
        msg_id = KafkaUtils.send_message(
            meao.producer,
            "federation_new_artefact",
            message
        )

        # wait for the artifact to be uploaded to the partner domain
        response = meao.wait_for_response(msg_id)
        if int(response["status"]) != 200:
            return {"status": int(response["status"]), "error": response["message"]}
        
        # TODO: This is for test purposes
        # ##################################################################################################
        try:
            request_body = {"name": "artefact-onboard-done", "message": "MEAO Artefact Onboard Done", "value": None}
            alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
            if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
        except Exception as e:
            print(f"Failed to send request: {e}")
        # ##################################################################################################

        # TODO: This is for test purposes
        # ##################################################################################################
        try:
            request_body = {"name": "appi-inst-init", "message": "MEAO Appi Creation Init", "value": None}
            alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
            if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
        except Exception as e:
            print(f"Failed to send request: {e}")
        # ##################################################################################################
        
        # Instantiate the new network service
        msg_id = KafkaUtils.send_message(
            meao.producer,
            "federation_new_appi",
            message
        )

        # wait for the new network service to be fully running
        response = meao.wait_for_response(msg_id)
        if int(response["status"]) != 201:
            return {"status": int(response["status"]), "error": response["message"]}
        
        # TODO: This is for test purposes
        # ##################################################################################################
        try:
            request_body = {"name": "appi-inst-done", "message": "MEAO Appi Creation Done", "value": None}
            alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
            if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
        except Exception as e:
            print(f"Failed to send request: {e}")
        # ##################################################################################################

        federated_appi_id = response.get("app_instance_id")
        ns_id = response["ns_id"]
        vnf_id = response["vnf_id"]


    appi["instances"].setdefault(domain, {}).setdefault(cluster, {"appi_id": federated_appi_id, "ns_id": ns_id, "vnf_id": vnf_id, "kdus": {}})

def enable_new_kdu(meao, domain, cluster, node, mec_appd, appi, kdu_id):
    new_ns_id = appi["instances"][domain][cluster]["ns_id"]

    # Enable the KDU in the new domain and cluster and wait for it to be running
    if domain == meao.domain:
        meao.nbi_k8s_connector.enable_kdu(mec_appd["appd_id"], new_ns_id, [kdu_id], node)
        meao.nbi_k8s_connector.wait_for_kdu_enable(new_ns_id, kdu_id)
    else:
        msg_id = KafkaUtils.send_message(
            meao.producer,
            "federation_enable_kdu",
            {
                "federation_context_id": meao.federations_context_id.get(domain),
                "mec_appd_id": mec_appd["appd_id"],
                "ns_id": new_ns_id,
                "kdu_id": kdu_id,
                "node": node,
            }
        )

        # wait for the new kdu to be running
        response = meao.wait_for_response(msg_id)
        if int(response["status"]) != 200:
            return {"status": int(response["status"]), "error": response["message"]}

def disable_old_kdu(meao, domain, cluster, node, mec_appd, appi, kdu_id):
    old_instance = next(({"domain": _domain, "cluster": _cluster, "appi_id": appi["instances"][_domain][_cluster].get("appi_id", None), "ns_id": appi["instances"][_domain][_cluster]["ns_id"]} for _domain in appi["instances"] for _cluster in appi["instances"][_domain] for _kdu in appi["instances"][_domain][_cluster]["kdus"] if _kdu == kdu_id), None)

    if old_instance is None:
        return {"status": 404, "error": "Old instance not found for KDU {}".format(kdu_id)}

    # Change the appi instance to the new cluster and delete the old one if empty
    appi["instances"][domain][cluster]["kdus"][kdu_id] = node
    appi["instances"][old_instance["domain"]][old_instance["cluster"]]["kdus"].pop(kdu_id, None)

    if old_instance["domain"] == meao.domain:
        if not appi["instances"][old_instance["domain"]][old_instance["cluster"]]["kdus"]:
            # If there are no more kdu instances running in the old cluster, delete the network service and remove it from the appi
            appi["instances"][old_instance["domain"]].pop(old_instance["cluster"], None)
            # TODO: This is for test purposes
            # ##################################################################################################
            try:
                request_body = {"name": "old-appi-remove-init", "message": "MEAO Removing old appi Init", "value": None}
                alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
                if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
            except Exception as e:
                print(f"Failed to send request: {e}")
            # ##################################################################################################
            meao.nbi_k8s_connector.delete_network_service(old_instance["ns_id"], wait=True)
            # TODO: This is for test purposes
            # ##################################################################################################
            try:
                request_body = {"name": "old-appi-remove-done", "message": "MEAO Removing old done", "value": None}
                alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
                if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
            except Exception as e:
                print(f"Failed to send request: {e}")
            # ##################################################################################################
        else:
            # Disable the old kdu in the current domain if there are more kdu instances running in the old cluster
            meao.nbi_k8s_connector.disable_kdu(mec_appd["appd_id"], old_instance["ns_id"], [kdu_id])
    else:
        if not appi["instances"][old_instance["domain"]][old_instance["cluster"]]["kdus"]:
            # If there are no more kdu instances running in the old cluster, delete the network service and remove it from the appi
            appi["instances"][old_instance["domain"]].pop(old_instance["cluster"], None)

            # TODO: This is for test purposes
            # ##################################################################################################
            try:
                request_body = {"name": "old-appi-remove-init", "message": "MEAO Removing old appi Init", "value": None}
                alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
                if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
            except Exception as e:
                print(f"Failed to send request: {e}")
            # ##################################################################################################
            msg_id = KafkaUtils.send_message(
                meao.producer,
                "federation_remove_appi",
                {
                    "federation_context_id": meao.federations_context_id.get(old_instance["domain"]),
                    "app_instance_id": old_instance["appi_id"],
                }
            )
            # TODO: This is for test purposes
            # ##################################################################################################
            try:
                request_body = {"name": "old-appi-remove-done", "message": "MEAO Removing old done", "value": None}
                alert_response = requests.post(f"http://10.255.41.239:8000/alert", json=request_body, timeout=5)
                if alert_response.status_code != 200: print(f"Failed to notify application: {alert_response.status_code} - {alert_response.text}")
            except Exception as e:
                print(f"Failed to send request: {e}")
            # ##################################################################################################
        else:
            msg_id = KafkaUtils.send_message(
                meao.producer,
                "federation_disable_kdu",
                {
                    "federation_context_id": meao.federations_context_id.get(old_instance["domain"]),
                    "mec_appd_id": mec_appd["appd_id"],
                    "ns_id": old_instance["ns_id"],
                    "kdu_id": kdu_id,
                }
            )
    
    # If there are no more clusters in the old domain, remove the domain from the appi
    if not appi["instances"][old_instance["domain"]]:
        appi["instances"].pop(old_instance["domain"], None)
