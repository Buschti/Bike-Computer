import math

from Util.Haversine import Haversine
import os
import json


def normalize_coordinates(lat, lon, current_bbox):
    # TODO: maybe find a better place, because its not about config files
    min_lon, min_lat, max_lon, max_lat = current_bbox
    norm_lon = (lon - min_lon) / (max_lon - min_lon)
    norm_lat = (lat - min_lat) / (max_lat - min_lat)
    return norm_lat, norm_lon


def create_bbox_around_coordinate(latitude, longitude, radius_m):
    # TODO: maybe find a better place, because its not about config files
    earth_radius = 6378137

    d_lat = radius_m / earth_radius
    d_lon = radius_m / (earth_radius * math.cos(math.pi * latitude / 180))

    d_lat = d_lat * 180 / math.pi
    d_lon = d_lon * 180 / math.pi

    min_lat = latitude - d_lat
    max_lat = latitude + d_lat
    min_lon = longitude - d_lon
    max_lon = longitude + d_lon

    return min_lat, min_lon, max_lat, max_lon


def read_bbox_from_config(config_file):
    with open(config_file, 'r') as file:
        for line in file:
            if line.startswith('bbox:'):
                bbox_str = line.split(':')[1].strip().strip('[]')
                bbox = list(map(float, bbox_str.split(',')))
                return bbox
    return None


def get_bbox_from_config(config_file: str, tiles_directory: str) -> dict:
    bbox = []
    with open(os.path.join(tiles_directory, config_file), 'r') as f:
        for line in f:
            if "bbox" in line:
                bbox = line.strip().split(": ")[1].strip("[]").split(", ")
                bbox = [float(coord) for coord in bbox]
    return {'bottom': bbox[1], 'left': bbox[0], 'top': bbox[3], 'right': bbox[2]}


def get_neighbors_from_config(config_file: str, tiles_directory: str) -> list:
    neighbors = []
    with open(os.path.join(tiles_directory, config_file), 'r') as f:
        for line in f:
            if "neighbors" in line:
                neighbors = line.strip().split(": ")[1].strip("[]").split(", ")
                neighbors = [neighbor.strip("'") for neighbor in neighbors]
    return neighbors


def get_closest_neighbor(neighbors: list, goal_lat: float, goal_lon: float, tiles_directory: str) -> str:
    """
    Find the closest neighbor to the goal coordinates.
    :return: str: The name of the closest neighbor
    """
    haversine = Haversine()
    min_distance = float('inf')
    closest_neighbor = None
    for neighbor in neighbors:
        neighbor_name = neighbor.split(".osm.pbf")[0]
        neighbor_bbox = get_bbox_from_config(neighbor_name + "_config.txt", tiles_directory)
        neighbor_lat = (neighbor_bbox['top'] + neighbor_bbox['bottom']) / 2
        neighbor_lon = (neighbor_bbox['left'] + neighbor_bbox['right']) / 2
        distance = haversine.haversine(goal_lat, goal_lon, neighbor_lat, neighbor_lon)
        if distance < min_distance:
            min_distance = distance
            closest_neighbor = neighbor
    return closest_neighbor


def find_path(start_lat: float, start_lon: float, goal_lat: float, goal_lon: float, tiles_directory: str) -> list:
    """
    Find the path from the start to the goal coordinates. Every tile has a corresponding config file that contains the
    neighbors and the bbox of the tile. The path is found by traversing the tiles based on the closest neighbor to the
    goal coordinates.
    :return: list: A list containing the names of the tiles in the path. The names are used to access the pbf files
                    in constant time.
    """
    for tile in os.listdir(tiles_directory):
        if tile.endswith(".osm.pbf"):
            tile_name = tile.split(".osm.pbf")[0]
            bbox = get_bbox_from_config(f"{tile_name}_config.txt", tiles_directory)
            if bbox['bottom'] <= start_lat <= bbox['top'] and bbox['left'] <= start_lon <= bbox['right']:
                start_tile = tile_name
                break

    path = [start_tile]
    while True:
        neighbors = get_neighbors_from_config(f"{path[-1]}_config.txt", tiles_directory)
        next_tile = get_closest_neighbor(neighbors, goal_lat, goal_lon, tiles_directory)
        next_tile_name = next_tile.split(".osm.pbf")[0]
        path.append(next_tile_name)
        next_bbox = get_bbox_from_config(f"{next_tile_name}_config.txt", tiles_directory)
        if next_bbox['bottom'] <= goal_lat <= next_bbox['top'] and next_bbox['left'] <= goal_lon <= next_bbox['right']:
            break

    return path
