from Graphs import Node


class Edge:
    """
    A class to represent an edge in a graph.

    This class represents an edge with a unique id, source node, target node, weight, and a dictionary of attributes.

    Attributes:
        id (int): The unique identifier for the edge.
        source (Node): The source node of the edge.
        target (Node): The target node of the edge.
        weight (float): The weight of the edge.
        attributes (dict): A dictionary of attributes for the edge.

    Methods:
        __str__(): Returns a string representation of the edge.
        __eq__(other): Determines if this edge is equal to another edge.
    """
    def __init__(self, id: int, source: Node, target: Node, weight: float):
        self.id = id
        self.source = source
        self.target = target
        self.weight = weight
        self.attributes = {}

    def __str__(self):
        return (f"Edge {self.id}:\n"
                f"Source and target node ID: ({self.source.id}, {self.target.id})\n"
                f"Weight: {self.weight} \n"
                f"Edge attributes:\n"
                f"{self.attributes}\n")

    def __eq__(self, other):
        return self.id == other.id and self.source == other.source and self.target == other.target
