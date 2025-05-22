from src.utils.exceptions import handle_exceptions
from src.utils.general import updateDict

@handle_exceptions
def callback(meao, message):
    message.pop("msg_id", None)
    meao.node_specs = updateDict(meao.node_specs, message)
