from src.utils.exceptions import handle_exceptions
from src.utils.general import updateDict

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
        meao.appis = message

        # Get the containers information to be able to monitor them
        container_to_app, current_metrics = meao.nbi_k8s_connector.get_container_info(meao.appis)

        # Update the container to app mapping and the current metrics
        meao.container_to_app = updateDict(meao.container_to_app, container_to_app)
        meao.current_metrics = updateDict(meao.current_metrics, current_metrics)   #
        
    except RuntimeError as e:
        print("INFO: Exception while processing kafka messages: ", e)
    
