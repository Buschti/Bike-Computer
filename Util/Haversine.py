from math import radians, sin, cos, asin, sqrt


class Haversine:
    """
    A class to calculate the haversine distance between two geographical points.

    This class provides methods to calculate the haversine distance between two geographical points and the total
     haversine distance between a list of geographical points. The haversine formula is used to calculate the
     great-circle distance between two points – that is, the shortest distance over the earth's surface – giving an
      "as-the-crow-flies" distance between the points (ignoring any hills, valleys, or other potential obstacles).

    Attributes:
        EARTH_RADIUS_KM (float): The radius of the Earth in kilometers.

    Methods:
        calculate_street_length_haversine(nodes, haversine): Calculates the total haversine distance between a list of
                                                            geographical points.
        haversine(lon1, lat1, lon2, lat2): Calculates the haversine distance between two geographical points.
    """
    def __init__(self):
        self.EARTH_RADIUS_KM: float = 6378.1370

    def calculate_street_length_haversine(self, nodes: list, haversine) -> float:
        """
        Calculates the total distance between a list of nodes using the haversine formula.

        This method iterates over the provided list of nodes, and for each pair of consecutive nodes,
        it calculates the haversine distance between them. It then adds these distances to a total distance,
        which is returned at the end.

        :param: nodes (list): A list of Node objects, each representing a geographical point.
        :param: haversine: haversine function

        :return:
            float: The total haversine distance between the provided nodes.
        """
        total_distance = 0
        for i in range(len(nodes) - 1):
            lon1 = nodes[i].longitude
            lat1 = nodes[i].latitude
            lon2 = nodes[i + 1].longitude
            lat2 = nodes[i + 1].latitude
            distance = self.haversine(lon1, lat1, lon2, lat2)
            total_distance += distance
        return total_distance

    def haversine(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Haversine formula to calculate the distance between two coordinates.
        :param lon1: longitude of the first coordinate
        :param lat1: latitude of the first coordinate
        :param lon2: longitude of the second coordinate
        :param lat2: latitude of the second coordinate
        :return: Total distance in meters
        """
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371e3
        return c * r
