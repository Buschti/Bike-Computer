from PySide6.QtCore import QRectF, Qt, QObject
from PySide6.QtGui import QPixmap, QPainter


class MapCacheManager:
    """Manages pre-rendered map images for different zoom levels and viewport positions"""

    def __init__(self, osm_viewer):
        self.osm_viewer = osm_viewer
        self.cache = {}  # Dictionary to store rendered map sections
        self.cache_dirty = True  # Flag indicating cache needs refresh
        self.last_viewport = None  # Track last viewport for change detection
        self.max_cache_entries = 10  # Limit cache size to control memory usage
        self.movement_threshold = 0.3  # Viewport movement threshold (30%) for cache refresh

        # Hook into the OSMViewer
        self._install_cache_hooks()

    def _install_cache_hooks(self):
        """Install the necessary hooks to the OSMViewer to enable caching"""
        # Store original paint event
        self.original_paint_event = self.osm_viewer.paintEvent

        # Replace with our cached version
        def cached_paint_event(event):
            self.handle_paint_event(event)

        self.osm_viewer.paintEvent = cached_paint_event

        # Create or patch other necessary methods
        self.original_on_tiles_loaded = getattr(self.osm_viewer, "on_all_tiles_loaded", None)
        self.osm_viewer.on_all_tiles_loaded = self._wrap_tile_loaded_event(self.original_on_tiles_loaded)

    def _wrap_tile_loaded_event(self, original_method):
        """Wrap the tile loaded event to invalidate cache when new data arrives"""
        def wrapped_method():
            # Invalidate cache when new tiles load
            self.cache_dirty = True

            # Call original method if it exists
            if original_method:
                original_method()

        return wrapped_method

    def handle_paint_event(self, event):
        """Handle paint event with caching"""
        # Get current view state
        current_zoom = int(self.osm_viewer.transform().m11() * 10) / 10  # Round to nearest 0.1
        viewport_rect = self.osm_viewer.mapToScene(self.osm_viewer.viewport().rect()).boundingRect()

        # Create cache key based on zoom and viewport center
        center = viewport_rect.center()
        # Round position to reduce sensitivity to small movements
        center_x = round(center.x() / 100) * 100
        center_y = round(center.y() / 100) * 100
        cache_key = f"zoom_{current_zoom}_x{center_x}_y{center_y}"

        # Check if cache needs refresh
        cache_needs_refresh = (
            cache_key not in self.cache or
            self.cache_dirty or
            self.last_viewport is None or
            self._viewport_moved_significantly(viewport_rect)
        )

        if cache_needs_refresh:
            # Create a new pixmap and render the visible map to it
            pixmap = QPixmap(self.osm_viewer.viewport().size())
            pixmap.fill(Qt.GlobalColor.white)

            # Render to the pixmap
            temp_painter = QPainter(pixmap)
            self.osm_viewer.scene.render(temp_painter, QRectF(pixmap.rect()), viewport_rect)
            temp_painter.end()

            # Store in cache and update state
            self.cache[cache_key] = pixmap
            self.last_viewport = viewport_rect
            self.cache_dirty = False

            # Manage cache size
            self._manage_cache_size()

            print(f"Rendered and cached view at zoom {current_zoom}")
        #else:
            # print(f"Using cached view at zoom {current_zoom}")

        # Draw from cache
        painter = QPainter(self.osm_viewer.viewport())
        painter.drawPixmap(0, 0, self.cache[cache_key])
        painter.end()

    def _viewport_moved_significantly(self, new_viewport):
        """Check if viewport has moved enough to warrant a cache refresh"""
        if self.last_viewport is None:
            return True

        # Calculate overlap percentage
        intersection = self.last_viewport.intersected(new_viewport)
        if intersection.isEmpty():
            return True

        overlap_area = intersection.width() * intersection.height()
        viewport_area = new_viewport.width() * new_viewport.height()

        # If overlap is too small, consider it a significant movement
        return (overlap_area / viewport_area) < (1 - self.movement_threshold)

    def _manage_cache_size(self):
        """Remove oldest entries if cache gets too large"""
        if len(self.cache) > self.max_cache_entries:
            # Simple strategy: remove oldest entries
            entries = list(self.cache.keys())
            for old_key in entries[:-self.max_cache_entries]:
                del self.cache[old_key]

    def invalidate_cache(self):
        """Mark the cache as dirty to force refresh"""
        self.cache_dirty = True

    def clear_cache(self):
        """Clear the entire cache"""
        self.cache.clear()
        self.last_viewport = None
        self.cache_dirty = True
