from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QDialog,
                               QLineEdit, QLabel, QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Signal, QObject, QThread, Qt
from PySide6.QtGui import QPen, QPainter, Qt, QFont

from GUI.OSMViewer import TileLoader
from Graphs.Graph import Graph
from Routing.AStar import AStar
from Util.Config import normalize_coordinates, read_bbox_from_config
from Util.Haversine import Haversine
from GUI.NavigationOverlay import NavigationOverlay

import time


class RouteCoordinatesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Route Coordinates")

        self.layout = QFormLayout(self)

        # Start coordinate inputs
        self.start_lat_input = QLineEdit(self)
        self.start_lon_input = QLineEdit(self)

        # Goal coordinate inputs
        self.goal_lat_input = QLineEdit(self)
        self.goal_lon_input = QLineEdit(self)

        # Add fields to form layout
        self.layout.addRow(QLabel("Start Latitude:"), self.start_lat_input)
        self.layout.addRow(QLabel("Start Longitude:"), self.start_lon_input)
        self.layout.addRow(QLabel("Goal Latitude:"), self.goal_lat_input)
        self.layout.addRow(QLabel("Goal Longitude:"), self.goal_lon_input)

        # Set default values for testing (Regensburg area)
        self.start_lat_input.setText("49.0127")
        self.start_lon_input.setText("12.0405")
        self.goal_lat_input.setText("49.0180")
        self.goal_lon_input.setText("12.0462")

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_coordinates(self):
        return {
            "start_lat": float(self.start_lat_input.text()),
            "start_lon": float(self.start_lon_input.text()),
            "goal_lat": float(self.goal_lat_input.text()),
            "goal_lon": float(self.goal_lon_input.text())
        }


class RouteCalculator(QObject):
    # Define signals to communicate results back to the main thread
    finished = Signal()
    route_calculated = Signal(list, float)

    def __init__(self, handler, graph, astar, haversine, start_lat, start_lon, goal_lat, goal_lon):
        super().__init__()
        # Store parameters needed for calculation
        self.handler = handler
        self.graph = graph
        self.astar = astar
        self.haversine = haversine
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.goal_lat = goal_lat
        self.goal_lon = goal_lon

    def run(self):
        """This method runs in a separate thread"""
        try:
            print("Starting route calculation...")
            from Util.Polygon import get_buffer_around_route

            # Create a route-specific tile loader
            tile_loader = TileLoader(self.handler, "tile_config_dynamic")

            # Use get_buffer_around_route instead of fixed buffer
            # The buffer value (0.5) is in kilometers - adjust as needed
            route_buffer = get_buffer_around_route(
                self.start_lat, self.start_lon,
                self.goal_lat, self.goal_lon,
                0.1  # 500m buffer around the direct line
            )

            # Get the bounds from the polygon
            bounds = route_buffer.bounds
            min_lat, min_lon, max_lat, max_lon = bounds

            print(f"Route buffer bounds: {min_lat:.6f}, {min_lon:.6f} to {max_lat:.6f}, {max_lon:.6f}")

            # Load tiles using the optimized buffer
            tile_loader.load_by_viewport(min_lat, min_lon, max_lat, max_lon)
            tile_loader.run()  # Run directly without starting thread

            # Now build the graph with loaded tiles
            self.graph.build(self.handler.ways)
            self.graph.apply_weight('shortest')

            start_node = self.graph.get_nearest_node(self.start_lat, self.start_lon)
            goal_node = self.graph.get_nearest_node(self.goal_lat, self.goal_lon)

            path, cost = self.astar.search(start_node, goal_node)
            path_length = self.haversine.calculate_street_length_haversine(path, self.haversine.haversine)

            # Send results back to main thread
            self.route_calculated.emit(path, path_length)
        finally:
            self.finished.emit()


class RouteButton(QWidget):
    def __init__(self, osm_viewer, handler):
        super().__init__()
        self.path_length = 0
        self.path = []
        self.turn_indicators = []
        self.destination_focus_shown = False
        self.turn_points = []
        self.osm_viewer = osm_viewer
        self.handler = handler
        self.graph = Graph()
        self.astar = AStar(self.graph)
        self.haversine = Haversine()
        self.route_heading = 0

        self.route_button = QPushButton("Calculate Route")
        self.route_button.clicked.connect(self.calculate_and_display_route)

        layout = QVBoxLayout()
        layout.addWidget(self.route_button)
        self.setLayout(layout)

    def show_route_dialog(self):
        dialog = RouteCoordinatesDialog(self)
        if dialog.exec():
            coordinates = dialog.get_coordinates()
            self.calculate_and_display_route(coordinates)

    def calculate_and_display_route(self, coordinates):
        if hasattr(self, 'path') and self.path_length is not 0:
            print(f"Route already calculated.")
            return

        # Disable button while calculating
        self.route_button.setEnabled(False)
        self.route_button.setText("Calculating...")

        # Set default coordinates if none provided
        start_lat = 49.0127394
        start_lon = 12.0405144

        goal_lat = 49.0170210
        goal_lon = 12.0489621

        # Create thread and worker
        self.thread = QThread()
        self.worker = RouteCalculator(
            self.handler, self.graph, self.astar, self.haversine,
            start_lat, start_lon, goal_lat, goal_lon
        )

        # Move worker to thread
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Connect result signal
        self.worker.route_calculated.connect(self.on_route_calculated)

        # Start the thread
        self.thread.start()

    def on_route_calculated(self, path, path_length):
        self.osm_viewer.update_map(path[0].latitude, path[0].longitude)  # Reset map to default view
        # Store the path for later use in navigation
        self.path = path
        self.path_length = path_length

        # Re-enable the button
        self.route_button.setEnabled(True)
        self.route_button.setText("Calculate Route")

        # Detect turn points right after calculating the route
        self.detect_turn_points()

        # Set initial position for arrow display
        self.current_position = {
            'latitude': self.path[0].latitude,
            'longitude': self.path[0].longitude,
            'index': 0
        }

        # Display the calculated route with turn indicators
        self.display_route(path)

        # Show navigation overlay
        if not hasattr(self.osm_viewer, 'nav_overlay'):
            self.osm_viewer.nav_overlay = NavigationOverlay(self.osm_viewer)

        # Show the overlay
        self.osm_viewer.nav_overlay.show()

        print(f"Route calculated: {path_length:.2f} km with {len(path)} nodes")
        print(f"Detected {len(self.turn_points)} turns in route")

    def display_route(self, path):
        # Draw the route on the map
        pen = QPen(Qt.GlobalColor.blue)
        pen.setWidth(10)
        pen.setCosmetic(True)

        for i in range(len(path) - 1):
            lat1, lon1 = normalize_coordinates(path[i].latitude, path[i].longitude,
                                               read_bbox_from_config(self.osm_viewer.config))
            lat2, lon2 = normalize_coordinates(path[i + 1].latitude, path[i + 1].longitude,
                                               read_bbox_from_config(self.osm_viewer.config))

            line = self.osm_viewer.scene.addLine(
                lon1 * 1000, -lat1 * 1000,
                lon2 * 1000, -lat2 * 1000,
                pen
            )

        self.draw_turn_indicators()

    def start_navigation(self):
        print("Starting navigation...")
        self.osm_viewer.navigation_active = True
        self.osm_viewer.nav_overlay.hide()

        # Initialize current position
        self.current_position = {
            'latitude': self.path[0].latitude,
            'longitude': self.path[0].longitude,
            'index': 0
        }

        # Initialize turn indicator overlay
        if not hasattr(self, 'turn_indicator'):
            self.turn_indicator = TurnIndicatorOverlay(self.osm_viewer)

        # Analyze path for turns
        self.detect_turn_points()
        print(f"Detected {len(self.turn_points)} turns in route")

        # Calculate heading and rotate map
        self.calculate_route_heading()
        self.rotate_map_to_heading()

        # Draw marker and route
        self.draw_navigation_marker()
        self.display_route(self.path)
        self.update_turn_indicator()  # Update turn indicator instead of drawing arrows
        self.draw_turn_indicators()

        print("Navigation started - use D-pad to move")

    def cancel_navigation(self):
        print("Navigation cancelled")
        self.osm_viewer.nav_overlay.hide()
        # Clear the route from the map
        center_point = self.osm_viewer.mapToScene(self.osm_viewer.viewport().rect().center())
        center_geo = self.osm_viewer.scene_to_geo(center_point)
        self.osm_viewer.update_map(center_geo[0], center_geo[1])

    def draw_navigation_marker(self):
        # Clear any existing marker
        if hasattr(self, 'position_marker'):
            self.osm_viewer.scene.removeItem(self.position_marker)

        # Draw a new marker at current position
        lat, lon = normalize_coordinates(
            self.current_position['latitude'],
            self.current_position['longitude'],
            read_bbox_from_config(self.osm_viewer.config)
        )

        # Create a larger, more visible marker
        from PySide6.QtWidgets import QGraphicsEllipseItem
        from PySide6.QtGui import QBrush

        self.position_marker = QGraphicsEllipseItem(
            lon * 1000 - 1, -lat * 1000 - 1, 5, 5
        )
        self.position_marker.setBrush(QBrush(Qt.GlobalColor.green))
        self.position_marker.setPen(QPen(Qt.GlobalColor.black, 1))
        self.osm_viewer.scene.addItem(self.position_marker)

        # Center the view on the marker
        self.osm_viewer.centerOn(lon * 1000, -lat * 1000)

    def move_navigation_marker(self, direction):
        """Move the navigation marker based on D-pad input"""
        if not hasattr(self, 'current_position'):
            return

        # Movement step size
        step = 0.0001

        if direction == 'up':
            self.current_position['latitude'] += step
        elif direction == 'down':
            self.current_position['latitude'] -= step
        elif direction == 'left':
            self.current_position['longitude'] -= step
        elif direction == 'right':
            self.current_position['longitude'] += step

        # Update heading and rotate map
        self.calculate_route_heading()
        self.rotate_map_to_heading()

        # Redraw marker
        self.draw_navigation_marker()

        # Check waypoint progress
        self.check_route_progress()

        self.draw_turn_indicators()

        # In move_navigation_marker method, after check_route_progress:
        if not self.check_destination_reached():
            self.check_route_progress()
            self.update_turn_indicator()

    def check_route_progress(self):
        """Check if we're close to the next turn or destination"""
        if not hasattr(self, 'path') or len(self.path) <= 1 or not hasattr(self, 'turn_points'):
            return

        # Check if we're near a turn point
        if self.turn_points:
            next_turn = None
            passed_all_turns = True

            # Find the next turn
            for turn in self.turn_points:
                if turn['index'] > self.current_position['index']:
                    next_turn = turn
                    passed_all_turns = False
                    break

            # Calculate distance to next turn or destination
            target_point = None

            if next_turn:
                # Focus on next turn
                target_point = next_turn['point']
                target_index = next_turn['index']
            else:
                # Focus on destination
                target_point = self.path[-1]
                target_index = len(self.path) - 1

            # Calculate distance to target
            distance = self.haversine.haversine(
                self.current_position['latitude'],
                self.current_position['longitude'],
                target_point.latitude,
                target_point.longitude
            )

            # If close enough to next turn, process it
            if next_turn and distance < 50:  # 50 meters threshold
                print(f"Reached turn point {next_turn['index']} - {next_turn['direction']} turn")

                # Update current position index
                self.current_position['index'] = target_index

                # Show notification about the turn
                self.show_turn_notification(not passed_all_turns)

                # Update heading and rotation
                self.calculate_route_heading()
                self.rotate_map_to_heading()
                self.draw_turn_indicators()

            # If we've passed all turns, focus on destination
            elif passed_all_turns and self.current_position['index'] < len(self.path) - 1:
                # Only show this if we haven't shown it already
                if not hasattr(self, 'destination_focus_shown') or not self.destination_focus_shown:
                    self.show_destination_focus()
                    self.destination_focus_shown = True

                    # Update heading to focus on destination
                    self.calculate_route_heading()
                    self.rotate_map_to_heading()

    def calculate_route_heading(self):
        """Calculate heading toward next turn or destination"""
        import math

        if not hasattr(self, 'path') or len(self.path) < 2:
            return 0

        # Find the next turn point
        next_turn = None
        past_last_turn = True

        if hasattr(self, 'turn_points') and self.turn_points:
            past_last_turn = self.current_position['index'] > self.turn_points[-1]['index']

            if not past_last_turn:
                for turn in self.turn_points:
                    if turn['index'] > self.current_position['index']:
                        next_turn = turn
                        break

        # If no turn ahead or we're past all turns, use final destination
        if next_turn and not past_last_turn:
            target_lat = next_turn['point'].latitude
            target_lon = next_turn['point'].longitude
            print(f"Focusing on next turn: {next_turn['direction']} turn")
        else:
            target_lat = self.path[-1].latitude
            target_lon = self.path[-1].longitude
            print("Focusing on final destination")

        # Calculate heading to target
        start_lat = self.current_position['latitude']
        start_lon = self.current_position['longitude']

        # Convert to radians
        start_lat_rad = math.radians(start_lat)
        start_lon_rad = math.radians(start_lon)
        target_lat_rad = math.radians(target_lat)
        target_lon_rad = math.radians(target_lon)

        # Calculate bearing
        y = math.sin(target_lon_rad - start_lon_rad) * math.cos(target_lat_rad)
        x = math.cos(start_lat_rad) * math.sin(target_lat_rad) - \
            math.sin(start_lat_rad) * math.cos(target_lat_rad) * math.cos(target_lon_rad - start_lon_rad)

        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360

        self.route_heading = bearing
        return bearing

    def rotate_map_to_heading(self):
        """Rotate map so destination is at the top"""
        # Reset any previous transform
        self.osm_viewer.resetTransform()

        # Apply zoom
        self.osm_viewer.scale(8, 8)

        # Get the center of the viewport
        center_x = self.osm_viewer.viewport().width() / 2
        center_y = self.osm_viewer.viewport().height() / 2

        # Calculate rotation to put destination at top
        rotation = 360 - self.route_heading

        # Apply rotation around center
        self.osm_viewer.translate(center_x, center_y)
        self.osm_viewer.rotate(rotation)
        self.osm_viewer.translate(-center_x, -center_y)

    def detect_turn_points(self):
        """Analyze the path to find significant turns"""
        import math

        if not hasattr(self, 'path') or len(self.path) < 3:
            return []

        turn_points = []
        turn_threshold = 45  # Degrees - adjust as needed

        # Analyze each trio of points to detect turns
        for i in range(1, len(self.path) - 1):
            prev_point = self.path[i - 1]
            current_point = self.path[i]
            next_point = self.path[i + 1]

            # Calculate vectors
            vector1 = (
                current_point.latitude - prev_point.latitude,
                current_point.longitude - prev_point.longitude
            )
            vector2 = (
                next_point.latitude - current_point.latitude,
                next_point.longitude - current_point.longitude
            )

            # Calculate headings
            heading1 = math.degrees(math.atan2(vector1[1], vector1[0]))
            heading2 = math.degrees(math.atan2(vector2[1], vector2[0]))

            # Calculate angle difference
            angle_diff = abs((heading2 - heading1 + 180) % 360 - 180)

            # If there's a significant turn, add to turn points
            if angle_diff > turn_threshold:
                turn_points.append({
                    'index': i,
                    'point': current_point,
                    'angle': angle_diff,
                    'direction': 'left' if (heading2 - heading1) % 360 > 180 else 'right'
                })

        self.turn_points = turn_points
        return turn_points

    def clean_up_navigation(self):
        """Clean up all navigation-related elements from the display"""
        # Hide navigation overlay
        if hasattr(self.osm_viewer, 'nav_overlay'):
            self.osm_viewer.nav_overlay.hide()

        # Hide turn indicator if it exists
        if hasattr(self, 'turn_indicator'):
            self.turn_indicator.hide()

        # Remove turn indicators
        if hasattr(self, 'turn_indicators'):
            for indicator in self.turn_indicators:
                self.osm_viewer.scene.removeItem(indicator)
            self.turn_indicators = []

        # Remove position marker
        if hasattr(self, 'position_marker'):
            self.osm_viewer.scene.removeItem(self.position_marker)

    def check_destination_reached(self):
        """Check if we've reached the final destination and stop navigation if so"""
        if not hasattr(self, 'path') or len(self.path) < 1:
            return False

        # Get final destination
        final_point = self.path[-1]

        # Calculate distance to destination
        distance = self.haversine.haversine(
            self.current_position['latitude'],
            self.current_position['longitude'],
            final_point.latitude,
            final_point.longitude
        )

        # Define arrival threshold (in meters)
        arrival_threshold = 50

        # Check if we've reached the destination
        if distance <= arrival_threshold:
            print(f"Destination reached! Distance: {distance:.1f}m")

            # Show arrival notification
            self.show_arrival_notification()

            # Reset navigation state
            self.osm_viewer.navigation_active = False

            # Store the current position
            final_lat = self.current_position['latitude']
            final_lon = self.current_position['longitude']

            # Reset map transformation
            self.osm_viewer.resetTransform()
            self.osm_viewer.scale(5, 5)

            # Clean up navigation elements without reloading the map
            self.clean_up_navigation()

            # Clear just the navigation elements (not the whole map)
            self.osm_viewer.clear_navigation_elements()

            # Center on final position
            lat, lon = normalize_coordinates(
                final_lat, final_lon,
                read_bbox_from_config(self.osm_viewer.config)
            )
            self.osm_viewer.centerOn(lon * 1000, -lat * 1000)

            # Reset button to calculate route again
            try:
                self.route_button.clicked.disconnect()
            except:
                pass
            self.route_button.clicked.connect(self.calculate_and_display_route)
            self.route_button.setText("Calculate Route")

            return True

        return False

    def show_turn_notification(self, has_next_turn):
        """Show a brief notification when crossing a turn"""
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt, QTimer

        # Create notification label
        notification = QLabel(self.osm_viewer)

        if has_next_turn:
            # Find the next turn
            next_turn = None
            for turn in self.turn_points:
                if turn['index'] > self.current_position['index']:
                    next_turn = turn
                    break

            if next_turn:
                # Show info about next turn
                text = f"Next: {next_turn['direction'].capitalize()} turn in {self.estimate_distance_to_turn(next_turn):.0f}m"
            else:
                text = "Continue to destination"
        else:
            text = "Approaching destination"

        # Style and position the notification
        notification.setText(text)
        notification.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        notification.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notification.adjustSize()

        # Position at bottom of screen
        notification.move(
            (self.osm_viewer.width() - notification.width()) // 2,
            self.osm_viewer.height() - notification.height() - 20
        )
        notification.show()

        # Remove after 3 seconds
        QTimer.singleShot(3000, notification.deleteLater)

    def show_destination_focus(self):
        """Show notification when focusing on final destination"""
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt, QTimer

        # Calculate remaining distance
        remaining_distance = 0
        for i in range(self.current_position['index'], len(self.path) - 1):
            remaining_distance += self.haversine.haversine(
                self.path[i].latitude,
                self.path[i].longitude,
                self.path[i + 1].latitude,
                self.path[i + 1].longitude
            )

        # Create notification
        notification = QLabel(self.osm_viewer)
        notification.setText(f"Heading to destination ({remaining_distance:.0f}m)")
        notification.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        """)
        notification.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notification.adjustSize()

        # Position at bottom of screen
        notification.move(
            (self.osm_viewer.width() - notification.width()) // 2,
            self.osm_viewer.height() - notification.height() - 20
        )
        notification.show()

        # Remove after 3 seconds
        QTimer.singleShot(4000, notification.deleteLater)

    def show_arrival_notification(self):
        """Show notification when destination is reached"""
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt, QTimer

        # Create notification
        notification = QLabel(self.osm_viewer)
        notification.setText("You have reached your destination!")
        notification.setStyleSheet("""
            background-color: rgba(0, 100, 0, 220);
            color: white;
            padding: 12px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
        """)
        notification.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notification.adjustSize()

        # Position at center of screen
        notification.move(
            (self.osm_viewer.width() - notification.width()) // 2,
            (self.osm_viewer.height() - notification.height()) // 2
        )
        notification.show()

        # Remove after 5 seconds
        QTimer.singleShot(5000, notification.deleteLater)

    def estimate_distance_to_turn(self, turn):
        """Estimate distance in meters to the next turn"""
        total_distance = 0

        # Sum up distances between waypoints from current position to turn
        for i in range(self.current_position['index'], turn['index']):
            if i + 1 < len(self.path):
                total_distance += self.haversine.haversine(
                    self.path[i].latitude,
                    self.path[i].longitude,
                    self.path[i + 1].latitude,
                    self.path[i + 1].longitude
                )

        return total_distance

    def draw_turn_indicators(self):
        """Draw red arrows at turn points to indicate turn direction"""
        from PySide6.QtWidgets import QGraphicsPolygonItem
        from PySide6.QtGui import QPolygonF, QBrush
        from PySide6.QtCore import QPointF
        import math

        # Clear existing turn indicators
        if hasattr(self, 'turn_indicators'):
            for indicator in self.turn_indicators:
                self.osm_viewer.scene.removeItem(indicator)

        self.turn_indicators = []

        # Only draw if we have turn points
        if not hasattr(self, 'turn_points') or not self.turn_points:
            return

        # Find the next turn
        next_turn = None
        for turn in self.turn_points:
            if turn['index'] > self.current_position['index']:
                next_turn = turn
                break

        if not next_turn:
            return  # No upcoming turns

        # Get turn point coordinates
        turn_point = next_turn['point']
        turn_index = next_turn['index']

        # Get the points before and after the turn to determine path direction
        if turn_index > 0 and turn_index < len(self.path) - 1:
            prev_point = self.path[turn_index - 1]
            next_point = self.path[turn_index + 1]

            # Calculate path direction before turn
            incoming_angle = math.degrees(math.atan2(
                turn_point.longitude - prev_point.longitude,
                turn_point.latitude - prev_point.latitude
            ))

            # Calculate path direction after turn
            outgoing_angle = math.degrees(math.atan2(
                next_point.longitude - turn_point.longitude,
                next_point.latitude - turn_point.latitude
            ))

            # Normalize angles
            incoming_angle = (incoming_angle + 360) % 360
            outgoing_angle = (outgoing_angle + 360) % 360

            # Calculate arrow direction (along the path)
            path_angle = (incoming_angle + outgoing_angle) / 2

            # Adjust arrow direction based on turn direction
            if next_turn['direction'] == 'left':
                arrow_angle = (incoming_angle - 90) % 360  # Offset to point left of path
            else:  # right turn
                arrow_angle = (incoming_angle + 90) % 360  # Offset to point right of path

            # Convert turn point to scene coordinates
            lat, lon = normalize_coordinates(
                turn_point.latitude,
                turn_point.longitude,
                read_bbox_from_config(self.osm_viewer.config)
            )
            x = lon * 1000
            y = -lat * 1000

            # Create arrow shape
            arrow_size = 4  # Increased size for visibility
            arrow_polygon = QPolygonF()

            # Create arrow shape (triangle) pointing in the right direction
            angle_rad = math.radians(arrow_angle)
            arrow_polygon.append(QPointF(x, y))  # Tip of arrow
            arrow_polygon.append(QPointF(
                x - arrow_size * math.cos(angle_rad - math.pi / 6),
                y - arrow_size * math.sin(angle_rad - math.pi / 6)
            ))
            arrow_polygon.append(QPointF(
                x - arrow_size * math.cos(angle_rad + math.pi / 6),
                y - arrow_size * math.sin(angle_rad + math.pi / 6)
            ))

            # Create arrow item
            arrow_item = QGraphicsPolygonItem(arrow_polygon)
            arrow_item.setBrush(QBrush(Qt.GlobalColor.red))
            arrow_item.setPen(Qt.PenStyle.NoPen)

            # Add to scene and store reference
            self.osm_viewer.scene.addItem(arrow_item)
            self.turn_indicators.append(arrow_item)

    def update_turn_indicator(self):
        """Update the turn indicator with information about the next turn"""
        if not hasattr(self, 'path') or len(self.path) < 3 or not hasattr(self, 'turn_points'):
            return

        # Find the next turn
        next_turn = None
        for turn in self.turn_points:
            if turn['index'] > self.current_position['index']:
                next_turn = turn
                break

        if next_turn:
            # Calculate distance to the turn
            distance = self.haversine.haversine(
                self.current_position['latitude'],
                self.current_position['longitude'],
                next_turn['point'].latitude,
                next_turn['point'].longitude
            )

            # Update the turn indicator
            self.turn_indicator.update_info(distance, next_turn['direction'])
        else:
            # No more turns, show distance to destination
            final_point = self.path[-1]
            distance = self.haversine.haversine(
                self.current_position['latitude'],
                self.current_position['longitude'],
                final_point.latitude,
                final_point.longitude
            )

            self.turn_indicator.update_info(distance, "destination")


class TurnIndicatorOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set position and size
        self.setGeometry(10, 10, 120, 60)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180); border-radius: 5px;")

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Create labels
        self.distance_label = QLabel("-- m")
        self.distance_label.setStyleSheet("color: white; font-weight: bold;")

        self.direction_label = QLabel("Straight")
        self.direction_label.setStyleSheet("color: white;")

        # Add to layout
        layout.addWidget(self.distance_label)
        layout.addWidget(self.direction_label)

        # Hide initially
        self.hide()

    def update_info(self, distance, direction):
        """Update the displayed turn information"""
        self.distance_label.setText(f"{int(distance)} m")
        self.direction_label.setText(f"Turn {direction}")
        self.show()
