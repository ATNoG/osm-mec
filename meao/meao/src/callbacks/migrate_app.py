import yaml
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.osm import get_osm_client
from src.utils.capture_io import CaptureIO
import time

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
    node_specs = meao.get_infrastructure_info()

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

    # Check if the kdu instance exists and where it is running
    kdu_instance = next(({"domain": _domain, "cluster": _cluster, "node": appis[appi_id]["instances"][_domain][_cluster]["kdus"][_kdu], "kdu": _kdu} for _domain in appis[appi_id]["instances"] for _cluster in appis[appi_id]["instances"][_domain] for _kdu in appis[appi_id]["instances"][_domain][_cluster]["kdus"] if _kdu == kdu_id), None)

    if not kdu_instance:
        return {"status": 404, "error": "KDU Instance {} not found".format(kdu_id)}
    
    # update the appi kdu instance status to migrating
    DB._update(appis[appi_id]["_id"], "appis", {'details': "Migrating", f"kdus.{kdu_id}.status": "migrating"})

    # Allocate the resources in the new node
    kdu_resources = {
        "allocated-cpu": appis[appi_id]["migration_policy"].get(kdu_id, {}).get("cpu-criteria", {}).get("allocated-cpu", 0),
        "allocated-mem": appis[appi_id]["migration_policy"].get(kdu_id, {}).get("mem-criteria", {}).get("allocated-mem", 0),
    }

    # Select a strategy to migrate the kdu instance
    if domain != meao.domain:
        return {"status": 400, "error": "Federation Needed. Not Implemented yet."}
    elif kdu_instance["cluster"] != cluster:
        DB._general_update_by("resources", {"cluster": cluster, "node": node}, {"$inc": kdu_resources})
        migrate_cluster(meao, mec_apps[appis[appi_id]["app_pkg_id"]], appis[appi_id], kdu_id, domain, cluster, node)
    elif kdu_instance["node"] != node:
        DB._general_update_by("resources", {"cluster": cluster, "node": node}, {"$inc": kdu_resources})
        migrate_node(meao, mec_apps[appis[appi_id]["app_pkg_id"]], appis[appi_id], kdu_id, domain, cluster, node)
    else:
        DB._update(appis[appi_id]["_id"], "appis", {'details': "Migration Completed", f"kdus.{kdu_id}.status": "running"})
        return {"status": 200, "message": "KDU {} is already running in the desired location.".format(kdu_id)}
    
    # Remove the resources from the old node if it was in the domain
    if kdu_instance["domain"] == meao.domain:
        DB._general_update_by("resources", {"cluster": kdu_instance["cluster"], "node": kdu_instance["node"]}, {"$inc": {k: -v for k, v in kdu_resources.items()}})

    DB._update(appis[appi_id]["_id"], "appis", {'details': "Migrated with success", f"kdus.{kdu_id}.status": "running"})
    return {"status": 200, "message": "KDU {} migrated to cluster {} at node {}.".format(kdu_id, cluster, node)}


def migrate_cluster(meao, mec_appd, appi, kdu_id, domain, cluster, node):
    # Check if the new cluster already has a running network service
    if appi.get("instances", {}).get(domain, {}).get(cluster, None): # There is already a Network service in the cluster, I need to enable the kdu there
        new_ns_id = appi["instances"][domain][cluster]["ns_id"]
        meao.nbi_k8s_connector.enable_kdu(mec_appd["appd_id"], new_ns_id, [kdu_id], node)

        # wait for the new kdu to be running
        meao.nbi_k8s_connector.wait_for_kdu_enable(new_ns_id, kdu_id)

    else: # There is no network service in the cluster, create a new one
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
        
        # Instantiate and wait for the new network service to be fully running
        with CaptureIO() as out:
            get_osm_client().ns.create(
                nsd_name=appi.get("ns_pkg_id"),
                nsr_name=appi.get("name"),
                account=meao.infrastructure_info[cluster]["vim-account"],
                description=appi.get("description"),
                config=dict_to_yaml_string(config),
                wait=True,
            )
        instance_id = out[0]
        vnf_id = get_osm_client().vnf.list(ns=instance_id)[0]["_id"]

        appi["instances"].setdefault(domain, {}).setdefault(cluster, {"ns_id": instance_id, "vnf_id": vnf_id, "kdus": {}})

    # Disable the old kdu
    old_instance = next(({"domain": _domain, "cluster": _cluster, "ns_id": appi["instances"][_domain][_cluster]["ns_id"]} for _domain in appi["instances"] for _cluster in appi["instances"][_domain] for _kdu in appi["instances"][_domain][_cluster]["kdus"] if _kdu == kdu_id), None)
    meao.nbi_k8s_connector.disable_kdu(mec_appd["appd_id"], old_instance["ns_id"], [kdu_id])
    
    # Change the appi instance to the new cluster and delete the old one if empty
    appi["instances"][domain][cluster]["kdus"][kdu_id] = node
    appi["instances"][old_instance["domain"]][old_instance["cluster"]]["kdus"].pop(kdu_id, None)

    # If there are no more kdu instances running in the old cluster, delete the network service and remove it from the appi
    if not appi["instances"][old_instance["domain"]][old_instance["cluster"]]["kdus"]:
        meao.nbi_k8s_connector.delete_network_service(old_instance["ns_id"])
        appi["instances"][old_instance["domain"]].pop(old_instance["cluster"], None)
    
    # If there are no more clusters in the old domain, remove the domain from the appi
    if not appi["instances"][old_instance["domain"]]:
        appi["instances"].pop(old_instance["domain"], None)
    
    # Update the appi in the database to reflect the changes
    DB._update(appi["_id"], "appis", {"instances": appi["instances"]})


def migrate_node(meao, mec_app, appi, kdu_id, domain, cluster, node):
    # Get the ns and vnf ids from the appi
    ns_id = appi["instances"][domain][cluster]["ns_id"]
    vnf_id = appi["instances"][domain][cluster]["vnf_id"]

    # Get the kdu instance of the kdu_id from the ns instance
    ns_instance = meao.nbi_k8s_connector.callNBI(meao.nbi_k8s_connector.nbi_client.ns.get, ns_id)
    kdu_instance_index, kdu_instance = next((index, kdu) for index, kdu in enumerate(ns_instance["_admin"]["deployed"]["K8s"]) if kdu["kdu-name"] == kdu_id and kdu["member-vnf-index"] == str(mec_app["appd_id"] + "-vnf"))

    if not kdu_instance:
        return {"status": 404, "error": "KDU Instance {} not found".format(kdu_id)}

    # Migrate the kdu instance to the new node
    meao.nbi_k8s_connector.migrate(ns_id, vnf_id, kdu_instance["kdu-instance"], kdu_instance_index, node)

    # Wait for the new kdu to be running
    wait_for_kdu_node(meao, ns_id, kdu_id, node)

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
    