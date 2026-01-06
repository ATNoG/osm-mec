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
    keys_to_add = set(updatedDict.keys()) - set(oldDict.keys())
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
    
    for key in keys_to_add:
        oldDict[key] = updatedDict[key]

    return oldDict

def updateMetricsDict(oldDict, updatedDict):
    """
    Sync oldDict to have the same structure as updatedDict, preserving
    existing 'metrics' values when the corresponding metrics in updatedDict
    are empty, adding new keys with empty dicts, and removing disappeared keys.
    This function mutates oldDict and also returns it.
    """

    def sync_level(old_level, new_level):
        # Remove keys that disappeared
        for k in list(old_level.keys()):
            if k not in new_level:
                del old_level[k]

        # Add/update keys from new_level
        for k, new_val in new_level.items():
            # If value is not a dict, just copy (for static fields like 'domain', 'cluster', 'node', 'name')
            if not isinstance(new_val, dict):
                old_level[k] = new_val
                continue

            old_val = old_level.get(k)

            # If this is a metrics dict: preserve old if exists and new is empty
            if k == "metrics" and isinstance(new_val, dict):
                if isinstance(old_val, dict) and not new_val:
                    # keep old metrics as-is
                    continue
                # otherwise overwrite/initialize metrics to new_val
                old_level[k] = new_val.copy()
                continue

            # For nested dicts (pods, containers, app ids, etc.)
            if not isinstance(old_val, dict):
                old_val = {}
                old_level[k] = old_val

            sync_level(old_val, new_val)

    sync_level(oldDict, updatedDict)
    return oldDict

def bytes_to_mb(value):
    return value / 1_000_000

def ki_to_mb(ki):
    return (ki * 1024) / 1_000_000
