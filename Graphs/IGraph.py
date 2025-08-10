from abc import ABC, abstractmethod
from Graphs import Edge
from Graphs import Node


class IGraph(ABC):
    """
    An abstract base class representing a graph.

    This class provides an interface for a graph, which can be implemented by any specific type of graph
    (e.g., directed, undirected, weighted, unweighted, etc.). It includes abstract methods for adding nodes and edges
    to the graph, getting neighbors of a node, getting a node by its id, getting all nodes and edges in the graph,
    and building the graph.

    Subclasses must implement the abstract methods to provide the functionality for a specific type of graph.

    Methods:
        add_node(node): Adds a Node object to the graph.
        add_edge(edge): Adds an Edge object to the graph.
        get_neighbors(node): Returns a list of edges connected to a specific node.
        get_node(node_id): Returns the Node object with the given ID.
        get_all_nodes(): Returns a list of all Node objects in the graph.
        get_all_edges(): Returns a list of all Edge objects in the graph.
        build(street_ways): Builds the graph.
    """

    @abstractmethod
    def add_node(self, node: Node):
        """
        Adds a Node object to the graph.

        Args:
            node (Node): An instance of the provided Node class.
        """
        pass

    @abstractmethod
    def add_edge(self, edge: Edge):
        """
        Adds an Edge object to the graph.

        Args:
        edge (Edge): An instance of the provided Edge class.
        """
        pass

    @abstractmethod
    def get_neighbors(self, node: Node) -> list:
        """
        Returns a list of edges connected to a specific node.

        Args:
            node (int): The node.

        Returns:
            list: A list of Edge objects connected to the node.
        """
        pass

    @abstractmethod
    def get_node(self, node_id: int) -> Node:
        """
        Returns the Node object with the given ID.

        Args:
        node_id (int): The ID of the node.

        Returns:
        Node: The Node object if found, None otherwise.
        """
        pass

    def get_all_nodes(self):
        """
        Returns a list of all Node objects in the graph.

        Returns:
            list: A list of Node objects.
        """
        pass

    def get_all_edges(self):
        """
        Returns a list of all Edge objects in the graph.

        Returns:
            list: A list of Edge objects.
        """
        pass

    @abstractmethod
    def build(self, street_ways: list):
        """
        Builds the graph.
        :param street_ways:
        A list of street_ways that contain all the information for building the graph, e.g. ID, length, geo etc.
        """
        pass
