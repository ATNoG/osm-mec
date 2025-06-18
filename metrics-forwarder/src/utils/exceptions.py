
def handle_exceptions(f):
    def wrapper(*args, **kw):
        try:
            result = f(*args, **kw)
            if result is not None:
                result["msg_id"] = args[1].get("msg_id")

            return result
        except Exception as e:
            return {
                "msg_id": args[1].get("msg_id"),
                "status": 500,
                "error": "MEAO: " + str(e),
            }

    return wrapper
