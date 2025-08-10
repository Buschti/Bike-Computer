import os
import queue

import osmium
import shapely.wkb as wkblib
from shapely import Point, Polygon
from Util.Haversine import Haversine
from Util.Polygon import get_buffer_around_route, get_bbox_from_tile_name, get_polygon_from_two_points
from Util.Config import get_bbox_from_config, create_bbox_around_coordinate, read_bbox_from_config


class StreetsHandler(osmium.SimpleHandler):
    """
    A class to handle street data from OpenStreetMap.

    This class inherits from osmium.SimpleHandler and is used to process OpenStreetMap data. It specifically handles
     'way' elements in the data, which represent streets. It extracts relevant information from these elements,
      such as their id, bounding box, geographical representation, length, and associated tags. It also provides
      methods to build the handler from tiles or a tree structure of tiles.

    Attributes:
        haversine (Haversine): An instance of the Haversine class to calculate distances.
        num_ways (int): The number of 'way' elements processed.
        ways (list): A list of dictionaries, each representing a 'way' element (street).
        wkbfab (osmium.geom.WKBFactory): A factory to create WKB (Well-Known Binary) representations of OSM elements.

    Methods:
        way(w): Processes a 'way' element from the OSM data.
        build_handler_from_tiles(tiles_directory, start_lat, start_lon, goal_lat, goal_lon): Builds the handler by
                    traversing the split pbf files linearly.
        build_handler_from_tree(tiles_directory, start_lat, start_lon, goal_lat, goal_lon): Builds the handler by
                    traversing the split pbf files non-linearly.
    """
    haversine = Haversine()

    def __init__(self, config_file):
        osmium.SimpleHandler.__init__(self)
        self.num_ways = 0
        self.ways = []
        self.wkbfab = osmium.geom.WKBFactory()
        self.loaded_pbf_files = {}
        self.current_bbox = read_bbox_from_config(config_file)

    def way(self, w):
        if w.tags.get("highway"):
            try:
                wkb = self.wkbfab.create_linestring(w)
                geo = wkblib.loads(wkb, hex=True)
                way_nodes = [{"id": node.ref, "lat": node.location.lat, "lon": node.location.lon} for node in w.nodes]
            except:
                return

            start_point = Point(w.nodes[0].location.lat, w.nodes[0].location.lon)
            end_point = Point(w.nodes[-1].location.lat, w.nodes[-1].location.lon)
            minx, miny, maxx, maxy = (min(start_point.x, end_point.x), min(start_point.y, end_point.y),
                                      max(start_point.x, end_point.x), max(start_point.y, end_point.y))
            bbox = (minx, miny, maxx, maxy)

            row = {"w_id": w.id, "bbox": bbox, "geo": geo, "length": osmium.geom.haversine_distance(w.nodes),
                   "nodes": way_nodes}

            for key, value in w.tags:
                row[key] = value

            self.ways.append(row)
            self.num_ways += 1

    def build_handler_from_tiles(self, tiles_directory: str, start_lat: float, start_lon: float, goal_lat: float,
                                 goal_lon: float):
        """
        Traverses the split pbf files linearly and applies them to the StreetHandler. O(n)
        :param tiles_directory: one folder with every pbf file.
        """
        route_buffer = get_buffer_around_route(start_lat, start_lon, goal_lat, goal_lon, 0.1)
        bbox = route_buffer.bounds
        bbox_dict = {"left": bbox[1], "bottom": bbox[0], "right": bbox[3], "top": bbox[2]}

        tiles = os.listdir(tiles_directory)
        for tile in tiles:
            if tile.endswith(".osm.pbf"):
                tile_name = tile.split(".osm.pbf")[0]
                tile_bbox = get_bbox_from_config(f"{tile_name}", tiles_directory)
                if (bbox_dict["left"] <= tile_bbox["right"] and bbox_dict["right"] >= tile_bbox["left"] and
                        bbox_dict["bottom"] <= tile_bbox["top"] and bbox_dict["top"] >= tile_bbox["bottom"]):
                    tile_file = os.path.join(tiles_directory, tile)
                    self.apply_file(tile_file, locations=True, idx='flex_mem')

    def build_handler_from_tree(self, tiles_directory: str, start_lat: float, start_lon: float, goal_lat: float,
                                goal_lon: float):
        """
        Traverses the split pbf files non-linearly and applies them to the StreetHandler.
        :param tiles_directory: structured like a tree. One main folder that contains row * col sub-folders.
                                These sub-folders also contain sub-folders. The number of sub-folder is determined by
                                the precision of the grid.
        """
        # route_buffer = get_buffer_around_route(start_lat, start_lon, goal_lat, goal_lon, 0.01)
        # bbox = route_buffer.bounds
        # # bbox_dict = {"left": bbox[1], "bottom": bbox[0], "right": bbox[3], "top": bbox[2]}
        # bbox_dict = {"bottom": bbox[0], "left": bbox[1], "top": bbox[2], "right": bbox[3]}
        #
        # dir_queue = queue.Queue()
        # dir_queue.put(tiles_directory)
        #
        # while not dir_queue.empty():
        #     current_dir = dir_queue.get()
        #     for entry in os.scandir(current_dir):
        #         if entry.is_dir():
        #             dir_bbox = get_bbox_from_tile_name(entry.name)
        #             if (bbox_dict["left"] <= dir_bbox["right"] and bbox_dict["right"] >= dir_bbox["left"] and
        #                     bbox_dict["bottom"] <= dir_bbox["top"] and bbox_dict["top"] >= dir_bbox["bottom"]):
        #                 dir_queue.put(entry.path)
        #         elif entry.is_file():
        #             self.apply_file(entry.path, locations=True, idx='flex_mem')
        route_polygon = get_polygon_from_two_points(start_lat, start_lon, goal_lat, goal_lon, 1, 0.25)

        dir_queue = queue.Queue()
        dir_queue.put(tiles_directory)

        while not dir_queue.empty():
            current_dir = dir_queue.get()
            for entry in os.scandir(current_dir):
                if entry.is_dir():
                    dir_bbox = get_bbox_from_tile_name(entry.name)
                    dir_polygon = Polygon([(dir_bbox['bottom'], dir_bbox['left']),
                                           (dir_bbox['bottom'], dir_bbox['right']),
                                           (dir_bbox['top'], dir_bbox['right']),
                                           (dir_bbox['top'], dir_bbox['left'])])
                    # coords = dir_polygon.coords
                    if route_polygon.intersects(dir_polygon):
                        dir_queue.put(entry.path)
                elif entry.is_file():
                    self.apply_file(entry.path, locations=True, idx='flex_mem')

    def apply_handler_to_tiles(self, tiles: list, tiles_directory: str):
        """
        Applies the StreetsHandler to each tile in the given list of tiles.
        """
        for tile in tiles:
            tile_file = os.path.join(tiles_directory, tile + ".osm.pbf")
            self.apply_file(tile_file, locations=True, idx='flex_mem')

    def build_handler_from_current_position(self, latitude, longitude, tiles_directory, radius_m):
        # Builds the handler from the current position by loading all tiles that are within a certain radius.
        # But only within that bbox. A too small radius will not load any tiles.

        min_lat, min_lon, max_lat, max_lon = create_bbox_around_coordinate(latitude, longitude, radius_m)
        print(f"bottom: {min_lat}, left: {min_lon}, top: {max_lat}, right: {max_lon}")
        tiles = os.listdir(tiles_directory)
        for tile in tiles:
            if tile.endswith(".osm.pbf"):
                tile_name = tile.split(".osm.pbf")[0]
                bbox = get_bbox_from_config(f"{tile_name}_config.txt", tiles_directory)
                if min_lat <= bbox['bottom'] and max_lat >= bbox['top'] and min_lon <= bbox['left'] and max_lon >= bbox[
                    'right']:
                    if tile_name not in self.loaded_pbf_files:
                        tile_file = os.path.join(tiles_directory, tile)
                        self.apply_file(tile_file, locations=True, idx='flex_mem')
                        self.loaded_pbf_files[tile_name] = bbox
        print(f"Tiles loaded: {len(self.loaded_pbf_files)}")

    def build_handler_from_current_positions_intersections(self, latitude, longitude, tiles_directory, radius_m):
        """
        Builds the handler from the current position by loading all tiles that intersect with a certain radius.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            tiles_directory: Directory containing tile files
            radius_m: Radius in meters to search for tiles
        """
        min_lat, min_lon, max_lat, max_lon = create_bbox_around_coordinate(latitude, longitude, radius_m)
        print(f"Search area - bottom: {min_lat}, left: {min_lon}, top: {max_lat}, right: {max_lon}")

        tiles = os.listdir(tiles_directory)
        newly_loaded = 0

        for tile in tiles:
            if tile.endswith(".osm.pbf"):
                tile_name = tile.split(".osm.pbf")[0]

                # Skip already loaded tiles
                if tile_name in self.loaded_pbf_files:
                    continue

                bbox = get_bbox_from_config(f"{tile_name}_config.txt", tiles_directory)

                # Check for ANY intersection between bounding boxes
                if (min_lat <= bbox['top'] and max_lat >= bbox['bottom'] and
                        min_lon <= bbox['right'] and max_lon >= bbox['left']):
                    tile_file = os.path.join(tiles_directory, tile)
                    self.apply_file(tile_file, locations=True, idx='flex_mem')
                    self.loaded_pbf_files[tile_name] = bbox
                    newly_loaded += 1

        print(f"Newly loaded tiles: {newly_loaded}, Total tiles loaded: {len(self.loaded_pbf_files)}")
