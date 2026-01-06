from src.utils.exceptions import handle_exceptions
from src.utils.general import updateDict
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    update_appis:
        thread for collecting and processing MEC Application information received from the OSS
        updates the nodeSpecs and containerInfo
    """

    try:
        # Update the MEC Apps Instances
        message.pop("msg_id", None)
        meao.federation_appis.update(message.get("appis", {}))

        # Get the containers information to be able to monitor them
        container_to_app = meao.nbi_k8s_connector.get_federation_container_info(meao.federation_appis)

        # Update the container to app mapping and the current metrics
        meao.federation_container_to_app = updateDict(meao.federation_container_to_app, container_to_app)
        
    except RuntimeError as e:
        logging.error(f"Exception while processing kafka messages: {e}")