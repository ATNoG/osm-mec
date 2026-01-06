class AppiView:
    @staticmethod
    def _list(data):
        return {
            "id": str(data["_id"]),
            "appi_id": data.get("appi_id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "operational-status": data.get("operational-status"),
            "config-status": data.get("config-status"),
            "details": data.get("detailed-status"),
            "created-at": data.get("create-time"),
        }

    @staticmethod
    def _get(data):
        return AppiView._list(data)
    
    @staticmethod
    def _get_detailed(data):
        return {
            "id": str(data["_id"]),
            "appi_id": data.get("appi_id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "domain": data.get("domain", {}),
            "operational-status": data.get("operational-status"),
            "config-status": data.get("config-status"),
            "details": data.get("detailed-status"),
            "created-at": data.get("create-time"),

            "kdus": data.get("kdus", {}),
            "instances": data.get("instances", {}),
        }
