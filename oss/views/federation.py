from datetime import datetime

def date_to_str(value):
    return value.isoformat() if isinstance(value, datetime) else value

class FederationView:

    
    @staticmethod
    def _list(data):
        return {
            "id": str(data["_id"]),
            "origin": data.get("originOP").get("origOPFederationId"),
            "partner": data.get("partnerOP").get("partnerOPFederationId"),
            "number_applications": data.get("federationHealthInfo").get("numOfApplications"),
            "initial_date": date_to_str(data.get("originOP").get("initialDate")),
            "expiry_date": date_to_str(data.get("partnerOP").get("federationExpiryDate")),
            "renewal_date": date_to_str(data.get("partnerOP").get("federationRenewalDate")),
            "status": data.get("status"),
        }

    @staticmethod
    def _get(data):
        return data
    