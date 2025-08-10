from PySide6.QtCore import QThread, Signal, QObject, QMutex
from Util.Config import read_bbox_from_config


import os


class ParallelTileLoader(QObject):
    tile_loaded = Signal(str)  # Signal for each individual tile loaded
    all_finished = Signal()  # Signal when all tiles are done

    def __init__(self, handler, tiles_dir, blacklisted_tiles=None):
        super().__init__()
        self.handler = handler
        self.tiles_dir = tiles_dir
        self.blacklisted_tiles = blacklisted_tiles or []
        self.mutex = QMutex()
        self.threads = []
        self.pending_tiles = 0

    def __del__(self):
        """Destructor to ensure threads are stopped"""
        self.cleanup_threads()

    def cleanup_threads(self):
        """Clean up all worker threads"""
        for thread, worker in self.threads:
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # Wait up to 1 second for thread to finish

        self.threads = []

    def load_tiles(self, min_lat, min_lon, max_lat, max_lon):
        """Find and load all tiles in viewport area in parallel"""
        # Find all tiles that intersect with viewport
        tiles_to_load = []
        tiles = os.listdir(self.tiles_dir)

        for tile in tiles:
            if tile.endswith(".osm.pbf"):
                tile_name = tile.split(".osm.pbf")[0]

                # Skip already loaded or blacklisted tiles
                self.mutex.lock()
                already_loaded = tile_name in self.handler.loaded_pbf_files
                blacklisted = tile_name in self.blacklisted_tiles
                self.mutex.unlock()

                if already_loaded or blacklisted:
                    continue

                # Get tile bounds
                bbox = read_bbox_from_config(f"{self.tiles_dir}/{tile_name}_config.txt")

                # Check if this tile intersects with our area of interest
                if (min_lat <= bbox[3] and max_lat >= bbox[1] and
                        min_lon <= bbox[2] and max_lon >= bbox[0]):
                    tiles_to_load.append(tile_name)

        # Start worker threads for each tile (limit to 4 concurrent threads)
        self.pending_tiles = len(tiles_to_load)
        if self.pending_tiles == 0:
            self.all_finished.emit()
            return

        # Clean up any existing threads first
        self.cleanup_threads()

        # Maximum number of worker threads
        max_workers = min(4, self.pending_tiles)

        # Create a thread pool and start workers
        for i in range(max_workers):
            thread = QThread()
            worker = TileWorker(self.handler, self.tiles_dir, self.mutex)
            worker.moveToThread(thread)
            worker.tile_loaded.connect(self.on_tile_loaded)

            # Fix the lambda to properly call process_tiles
            subset = tiles_to_load[i::max_workers]
            thread.started.connect(lambda w=worker, tiles=subset: w.process_tiles(tiles))

            thread.finished.connect(thread.deleteLater)
            thread.start()
            self.threads.append((thread, worker))

    def on_tile_loaded(self, tile_name):
        """Called when a single tile is loaded"""
        self.mutex.lock()
        self.pending_tiles -= 1
        remaining = self.pending_tiles
        self.mutex.unlock()

        # Signal that this tile is ready, but don't update UI directly
        self.tile_loaded.emit(tile_name)

        # If all tiles are loaded, emit finished signal
        if remaining == 0:
            # Clean up threads
            self.cleanup_threads()
            self.all_finished.emit()


class TileWorker(QObject):
    tile_loaded = Signal(str)

    def __init__(self, handler, tiles_dir, mutex):
        super().__init__()
        self.handler = handler
        self.tiles_dir = tiles_dir
        self.mutex = mutex

    def process_tiles(self, tile_names):
        """Process a batch of tiles"""
        for tile_name in tile_names:
            self._load_tile(tile_name)

    def _load_tile(self, tile_name):
        """Load a single tile and signal completion"""
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

            # Mark ways with their tile name for incremental drawing
            for way in self.handler.ways:
                if '_tile_name' not in way:
                    way['_tile_name'] = tile_name

            print(f"Loaded new tile in thread: {tile_name}")
        except Exception as e:
            print(f"Error loading tile {tile_name}: {e}")
        finally:
            self.mutex.unlock()

        # Signal that this tile is ready
        self.tile_loaded.emit(tile_name)
