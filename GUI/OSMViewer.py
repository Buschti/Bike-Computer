from PySide6.QtGui import QPainter, QPen, QBrush
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsEllipseItem, QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QRectF, QPointF
import Util.Config
from Util.Config import read_bbox_from_config, normalize_coordinates
from Map.TileLoader import ParallelTileLoader

from PySide6.QtCore import QThread, Signal, QObject, QMutex

import os


class TileLoaderSignals(QObject):
    """Signals for the TileLoader thread"""
    finished = Signal(list)  # Signal emitted when loading is done, passing new tile names


class TileLoader(QThread):
    """Thread for loading map tiles without freezing the GUI"""

    def __init__(self, handler, tiles_dir, blacklisted_tiles=None):
        super().__init__()
        self.handler = handler
        self.tiles_dir = tiles_dir
        self.signals = TileLoaderSignals()
        self.mutex = QMutex()  # For thread safety
        self.blacklisted_tiles = blacklisted_tiles or []

        # These will be set by different loading strategies
        self.min_lat = None
        self.min_lon = None
        self.max_lat = None
        self.max_lon = None
        self.specific_tiles = None

    def load_by_viewport(self, min_lat, min_lon, max_lat, max_lon):
        """Set up tile loading based on viewport coordinates"""
        self.min_lat = min_lat
        self.min_lon = min_lon
        self.max_lat = max_lat
        self.max_lon = max_lon
        self.specific_tiles = None
        return self

    def load_by_route(self, path):
        """Set up tile loading based on a route path"""
        # Calculate bounding box for entire route
        self.min_lat = min(node.latitude for node in path)
        self.min_lon = min(node.longitude for node in path)
        self.max_lat = max(node.latitude for node in path)
        self.max_lon = max(node.longitude for node in path)
        self.specific_tiles = None
        return self

    def load_specific_tiles(self, tile_names):
        """Load specific tiles by name"""
        self.specific_tiles = tile_names
        return self

    def run(self):
        """Main thread execution"""
        import os
        newly_loaded_tiles = []

        if self.specific_tiles:
            # Load specific tiles by name
            for tile_name in self.specific_tiles:
                self._load_tile(tile_name, newly_loaded_tiles)
        else:
            # Load tiles by bounding box
            tiles = os.listdir(self.tiles_dir)
            for tile in tiles:
                if tile.endswith(".osm.pbf"):
                    tile_name = tile.split(".osm.pbf")[0]

                    # Skip already loaded or blacklisted tiles
                    if self._should_skip_tile(tile_name):
                        continue

                    # Get tile bounds
                    bbox = read_bbox_from_config(f"{self.tiles_dir}/{tile_name}_config.txt")

                    # Check if this tile intersects with our area of interest
                    if (self.min_lat <= bbox[3] and self.max_lat >= bbox[1] and
                            self.min_lon <= bbox[2] and self.max_lon >= bbox[0]):
                        self._load_tile(tile_name, newly_loaded_tiles)

        # Signal completion with list of newly loaded tiles
        self.signals.finished.emit(newly_loaded_tiles)

    def _should_skip_tile(self, tile_name):
        """Check if tile should be skipped"""
        self.mutex.lock()
        already_loaded = tile_name in self.handler.loaded_pbf_files
        blacklisted = tile_name in self.blacklisted_tiles
        self.mutex.unlock()
        return already_loaded or blacklisted

    def _load_tile(self, tile_name, newly_loaded_tiles):
        """Load a single tile and add to the list of loaded tiles"""
        tile_file = os.path.join(self.tiles_dir, f"{tile_name}.osm.pbf")
        if not os.path.exists(tile_file):
            print(f"Tile file not found: {tile_file}")
            return

        self.mutex.lock()
        try:
            self.handler.apply_file(tile_file, locations=True, idx='flex_mem')
            # Get bbox from config file
            bbox = read_bbox_from_config(f"{self.tiles_dir}/{tile_name}_config.txt")
            self.handler.loaded_pbf_files[tile_name] = bbox
            newly_loaded_tiles.append(tile_name)
            print(f"Loaded new tile in thread: {tile_name}")
        except Exception as e:
            print(f"Error loading tile {tile_name}: {e}")
        finally:
            self.mutex.unlock()


class OSMViewer(QGraphicsView):
    def __init__(self, config_file, handler):
        super().__init__()
        # Initialize the View
        self.setViewport(QOpenGLWidget())
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # Add these lines for better performance
        # self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        # self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Only enable when not moving

        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontSavePainterState |
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        # Cache the background
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.resize(400, 400)
        self.scale(8, 8)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Group scene updates
        self.scene.setBspTreeDepth(10)  # Higher depth can help with large scenes
        # Initialize the OSM handler
        self.handler = handler
        self.config = config_file
        self.viewport_rect = QRectF()
        self.tile_load_buffer = 0.0000001  # Buffer to check for adjacent tiles
        self.tiles_dir = "tile_config_dynamic"

        self.setup_tile_loader()

        self.blacklisted_tiles = ['1_1_3_3', '1_1_4_4', '1_1_4_3', '1_1_3_4', '1_1_3_5', '1_1_4_5']

        start_latitude, start_longitude = 49.01914, 12.09408
        start_position = (start_latitude, start_longitude)

        # First, center the view on the starting position (BEFORE loading tiles)
        norm_lat, norm_lon = Util.Config.normalize_coordinates(start_position[0], start_position[1],
                                                               read_bbox_from_config(self.config))
        scene_x = norm_lon * 1000
        scene_y = -norm_lat * 1000
        self.centerOn(scene_x, scene_y)

        self.handler.build_handler_from_current_positions_intersections(start_position[0], start_position[1],
                                                                        "tile_config_dynamic",
                                                                        100)
        self.check_viewport_position()
        # self.horizontalScrollBar().valueChanged.connect(self.check_viewport_position)
        # self.verticalScrollBar().valueChanged.connect(self.check_viewport_position)

        # self.centerOn(scene_x, scene_y)
        # Add the event connections

        pen = QPen(Qt.GlobalColor.black)
        pen.setCosmetic(True)  # False = pen width in pixels, True = pen width in device-independent pixels
        for way_data in self.handler.ways:
            way_nodes = way_data['nodes']
            pen.setCosmetic(True)
            pen.setWidth(1)
            if way_data.get('lanes') and int(way_data.get('lanes')) >= 2:
                pen.setWidth(4)
            if way_data.get('surface') == 'asphalt':
                pen.setColor(Qt.GlobalColor.gray)
            if way_data.get('highway') == 'cycleway' or way_data.get('bicycle') == 'designated':
                pen.setColor(Qt.GlobalColor.darkBlue)
            if way_data.get('waterway') == 'river':
                pen.setCosmetic(False)
                pen.setWidth(10)
                pen.setColor(Qt.GlobalColor.cyan)
            if way_data.get('building'):
                pen.setColor(Qt.GlobalColor.darkRed)
            # else:
            #     pen.setWidth(1)
            if len(way_nodes) > 1:
                for i in range(len(way_nodes) - 1):
                    lat1, lon1 = normalize_coordinates(way_nodes[i].get('lat'), way_nodes[i].get('lon'),
                                                       read_bbox_from_config(
                                                           config_file))
                    lat2, lon2 = normalize_coordinates(way_nodes[i + 1].get('lat'), way_nodes[i + 1].get('lon'),
                                                       read_bbox_from_config(config_file))
                    line = QGraphicsLineItem(lon1 * 1000, -lat1 * 1000, lon2 * 1000, -lat2 * 1000)
                    line.setPen(pen)
                    self.scene.addItem(line)

        self.current_position_marker(start_position[0], start_position[1], pen)
        self.setSceneRect(self.scene.itemsBoundingRect())

        # Center the view on the starting position
        # self.centerOn(scene_x, scene_y)

        print(f"Loaded pbf files: {self.handler.loaded_pbf_files.keys()}")

    # def wheelEvent(self, event):
    #   zoom_in_factor = 1.25
    #  zoom_out_factor = 1 / zoom_in_factor
    #
    #       if event.angleDelta().y() > 0:
    #          zoom_factor = zoom_in_factor
    #     else:
    #        zoom_factor = zoom_out_factor
    #
    #       self.scale(zoom_factor, zoom_factor)

    def current_position_marker(self, latitude, longitude, pen):
        norm_lat, norm_lon = Util.Config.normalize_coordinates(latitude, longitude, read_bbox_from_config(self.config))
        marker = QGraphicsEllipseItem(norm_lon * 1000 - 5, -norm_lat * 1000 - 5, 5, 5)
        marker.setBrush(QBrush(Qt.GlobalColor.red))
        marker.setPen(pen)
        self.scene.addItem(marker)

    def update_position(self, latitude, longitude):
        self.scene.clear()
        # self.handler.build_handler_from_current_position(latitude, longitude, "tile_config_dynamic", 1500)
        pen = QPen(Qt.GlobalColor.black)
        pen.setCosmetic(True)

    def update_map(self, latitude, longitude):
        self.scene.clear()
        self.update_position(latitude, longitude)
        pen = QPen(Qt.GlobalColor.black)
        pen.setCosmetic(True)
        for way_data in self.handler.ways:
            way_nodes = way_data['nodes']
            pen.setCosmetic(True)
            pen.setWidth(1)
            if way_data.get('lanes') and int(way_data.get('lanes')) >= 2:
                pen.setWidth(4)
            if way_data.get('surface') == 'asphalt':
                pen.setColor(Qt.GlobalColor.gray)
            if way_data.get('highway') == 'cycleway' or way_data.get('bicycle') == 'designated':
                pen.setColor(Qt.GlobalColor.darkBlue)
            if way_data.get('waterway') == 'river':
                pen.setCosmetic(False)
                pen.setWidth(10)
                pen.setColor(Qt.GlobalColor.cyan)
            if way_data.get('building'):
                pen.setColor(Qt.GlobalColor.darkRed)
            # else:
            #     pen.setWidth(1)
            if len(way_nodes) > 1:
                for i in range(len(way_nodes) - 1):
                    lat1, lon1 = normalize_coordinates(way_nodes[i].get('lat'), way_nodes[i].get('lon'),
                                                       read_bbox_from_config(
                                                           self.config))
                    lat2, lon2 = normalize_coordinates(way_nodes[i + 1].get('lat'), way_nodes[i + 1].get('lon'),
                                                       read_bbox_from_config(self.config))
                    line = QGraphicsLineItem(lon1 * 1000, -lat1 * 1000, lon2 * 1000, -lat2 * 1000)
                    line.setPen(pen)
                    self.scene.addItem(line)

        self.current_position_marker(latitude, longitude, pen)
        self.setSceneRect(self.scene.itemsBoundingRect())

        norm_lat, norm_lon = normalize_coordinates(latitude, longitude, read_bbox_from_config(self.config))
        scene_x = norm_lon * 1000
        scene_y = -norm_lat * 1000

        # Center the view on the updated position
        self.centerOn(scene_x, scene_y)

        print(f"Loaded pbf files: {self.handler.loaded_pbf_files.keys()}")

    def check_viewport_position(self):
        """Check if viewport is near edge of any loaded tile and load new tiles if needed"""
        # Get current viewport in scene coordinates - this is affected by zoom level
        viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()

        # Convert viewport corners to geo coordinates
        top_left = self.scene_to_geo(viewport_rect.topLeft())
        bottom_right = self.scene_to_geo(viewport_rect.bottomRight())

        # Use the actual viewport boundaries instead of forcing a square
        min_lat = min(top_left[0], bottom_right[0])
        max_lat = max(top_left[0], bottom_right[0])
        min_lon = min(top_left[1], bottom_right[1])
        max_lon = max(top_left[1], bottom_right[1])

        # Store current viewport for reference
        self.viewport_rect = QRectF(QPointF(min_lon, min_lat),
                                    QPointF(max_lon, max_lat))

        print(f"Viewport bounds: lat: {min_lat:.6f} to {max_lat:.6f}, lon: {min_lon:.6f} to {max_lon:.6f}")

        # Check if we're near the edge of any loaded tile
        self.check_and_load_adjacent_tiles(min_lat, min_lon, max_lat, max_lon)

    def scene_to_geo(self, point):
        """Convert scene coordinates to geo coordinates"""
        # Convert scene coordinates back to normalized coordinates
        norm_lon = point.x() / 1000
        norm_lat = -point.y() / 1000

        # Convert normalized coordinates to actual geo coordinates
        bbox = read_bbox_from_config(self.config)
        lat = norm_lat * (bbox[3] - bbox[1]) + bbox[1]
        lon = norm_lon * (bbox[2] - bbox[0]) + bbox[0]

        return (lat, lon)

    def check_and_load_adjacent_tiles(self, min_lat, min_lon, max_lat, max_lon):
        """Check if we need to load new tiles and load them in parallel with progressive updates"""
        # Check if already loading
        if hasattr(self, 'parallel_loader') and hasattr(self.parallel_loader,
                                                        'pending_tiles') and self.parallel_loader.pending_tiles > 0:
            print("Tile loading already in progress, skipping request")
            return

        # Create and start the parallel loader
        self.parallel_loader = ParallelTileLoader(self.handler, "tile_config_dynamic", self.blacklisted_tiles)

        # Connect signals for progressive updates
        self.parallel_loader.tile_loaded.connect(self.on_single_tile_loaded)
        self.parallel_loader.all_finished.connect(self.on_all_tiles_loaded)

        # Start loading
        self.parallel_loader.load_tiles(min_lat, min_lon, max_lat, max_lon)
        print("Started parallel tile loading")

        # def on_single_tile_loaded(self, tile_name):
        #     """Update the map incrementally as each tile loads"""
        #     # Remember current center position
        #     center_point = self.mapToScene(self.viewport().rect().center())
        #     center_geo = self.scene_to_geo(center_point)
        #
        #     # Partial redraw - only add new ways from this tile
        #     for way_data in self.handler.ways:
        #         # Only process ways from the just-loaded tile (this requires adding tile tracking to ways)
        #         if way_data.get('_tile_name') == tile_name:
        #             self.draw_way(way_data)

        # print(f"Incrementally updated map with tile: {tile_name}")

    def on_all_tiles_loaded(self):
        """Final update after all tiles are loaded"""
        print("All tiles loaded, finalizing map")

    #     # Set scene rect to encompass all loaded tiles
    #     min_lat = min_lon = float('inf')
    #     max_lat = max_lon = float('-inf')
    #
    #     # Find the bounds of all loaded tiles
    #     for bbox in self.handler.loaded_pbf_files.values():
    #         min_lat = min(min_lat, bbox.get('min_lat', min_lat))
    #         min_lon = min(min_lon, bbox.get('min_lon', min_lon))
    #         max_lat = max(max_lat, bbox.get('max_lat', max_lat))
    #         max_lon = max(max_lon, bbox.get('max_lon', min_lon))
    #
    #     if min_lat != float('inf'):
    #         # Convert to scene coordinates
    #         norm_min_lat, norm_min_lon = normalize_coordinates(min_lat, min_lon,
    #                                                            read_bbox_from_config(self.config))
    #         norm_max_lat, norm_max_lon = normalize_coordinates(max_lat, max_lon,
    #                                                            read_bbox_from_config(self.config))
    #
    #         # Set scene rect with some padding
    #         self.setSceneRect(
    #             norm_min_lon * 1000 - 100,
    #             -norm_max_lat * 1000 - 100,
    #             (norm_max_lon - norm_min_lon) * 1000 + 200,
    #             (norm_max_lat - norm_min_lat) * 1000 + 200
    #         )

    def cleanup_thread(self):
        """Clean up thread resources when finished"""
        if hasattr(self, 'tile_loader'):
            try:
                # Safely disconnect signals
                self.tile_loader.signals.finished.disconnect(self.on_tiles_loaded)
            except Exception:
                pass  # In case signal was already disconnected
            print("Thread completed and cleaned up")

    def on_single_tile_loaded(self, tile_name):
        # Remember current center position
        center_point = self.mapToScene(self.viewport().rect().center())
        center_geo = self.scene_to_geo(center_point)

        # Partial redraw - only add new ways from this tile
        for way_data in self.handler.ways:
            if way_data.get('_tile_name') == tile_name:
                self.draw_way(way_data)

        # Update scene rect to include new items
        self.setSceneRect(self.scene.itemsBoundingRect())

        # Re-center on the same position
        norm_lat, norm_lon = normalize_coordinates(center_geo[0], center_geo[1],
                                                   read_bbox_from_config(self.config))
        self.centerOn(norm_lon * 1000, -norm_lat * 1000)

        QApplication.processEvents()
        print(f"Incrementally updated map with tile: {tile_name}")

    def manual_load_tiles(self):
        """Manually check viewport and load tiles on button press"""
        print("Manual tile loading triggered")
        self.check_viewport_position()

    def clear_navigation_elements(self):
        """Clear only navigation-related elements without redrawing the entire map"""
        # Find and remove only navigation elements (blue lines, markers, etc)
        items_to_remove = []

        for item in self.scene.items():
            # Check if item is a navigation element (route line, marker, etc.)
            if isinstance(item, QGraphicsLineItem):
                # Check for blue pen color (route lines)
                if item.pen().color() == Qt.GlobalColor.blue:
                    items_to_remove.append(item)
            # Navigation markers are typically ellipses with specific colors
            elif isinstance(item, QGraphicsEllipseItem):
                if item.brush().color() in [Qt.GlobalColor.green, Qt.GlobalColor.red]:
                    items_to_remove.append(item)
            # Add other navigation element types here

        # Remove the identified items
        for item in items_to_remove:
            self.scene.removeItem(item)

        print(f"Cleared {len(items_to_remove)} navigation elements")

    def wheelEvent(self, event):
        # Store current zoom level before zooming
        old_zoom = self.transform().m11()
        print(f"wheelEvent triggered, old zoom: {old_zoom:.2f}")

        # Get center point before zooming
        center_point = self.mapToScene(self.viewport().rect().center())

        # super().wheelEvent(event)

        # Perform standard zoom
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self.scale(zoom_factor, zoom_factor)

        # Get new zoom level
        new_zoom = self.transform().m11()

        # Always update LOD when zoom level changes significantly
        if abs(new_zoom - old_zoom) > 0.05:
            self.update_lod()

        # Re-center on the same point
        self.centerOn(center_point)

    def update_lod(self):
        # Remember viewport center
        center_point = self.mapToScene(self.viewport().rect().center())

        print(f"lod update triggered, current zoom: {self.transform().m11():.2f}")
        # Clear existing ways
        items_to_remove = [item for item in self.scene.items()
                           if isinstance(item, QGraphicsLineItem)]
        for item in items_to_remove:
            self.scene.removeItem(item)

        # Redraw all ways with current zoom level
        for way_data in self.handler.ways:
            self.draw_way(way_data)

        # Re-center view
        self.centerOn(center_point)

        # Force UI update
        QApplication.processEvents()

    def draw_way(self, way_data):
        """Draw a single way on the map - used for incremental updates"""
        way_nodes = way_data['nodes']
        if len(way_nodes) <= 1:
            return
            # Get current zoom level
        # zoom_factor = self.transform().m11()
        #
        # # Multi-level LOD filtering
        # if zoom_factor < 1.0:
        #     # Very zoomed out - show only major roads
        #     # if way_data.get('highway') not in ['motorway', 'trunk', 'primary']:
        #     return
        # elif zoom_factor < 2.0:
        #     # Somewhat zoomed out - show medium roads too
        #     if way_data.get('highway') in ['residential', 'service', 'footway', 'path', 'track']:
        #         return
        # elif zoom_factor < 4.0:
        #     # Medium zoom - show everything except tiny paths
        #     if way_data.get('highway') in ['footway', 'path']:
        #         return
        #
        # # Progressive geometry simplification
        # if zoom_factor < 1.0 and len(way_nodes) > 5:
        #     step = max(1, int(10.0 / zoom_factor))
        #     way_nodes = way_nodes[::step]
        # elif zoom_factor < 3.0 and len(way_nodes) > 10:
        #     step = max(1, int(5.0 / zoom_factor))
        #     way_nodes = way_nodes[::step]

        pen = QPen(Qt.GlobalColor.darkGray)
        pen.setCosmetic(True)
        pen.setWidth(1)

        # Apply styling based on way properties
        if way_data.get('lanes') and int(way_data.get('lanes')) >= 2:
            pen.setWidth(4)
        if way_data.get('surface') == 'asphalt':
            pen.setColor(Qt.GlobalColor.gray)
        if way_data.get('highway') == 'cycleway' or way_data.get('bicycle') == 'designated':
            pen.setColor(Qt.GlobalColor.darkBlue)
        if way_data.get('waterway') == 'river':
            pen.setCosmetic(False)
            pen.setWidth(10)
            pen.setColor(Qt.GlobalColor.cyan)
        if way_data.get('building'):
            pen.setColor(Qt.GlobalColor.darkRed)

        # Draw the way segments
        for i in range(len(way_nodes) - 1):
            lat1, lon1 = normalize_coordinates(way_nodes[i].get('lat'), way_nodes[i].get('lon'),
                                               read_bbox_from_config(self.config))
            lat2, lon2 = normalize_coordinates(way_nodes[i + 1].get('lat'), way_nodes[i + 1].get('lon'),
                                               read_bbox_from_config(self.config))
            line = QGraphicsLineItem(lon1 * 1000, -lat1 * 1000, lon2 * 1000, -lat2 * 1000)
            line.setPen(pen)
            self.scene.addItem(line)

    def setup_tile_loader(self):
        self.tile_loader = ParallelTileLoader(self.handler, self.tiles_dir)
        # Connect with Qt.QueuedConnection to ensure UI updates happen on main thread
        self.tile_loader.tile_loaded.connect(self.update_tile_on_map, Qt.ConnectionType.QueuedConnection)
        self.tile_loader.all_finished.connect(self.finalize_map_update, Qt.ConnectionType.QueuedConnection)

    def update_tile_on_map(self, tile_name):
        # Schedule a repaint rather than painting directly
        self.update()

    def finalize_map_update(self):
        # Final map update after all tiles are loaded
        self.update()
