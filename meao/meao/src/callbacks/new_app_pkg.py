from osmclient.common.exceptions import ClientException
from src.utils.appd_parser import AppdParser
from src.utils.appd_validation import *
from src.utils.capture_io import CaptureIO
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.file_management import *
from src.utils.osm import get_osm_client
from decimal import Decimal, ROUND_HALF_UP


@handle_exceptions
def callback(message):
    app_pkg_id = message.get("app_pkg_id")

    if app_pkg_id:
        app_pkg = DB._get(id=app_pkg_id, collection="app_pkgs")

        appd_binary = app_pkg.get("appd")
        appd_data = get_descriptor_data(appd_binary)
        appd = validate_descriptor(appd_data)

        appd_parser = AppdParser(appd)

        artifacts = appd_parser.get_artifacts()
        artifacts_data = get_artifacts_data(appd_binary, artifacts)
        migration_policy = appd_parser.get_migration_policy()

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

            if (
                migration_policy
                and "mobility-criteria" in migration_policy
                and "mobility-migration-factor" in migration_policy["mobility-criteria"]
            ):
                migration_policy["mobility-criteria"]["mobility-migration-factor"] = float(Decimal(migration_policy["mobility-criteria"]["mobility-migration-factor"]).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
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

        return {"msg_id": message["msg_id"], "status": 201}
