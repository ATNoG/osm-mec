from src.utils.exceptions import handle_exceptions
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    handle_response:
        thread for collecting and processing responses from the MEAO
    """
    
    try:
        msg_id = message.pop("msg_id", None)

        if msg_id not in meao.waiting_responses:
            return
        
        meao.waiting_responses[msg_id] = message

    except RuntimeError as e:
        logging.info(f"Exception while processing kafka messages: {e}")
