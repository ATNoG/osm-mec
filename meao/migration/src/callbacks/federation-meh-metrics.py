from src.utils.exceptions import handle_exceptions
from src.utils.general import updateDict

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    update_federation_meh_metrics:
        thread for collecting and processing MEC Host metrics
    """

    try:
        # Update the federated MEC Hosts information
        message.pop("msg_id", None)
        meao.federation_meh_metrics.update(message.get("nodeSpecs", {}))
        
    except RuntimeError as e:
        print("INFO: Exception while processing kafka messages: ", e)
