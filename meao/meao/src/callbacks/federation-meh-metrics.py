from src.utils.exceptions import handle_exceptions
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    update_federation_infrastructure_info:
        thread for collecting and processing MEC Host metrics
    """

    try:
        # Update the federated MEC Hosts information
        message.pop("msg_id", None)
        meao.federation_infrastructure_info.update(message.get("nodeSpecs", {}))
        
    except RuntimeError as e:
        logging.info(f"INFO: Exception while processing kafka messages: {e}")
