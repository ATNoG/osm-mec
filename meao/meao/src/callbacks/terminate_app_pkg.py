from src.utils.appd_validation import *
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.file_management import *
from src.utils.osm import get_osm_client


@handle_exceptions
def callback(message):
    appi_id = message.get("appi_id")
    wait = message.get("wait")

    if appi_id:
        get_osm_client().ns.delete(
            name=appi_id,
            wait=wait,
        )
        _id = DB._find("appis", filter={"appi_id": appi_id}).get("_id")
        DB._delete(_id, "appis")

        return {"msg_id": message["msg_id"], "status": 204}
