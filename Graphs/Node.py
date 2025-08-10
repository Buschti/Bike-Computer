from shapely import Point


class Node:
    """
    A class to represent a geographical node.

    This class represents a node with a unique id, latitude, longitude, and a geographical point (geo) using the shapely library.

    Attributes:
        id (int): The unique identifier for the node.
        latitude (float): The latitude of the node.
        longitude (float): The longitude of the node.
        geo (Point): A Point object from the shapely library representing the geographical point of the node.

    Methods:
        __hash__(): Returns a hash value for the node.
        __eq__(other): Determines if this node is equal to another node.
        __str__(): Returns a string representation of the node.
    """
    def __init__(self, id: int, latitude: float, longitude: float, geo: Point):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.geo = geo

    def __hash__(self):
        return hash((self.id, self.latitude, self.longitude))

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id or self.latitude == other.latitude and self.longitude == other.longitude
        else:
            return False

    def __str__(self):
        return f"Node(id: {self.id}, Coordinates(lat, lon): {self.latitude}, {self.longitude}, Geo: {self.geo})"
