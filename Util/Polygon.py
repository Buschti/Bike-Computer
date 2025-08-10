from math import atan2, cos, sin, pi, radians, degrees

from shapely import LineString, Polygon

"""
This file provides methods to perform various operations related to polygons.

Methods:
    get_polygon_from_two_points: Calculates a polygon from two given points, width, and buffer.
    get_buffer_around_route: Calculates a buffer around the route for the given two points and buffer.
    get_streets_within_polygon: Returns the streets within the given polygon.
"""


def get_streets_within_polygon(street_ways: list, polygon: Polygon) -> list:
    """
    Returns the streets within the given polygon.

    :param street_ways: The street ways.
    :param polygon: The polygon.

    :return: A list of street ways within the polygon.
    """
    street_ways_within_polygon = []
    disallowed_highways = ['motorway', 'trunk', 'trunk_link', 'motorway_link']
    polygon_bounds = polygon.bounds

    for street_way in street_ways:
        bbox = street_way.get("bbox")
        if (bbox[0] <= polygon_bounds[2] and bbox[2] >= polygon_bounds[0] and
                bbox[1] <= polygon_bounds[3] and bbox[3] >= polygon_bounds[1] and
                street_way['highway'] not in disallowed_highways):
            street_ways_within_polygon.append(street_way)
    return street_ways_within_polygon


def get_polygon_from_two_points(lat1: float, lon1: float, lat2: float, lon2: float, width: float, buffer: float) -> Polygon:
    """
    Calculate a polygon for the given two points, width, and buffer.
    The polygon starts at the start coordinate - buffer, has the same direction as
    the line from start to goal and ends at the goal coordinate + buffer

    :param: lat1, lon1 (float): The latitude and longitude of the first point.
    :param: lat2, lon2 (float): The latitude and longitude of the second point.
    :param: width (float): The width of the polygon in kilometers.
    :param: buffer (float): The buffer in kilometers.

    :return:
         Polygon: A Shapely Polygon object.
    """
    if width < 1:
        width = width * 2
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    bearing = atan2(sin(dlon) * cos(lat2), cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon))

    perp_bearing = (bearing + pi / 2) % (2 * pi)

    # Calculate the latitude and longitude offsets for the width
    lat_offset = (width / 2) / 6371 * cos(perp_bearing)
    lon_offset = (width / 2) / (6371 * cos(lat1)) * sin(perp_bearing)

    lat_buffer = buffer / 6371 * cos(bearing)
    lon_buffer = buffer / (6371 * cos(lat1)) * sin(bearing)

    coords = [
        (lat1 - lat_offset - lat_buffer, lon1 - lon_offset - lon_buffer),
        (lat1 + lat_offset - lat_buffer, lon1 + lon_offset - lon_buffer),
        (lat2 + lat_offset + lat_buffer, lon2 + lon_offset + lon_buffer),
        (lat2 - lat_offset + lat_buffer, lon2 - lon_offset + lon_buffer),
        (lat1 - lat_offset - lat_buffer, lon1 - lon_offset - lon_buffer)
    ]

    coords = [(degrees(lat), degrees(lon)) for lat, lon in coords]

    return Polygon(coords)


def get_buffer_around_route(lat1: float, lon1: float, lat2: float, lon2: float, buffer: float) -> Polygon:
    """
    Calculate a buffer around the route for the given two points and buffer.

    :param lat1: The latitude of the first point.
    :param lon1: The longitude of the first point.
    :param lat2: The latitude of the second point.
    :param lon2: The longitude of the second point.
    :param buffer: The buffer in kilometers.

    :return: A shapely polygon
    """
    route_line = LineString([(lat1, lon1), (lat2, lon2)])
    buffer_in_degrees = buffer / 111.325
    route_buffer = route_line.buffer(buffer_in_degrees)
    return route_buffer


def get_bbox_from_tile_name(tile_name: str) -> dict:
    """
    Extracts the bounding box from the given tile name.

    The tile name is expected to be in the following format:
    "part_l{left}_b{bottom}_r{right}_t{top}.osm"
    :param tile_name: The tile name string.
    :return: Dictionary with the bounding box coordinates
    """
    parts = tile_name.split("_")
    parts[-1] = parts[-1].split(".osm")[0]
    bbox = {"left": round(float(parts[1].split('l')[1]), 5), "bottom": round(float(parts[2].split('b')[1]), 5),
            "right": round(float(parts[3].split('r')[1]), 5), "top": round(float(parts[4].split('t')[1]), 5)}

    return bbox
