from src.utils.exceptions import handle_exceptions
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    update_mec_apps:
        thread for collecting and processing MEC Applications information received from the MEAO
    """

    message.pop("msg_id", None)
    try:
        meao.mec_apps = message
    except RuntimeError as e:
        logging.info(f"Exception while processing kafka messages: {e}")
