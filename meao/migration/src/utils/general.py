def updateDict(oldDict, updatedDict):
    """
    Simple function to ensures the old dictionary is updated without altering the existing contents unnecessarily.

    Also verifies if there is an update to the migration policy of any container

    Parameters
    ----------
    oldDict : dict
        dictionary to be updated
    values: dict
        dictionary with new content
    """
    
    keys_to_keep = set(oldDict.keys()).intersection(updatedDict.keys())
    keys_to_remove = set(oldDict.keys()) - keys_to_keep
    for key in keys_to_remove:
        oldDict.pop(key)

    for key in keys_to_keep:
        if (
            "migration_policy" in oldDict[key]
            and not oldDict[key]["migration_policy"]
            and updatedDict[key]["migration_policy"]
        ):
            oldDict[key]["migration_policy"] = updatedDict[key]["migration_policy"]
    
    keys_to_add = set(updatedDict.keys()) - set(oldDict.keys())
    for key in keys_to_add:
        oldDict[key] = updatedDict[key]

    return oldDict

def updateDict2(oldDict, updatedDict):
    for key, value in updatedDict.items():
        if isinstance(value, dict) and isinstance(oldDict.get(key), dict):
            updateDict(oldDict[key], value)
        else:
            oldDict[key] = value
    return oldDict

def bytes_to_mb(value):
    return value / 1_000_000

def ki_to_mb(ki):
    return (ki * 1024) / 1_000_000
