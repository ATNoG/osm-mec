from src.utils.exceptions import handle_exceptions
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    update_appis:
        thread for collecting and updating MEC Application Instances information received from the MEAO
    """

    message.pop("msg_id", None)
    try:
        meao.appis = message
    except RuntimeError as e:
        logging.info(f"Exception while processing kafka messages: {e}")
