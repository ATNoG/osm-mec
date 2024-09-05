from utils.appd_validation import *
from utils.capture_io import CaptureIO
from utils.db import DB
from utils.exceptions import handle_exceptions
from utils.file_management import *
from utils.osm import get_osm_client


@handle_exceptions
def callback(message):
    app_pkg_id = message.get("app_pkg_id")
    vim_id = message.get("vim_id")
    name = message.get("name")
    description = message.get("description")
    wait = message.get("wait")

    if app_pkg_id and vim_id and name and description:
        app_pkg = DB._get(id=app_pkg_id, collection="app_pkgs")
        ns_pkg_id = app_pkg.get("ns_pkg_id")
        vnf_pkg_id = app_pkg.get("vnf_pkg_id")
        migration_policy = app_pkg.get("migration_policy")

        with CaptureIO() as out:
            get_osm_client().ns.create(
                nsd_name=ns_pkg_id,
                nsr_name=name,
                account=vim_id,
                description=description,
                wait=wait,
            )
        instance_id = out[0]
        vnf_id = get_osm_client().vnf.list(ns=instance_id)[0]["_id"]
        while True:
            ns_instance = get_osm_client().ns.get(name=instance_id)
            if ("deployed" in ns_instance["_admin"]
                and "K8s" in ns_instance["_admin"]["deployed"]
                and ns_instance["_admin"]["deployed"]["K8s"]
                and len(ns_instance["_admin"]["deployed"]["K8s"]) > 0
            ):
                break
        kdu_instance = ns_instance["_admin"]["deployed"]["K8s"][0]["kdu-instance"]
        DB._add(
            collection="appis",
            data={
                "appi_id": instance_id,
                "vnf_id": vnf_id,
                "kdu_id": kdu_instance,
                "name": name,
                "description": description,
                "vim_id": vim_id,
                "vnf_pkg_id": vnf_pkg_id,
                "ns_pkg_id": ns_pkg_id,
                "migration_policy": migration_policy
            }
        )

        return {"msg_id": message["msg_id"], "status": 201, "instance_id": instance_id}
