import sys
import time

from PySide6.QtWidgets import QApplication

import LCDDriver.DisplayButtonManager
# from PySide6.QtWidgets import QApplication
# from matplotlib import pyplot as plt

from GUI.MainWindow import MainWindow
from Graphs.Graph import Graph
from LCDDriver.DisplayBridge import DisplayBridge
from Util import Plot, Config
from Routing.AStar import AStar
from StreetHandler import StreetsHandler
from Util.Haversine import Haversine

if __name__ == '__main__':
    start_time = time.time()
    graph = Graph()
    astar = AStar(graph)
    haversine = Haversine()
    street_handler = StreetsHandler("tile_config_dynamic/regensburg_config.txt")
    regensburg_osm = f"regensburg2-small.osm.pbf"

    start_lat, start_lon = 49.0165, 12.0420
    goal_lat, goal_lon = 49.0131, 12.1516

    """
    Normal boot with matplotlib and pre coded route
    street_start = time.time()
    # street_handler.build_handler_from_tiles(f"OpenStreetMapData/regensburg_3_3_20", start_lat, start_lon, goal_lat, goal_lon)
    # street_handler.build_handler_from_tree(f"regensburg_tree_3_3_20", start_lat, start_lon, goal_lat, goal_lon) #TODO cant find directory when in opmd folder
    path = Config.find_path(start_lat, start_lon, goal_lat, goal_lon,
                            "tile_config_dynamic")  # TODO tiles too small, sometimes doesnt find path
    street_handler.apply_handler_to_tiles(path, "tile_config_dynamic")
    print(f"{path}")
    street_end = time.time()
    print(f"Extracting pbf took: {street_end - street_start} seconds.")

    fig, ax = plt.subplots(figsize=(30, 30))

    graph_start = time.time()
    graph.build(street_handler.street_ways)
    graph.apply_weight('shortest')
    graph_end = time.time()
    print(f"Building graph took: {graph_end - graph_start} seconds.")

    graph_plot_start = time.time()
    graph.plot_without_geo(ax, color='grey', node_size=0.5, node_color='red')
    graph_plot_end = time.time()
    print(f"Plotting graph took: {graph_plot_end - graph_plot_start} seconds.")

    start_node = graph.get_nearest_node(start_lat, start_lon)
    goal_node = graph.get_nearest_node(goal_lat, goal_lon)

    path, cost = astar.search(start_node, goal_node)
    path_start = time.time()
    path_length = haversine.calculate_street_length_haversine(path, haversine.haversine)
    path_end = time.time()
    print(f"Calculating path took: {path_end - path_start} seconds.")

    path_plot_start = time.time()
    Plot.plot_path(ax, path, color='blue', linewidth=1)
    fig.suptitle(f"Shortest Path (Total Cost: {path_length:.2f} meters)", fontsize=34)
    path_plot_end = time.time()
    print(f"Plotting path took {path_plot_end - path_plot_start} seconds")

    plt.show()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"{elapsed_time} seconds")
    """
    # GUI boot with PySide6
    app = QApplication(sys.argv)
    window = MainWindow(street_handler)
    window.setFixedSize(256, 256)
    display = DisplayBridge(window)
    button_manager = LCDDriver.DisplayButtonManager.ButtonManager(window, display.lcd)
    window.show()
    app.exec()
