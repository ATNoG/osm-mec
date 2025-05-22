import threading
import time
import random
random.seed(42)

from src.utils.kafka.kafka_utils import KafkaUtils

# only for type hints to avoid circular imports
TYPE_CHECKING = False
if TYPE_CHECKING:
    from src.meao import MEAO

class MigrationDecisionThread:
    """Background thread that sends MEC Apps information"""

    def __init__(self, meao):
        self.meao: MEAO = meao
        self.t = None

    def start(self):
        """Plugin entrypoint"""
        self.t = threading.Thread(target=self.migration_decision, args=())
        self.t.daemon = True
        self.t.start()

    def migration_decision(self):
        while True:
            try:
                for appi_id in list(self.meao.appis):
                    for kdu_id, migration_policy in self.meao.appis[appi_id]["migration_policy"].items():
                        print("===========================")
                        print("Checking appi", appi_id, "kdu", kdu_id, "migration policy: ", migration_policy)

                        print("Migrating Apps:", self.meao.migrating_apps)
                        print("Expected Resource Gains:", self.meao.expected_resource_gains)
                        print("Possible Migrations: ", self.meao.possible_migrations)

                        # Check if the appi is already migrating
                        if (appi_id, kdu_id) in self.meao.migrating_apps:
                            print("Appi already migrating")
                            continue

                        print("Checking the need for migration")
                        
                        kdu_current_node = next({"domain": domain, "cluster": cluster, "node": node} for domain in self.meao.appis[appi_id]["instances"] for cluster in self.meao.appis[appi_id]["instances"][domain] for kdu, node in self.meao.appis[appi_id]["instances"][domain][cluster]["kdus"].items() if kdu == kdu_id)
                        kdu_current_metrics = self.meao.current_metrics.get(appi_id, {}).get(kdu_id, {}).get("metrics", None)
                        print("KDU current Metrics: ", kdu_current_metrics)

                        # Check the need for migration based on the resources migration policy
                        resource_migration_need = False
                        if (
                            ("enabled" in migration_policy and migration_policy["enabled"]) and
                            ("cpu-criteria" in migration_policy or "mem-criteria" in migration_policy)
                        ):
                            resource_migration_need = self.check_resource_migration_need(kdu_id, migration_policy, kdu_current_node)

                        # Check the need for migration based on the latency migration policy
                        latency_migration_need = False
                        if (
                            ("enabled" in migration_policy and migration_policy["enabled"]) and
                            ("mobility-criteria" in migration_policy)
                        ):
                            latency_migration_need = self.check_latency_migration_need(kdu_id, migration_policy, kdu_current_node)

                        print("Do I need to migrate due to the resources? ", resource_migration_need)
                        print("Do I need to migrate due to the latency? ", latency_migration_need)

                        # If all of the migration policies are satisfied, then I do not need to migrate
                        if not resource_migration_need and not latency_migration_need:
                            continue

                        # Find a node that can fulfill all migration policy
                        min_resource_nodes = self.min_resource_nodes(migration_policy)
                        min_latency_nodes = self.min_latency_nodes(migration_policy)

                        # Intersect the nodes for each metrics to find the nodes that can fulfill all migration policy
                        possible_nodes = {node: {"resources": min_resource_nodes[node], "latency": min_latency_nodes[node]} for node in min_resource_nodes if node in min_latency_nodes}
                        print("Possible nodes: ", possible_nodes)
                        sorted_nodes = sorted(possible_nodes, key=lambda node: self.random_score_nodes(possible_nodes[node]))

                        # Select the best node if there are any
                        selected_node = sorted_nodes[0] if len(sorted_nodes) > 0 else None

                        if not selected_node:
                            print("There are no nodes that can fulfill the migration policy, I will not migrate")
                            continue
                        
                        # Execute the migration
                        print("I will migrate the appi {} kdu {} to node {} at cluster {} and domain {}".format(appi_id, kdu_id, selected_node[2], selected_node[1], selected_node[0]))
                        self.meao.possible_migrations.pop(kdu_id, None) # It is no longer a possible migration but an actual one
                        self.meao.migrate(appi_id, kdu_id, selected_node[0], selected_node[1], selected_node[2])

                time.sleep(5)
            except Exception as e:
                raise e
    
    def random_score_nodes(self, node_data):
        # Score the node
        return random.random()

    def min_resource_nodes(self, migration_policy):
        """
        Returns the nodes with the least resource usage that can fulfill a migration policy
        """
        min_resource_nodes = {}

        for cluster in self.meao.nodeSpecs:
            for node, node_specs in self.meao.nodeSpecs[cluster]["nodeSpecs"].items():
                if "available-cpu" in node_specs and "available-mem" in node_specs and node_specs["available-cpu"] > (migration_policy["cpu-criteria"]["allocated-cpu"] + migration_policy["cpu-criteria"].get("cpu-surge-capacity", 0)) and node_specs["available-mem"] > (migration_policy["mem-criteria"]["allocated-mem"] + migration_policy["mem-criteria"].get("mem-surge-capacity", 0)):
                    min_resource_nodes[(self.meao.nodeSpecs[cluster]["domain"], cluster, node)] = {
                        "available-cpu": node_specs["available-cpu"],
                        "available-mem": node_specs["available-mem"],
                        "available-cpu-load": round((node_specs["available-cpu"] / node_specs["num_cpu_cores"]) * 100, 2),
                        "available-mem-load": round((node_specs["available-mem"] / node_specs["memory_size"]) * 100, 2),
                        "expected-available-cpu": node_specs["available-cpu"] - (migration_policy["cpu-criteria"]["allocated-cpu"] + migration_policy["cpu-criteria"].get("cpu-surge-capacity", 0)),
                        "expected-available-mem": node_specs["available-mem"] - (migration_policy["mem-criteria"]["allocated-mem"] + migration_policy["mem-criteria"].get("mem-surge-capacity", 0)),
                        "expected-available-cpu-load": round(((node_specs["available-cpu"] - (migration_policy["cpu-criteria"]["allocated-cpu"] + migration_policy["cpu-criteria"].get("cpu-surge-capacity", 0))) / node_specs["num_cpu_cores"]) * 100, 2),
                        "expected-available-mem-load": round(((node_specs["available-mem"] - (migration_policy["mem-criteria"]["allocated-mem"] + migration_policy["mem-criteria"].get("mem-surge-capacity", 0))) / node_specs["memory_size"]) * 100, 2),
                    }
        
        return min_resource_nodes
    

    def min_latency_nodes(self, migration_policy):
        """
        Returns the name and latency of the node with the least latency

        Parameters
        ----------
        ue_lats : dict
            latency information
        exclude_nodes: list
            list containing the hostnames of nodes to not include in the search
        """
        min_latency_nodes = {}
        min_latency_nodes = self.min_resource_nodes(migration_policy)   # Copy the resource nodes since there is no way to know the latency yet, but this way I can keep with the code as if there was multiple metrics working

        return min_latency_nodes
    
    def check_resource_migration_need(self, kdu_id, migration_policy, kdu_current_node):
        """
        Processes the CPU and memory load of the container on the node and determines whether a migration operation must be scheduled

        The migration logic can be resumed in the following manner:

            If the current node cpu/memLoad + the container's cpu/mem_surge_capacity is larger than 100:
                - the container must be migrated since the node does not have the conditions for it
            If the current container cpu/memLoad on the node is larger than cpu/mem_load_thresh + cpu/mem_surge_capacity:
                - the container must be migrated since the Service-Level Agreement has been violated

        If none of these conditions are verified, the function returns None

        If the conditions for migration ARE verified, the function will then evaluate if the target node can support running the container,
        according to the application's Service-Level Agreement. If the target node can support running the container, 
        the function returns the name of the node with the least resource usage. 
        If not, it sends a Kafka message to notify the OSS of this occurrence and returns None

        Parameters
        ----------
        container : dict
            information relating to the container whose metrics are being processed, obtained from the containerInfo dictionary
        cName : str
            the container's ID
        """
        # Get kdu migration policy
        kdu_cpu_migration_policy = migration_policy["cpu-criteria"]
        kdu_mem_migration_policy = migration_policy["mem-criteria"]

        # Get node available resources
        if not self.meao.nodeSpecs.get(kdu_current_node["cluster"], {"nodeSpecs": {}})["nodeSpecs"].get(kdu_current_node["node"], {}).get("available-cpu", None):
            print("Available cpu not found for node: ", kdu_current_node["node"])
            return False
        available_node_cpu = self.meao.nodeSpecs[kdu_current_node["cluster"]]["nodeSpecs"][kdu_current_node["node"]]["available-cpu"] + self.meao.expected_resource_gains.get((kdu_current_node["domain"], kdu_current_node["cluster"], kdu_current_node["node"]), {}).get("cpu", 0)
        available_node_mem = self.meao.nodeSpecs[kdu_current_node["cluster"]]["nodeSpecs"][kdu_current_node["node"]]["available-mem"] + self.meao.expected_resource_gains.get((kdu_current_node["domain"], kdu_current_node["cluster"], kdu_current_node["node"]), {}).get("mem", 0)
        
        print("Available Node CPU: ", available_node_cpu)
        print("Available Node MEM: ", available_node_mem)

        # Check if the node enough resources to fulfill the allocated resources
        if available_node_cpu < 0 or available_node_mem < 0:
            return True

        # Check if the node has enough resources to fulfill the cpu_surge_capacity
        if kdu_cpu_migration_policy.get("cpu-surge-capacity", 0) > available_node_cpu:
            if kdu_id in self.meao.possible_migrations and "cpu" in self.meao.possible_migrations[kdu_id]:
                if time.time() - self.meao.possible_migrations[kdu_id]["cpu"] > kdu_cpu_migration_policy.get("cpu-threshold-time", 0):
                    return True
            else:
                self.meao.possible_migrations.setdefault(kdu_id, {})["cpu"] = time.time()
        elif kdu_id in self.meao.possible_migrations and "cpu" in self.meao.possible_migrations[kdu_id]:
            self.meao.possible_migrations[kdu_id].pop("cpu", None)
        
        # Check if the node has enough resources to fulfill the mem_surge_capacity
        if kdu_mem_migration_policy.get("mem-surge-capacity", 0) > available_node_mem:
            if kdu_id in self.meao.possible_migrations and "mem" in self.meao.possible_migrations[kdu_id]:
                if time.time() - self.meao.possible_migrations[kdu_id]["mem"] > kdu_mem_migration_policy.get("mem-threshold-time", 0):
                    return True
            else:
                self.meao.possible_migrations.setdefault(kdu_id, {})["mem"] = time.time()
        elif kdu_id in self.meao.possible_migrations and "mem" in self.meao.possible_migrations[kdu_id]:
            self.meao.possible_migrations[kdu_id].pop("mem", None)
        
        return False

        
    def check_latency_migration_need(self, kdu_id, migration_policy, kdu_current_node):
        """
        Processes latency information and determines whether a migration operation must be scheduled

        The migration logic can be resumed in the following manner:

            If a node is found where its latency is less than the current node's latency multiplied by the mobility migration factor:
                - the container must be migrated since the new node offers better conditions

        If this condition is not verified, the function returns None

        If the conditions for migration ARE verified, the function will then evaluate if the target node can support running the container,
        according to the application's Service-Level Agreement. If the target node can not support running the container, 
        the function will keep searching for a suitable node and eventually return the name of the suitable node with the least latency. 
        If no suitable node is found, it sends a Kafka message to notify the OSS of this occurrence and returns None

        Parameters
        ----------
        container : dict
            information relating to the container whose metrics are being processed, obtained from the containerInfo dictionary
        cName : str
            the container's ID
        """

        return False


    # Migration Decision Service Level Agreement (SLA) example
    #     cpu-criteria:
    #         allocated-cpu: 2     # The quantity of CPU allocated to the appi
    #         cpu-surge-capacity: 1    # The extra cpu capacity that the node must have free to allow for a extension of the usage for some time (this is some about of free resources shared by all the appis)
    #         cpu-threshold-time: 10    # The time in seconds that the CPU usage must be above the (node_capacity - (allocated-cpu + cpu-surge-capacity - current_app_cpu_usage)) value before the appi is migrated
    #         cooldown-time: 0  # The time to wait before checking the CPU usage again after a migration decision

    # The previous SLA basically means that I will allocate 2 cpu for the appi and I will allow for a surge up to allocated-cpu + cpu-surge-capacity for some time (cpu-threshold-time). If the node does not have free CPU resources of allocated-cpu - current_app_cpu_usage, the appi will be migrated immediately. If the node is not capable of offering the appi allocated-cpu - current_app_cpu_usage + cpu-surge-capacity, during the threshold, the appi should also be migrated. The cooldown time is the time to wait before checking the CPU usage again after a migration decision. This is to avoid causing unlimited migrations.

    # We migrate in the following cases:
    #   1. If the node does not have allocated-cpu - current_app_cpu_usage resources available, immediately
    #   2. If the node does not have ((allocated-cpu - current_app_cpu_usage) + cpu-surge-capacity) resources available for cpu-threshold-time seconds

    # The following cases might happen but are application related and it is not related with migration:
    #   1. If current_cpu_usage is greater than allocated-cpu for more than cpu-threshold-time seconds
    #   2. If current_cpu_usage is greater than allocated-cpu + cpu-surge-capacity
    # These are not related to migration because with migration nothing would be solved and the appi would keep being migrating infinitely. These can be solved by using namespace isolation with specific resource limits but this is not implemented in OSM yet and is not fully related with my dissertation so I will only worry about it for now. 

    # Node selection should be done across all available nodes and clusters and it will prioritize nodes running in the same cluster, then in the same domain and then will rank them based on the available resources (order by (cluster, domain, available resources)). The node with the most available resources will be selected first. If no node is found, the appi will not be migrated.

    # In terms of resources, it will be ordered by (latency, cpu, memory), which allows to select the node closest to the UE and with the most available resources. The node with the most available resources will be selected first. If no node is found, the appi will not be migrated.
