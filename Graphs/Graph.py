import math, time
from shapely import LineString, Point

from Graphs.IGraph import IGraph
from collections import defaultdict
from Graphs.Edge import Edge
from Graphs.Node import Node
from Util.Haversine import Haversine


class Graph(IGraph):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.edges = defaultdict(list)

    def add_node(self, node: Node):
        if not isinstance(node, Node):
            raise TypeError("Invalid node type. Please provide a Node object.")
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge):
        if not isinstance(edge, Edge):
            raise TypeError("Invalid edge type. Please provide an Edge object.")
        self.edges[edge.source].append(edge)

    def get_neighbors(self, node: Node) -> list:
        return self.edges.get(node, [])

    def get_node(self, node_id: int) -> Node:
        return self.nodes.get(node_id)

    def build(self, street_ways: list):
        """
        Builds the graph.
        :param: street_ways: A list of street_ways that contain all the information for building the
                            graph, e.g. ID, length, geo etc.
        """
        print("Building graph...")
        start = time.time()
        haversine = Haversine()
        self.find_nodes(street_ways, haversine)
        self.initialize_edges(street_ways, haversine)
        end = time.time()
        print(f"Graph built in {end - start:.2f} seconds.")

    def get_all_nodes(self) -> list:
        return list(self.nodes.values())

    def get_all_edges(self) -> list:
        all_edges = []
        for node_id, edge_list in self.edges.items():
            all_edges.extend(edge_list)  # Flatten the dictionary structure
        return all_edges

    def get_nearest_node(self, latitude: float, longitude: float) -> Node:
        """
        Iterates through every node in the graph and uses the haversine distance to find the node closest to the coordinate.
        :param latitude: Latitude of the coordinate.
        :param longitude: Longitude of the coordinate.
        :return: Nearest node in the graph
        """
        haversine = Haversine()
        min_distance = float('inf')
        nearest_node = None

        for node in self.get_all_nodes():
            distance = haversine.haversine(latitude, longitude, node.latitude, node.longitude)
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        return nearest_node

    def apply_weight(self, mode='shortest'):
        """
            Applies weight to the edges of the graph based on the given mode.
            Openstreetmap tags are saved in attributes
            :param mode:
                'shortest': This mode uses the default weight which is just the length of the way in meters.
                'bicycle': Adjusts weight in favor of ways built for bicycles.
        """
        for edge_list in self.edges.values():
            for edge in edge_list:
                if edge.attributes.get('access') == 'private':
                    edge.weight = 9999
                if mode == 'bicycle':
                    if edge.attributes['highway'] == 'cycleway':
                        edge.weight *= 0.95
                    if edge.attributes.get('bicycle') in ['yes', 'use_sidepath']:
                        edge.weight *= 0.95
                    if edge.attributes.get('bicycle') == 'designated':
                        edge.weight *= 0.90
                    if edge.attributes.get('bicycle') == 'no':
                        edge.weight = 9999

    def find_nodes(self, street_ways: list, haversine: Haversine):
        """
            This method iterates over the provided street ways, and for each street, it calculates the closest node
            for each coordinate in the street's geometry. It then creates a Node object for each of these nodes and
            adds them to the graph.

            :param: street_ways (list): A list of dictionaries, each representing a street way. Each dictionary should
                contain a 'geo' key with a LineString value representing the street's geometry, and a 'nodes' key with a
                list of nodes on the street.
            :param: haversine (Haversine): An instance of the Haversine class, used to calculate
                distances between geographical points.

            :exception:
                TypeError: If the provided node is not an instance of the Node class.
        """
        haversine = Haversine()
        for street_data in street_ways:
            street_geometry = street_data.get("geo")
            if isinstance(street_geometry, LineString):
                coords = list(street_geometry.coords)
                for i in range(len(coords)):
                    closest_node_data = min(street_data.get("nodes"),
                                            key=lambda node_data: haversine.haversine(node_data["lat"],
                                                                                      node_data["lon"],
                                                                                      coords[i][1], coords[i][0]))
                    geo = Point(coords[i][0], coords[i][1])
                    node = Node(closest_node_data["id"], closest_node_data["lat"], closest_node_data["lon"], geo)
                    self.add_node(node)

    def initialize_edges(self, street_ways: list, haversine: Haversine):
        """
            Initializes edges in the graph based on the provided street ways and haversine function.

            This method iterates over the provided street ways, and for each street, it calculates the closest node
            for each coordinate in the street's geometry. It then creates an edge between each pair of consecutive
            nodes on the street, and adds these edges to the graph. The weight of each edge is calculated as the
            haversine distance between the source and target nodes. The edge's attributes are set to the street's
            data, excluding the 'w_id' and 'length' keys.

            :param: street_ways (list): A list of dictionaries,
                each representing a street way. Each dictionary should contain a 'geo' key with a LineString value
                representing the street's geometry, a 'w_id' key with the street's ID, and a 'nodes' key with a list of
                nodes on the street.
            :param: haversine (Haversine): An instance of the Haversine class, used to calculate
                distances between geographical points.

            :exception: TypeError: If the provided edge is not an instance of
            the Edge class.
        """
        for street_data in street_ways:
            street_geometry = street_data.get("geo")
            if isinstance(street_geometry, LineString):
                coords = list(street_geometry.coords)
                nodes_on_street = []
                for i in range(len(coords)):
                    closest_node_data = min(street_data.get("nodes"),
                                            key=lambda node_data: haversine.haversine(node_data["lat"],
                                                                                      node_data["lon"],
                                                                                      coords[i][1], coords[i][0]))
                    node = self.nodes.get(closest_node_data["id"])
                    if node:
                        nodes_on_street.append(node)

                for i in range(len(nodes_on_street) - 1):
                    source = nodes_on_street[i]
                    target = nodes_on_street[i + 1]
                    weight = haversine.haversine(source.latitude, source.longitude, target.latitude, target.longitude)
                    edge = Edge(street_data.get("w_id"), source, target, weight)
                    edge.attributes = {key: value for key, value in street_data.items() if
                                       key not in ["w_id", "length"]}
                    self.add_edge(edge)
                    reverse_edge = Edge(edge.id, edge.target, edge.source, edge.weight)
                    reverse_edge.attributes = edge.attributes
                    self.edges[edge.target].append(reverse_edge)

    def __str__(self):
        """
        Returns a string representation of the graph.
        """
        output = "Nodes:\n"
        for node_id, node in self.nodes.items():
            output += f"\tNode {node_id}: {node}\n"

        output += "Edges:\n"
        for node_id, edges in self.edges.items():
            for edge in edges:
                output += f"{edge}\n"
        return output
