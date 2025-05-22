import json
from osmclient.common.exceptions import ClientException
from src.utils.appd_parser import AppdParser
from src.utils.appd_validation import *
from src.utils.capture_io import CaptureIO
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.file_management import *
from src.utils.osm import get_osm_client
from decimal import Decimal, ROUND_HALF_UP
import logging


@handle_exceptions
def callback(meao, message):
    app_pkg_id = message.get("app_pkg_id")

    if app_pkg_id:
        app_pkg = DB._get(id=app_pkg_id, collection="app_pkgs")

        appd_binary = app_pkg.get("appd")
        appd_data = get_descriptor_data(appd_binary)
        appd = validate_descriptor(appd_data)

        appd_parser = AppdParser(appd)

        artifacts = appd_parser.get_artifacts()
        artifacts_names = appd_parser.get_artifacts_names()
        artifacts_data = get_artifacts_data(appd_binary, artifacts)

        unprocessed_migration_policy = appd_parser.get_migration_policy()

        migration_policy = {}
        for policy in unprocessed_migration_policy.values():
            if policy.get("enabled", None) and policy.get("artifact", None) in artifacts_names:
                if (policy and "mobility-criteria" in policy and "mobility-migration-factor" in policy["mobility-criteria"]):
                    policy["mobility-criteria"]["mobility-migration-factor"] = float(Decimal(policy["mobility-criteria"]["mobility-migration-factor"]).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                migration_policy[policy["artifact"]] = policy

        vnfd_file = appd_parser.export_vnfd(get_dir("vnfd"), app_pkg_id, artifacts_data)
        nsd_file = appd_parser.export_nsd(get_dir("nsd"), app_pkg_id)

        try:
            with CaptureIO() as out:
                get_osm_client().vnfd.create(vnfd_file)
            vnf_pkg_id = out[0]

            try:
                with CaptureIO() as out:
                    get_osm_client().nsd.create(nsd_file)
                ns_pkg_id = out[0]
            except ClientException as e:
                get_osm_client().vnfd.delete(vnf_pkg_id)
                raise e

            DB._update(
                id=app_pkg_id,
                collection="app_pkgs",
                data={
                    "vnf_pkg_id": vnf_pkg_id,
                    "ns_pkg_id": ns_pkg_id,
                    "migration_policy": migration_policy
                },
            )
        except Exception as e:
            print("Exception occurred:", e)
        finally:
            delete_file(vnfd_file)
            delete_file(nsd_file)

        return {"status": 201}
    
    return {"status": 400}
