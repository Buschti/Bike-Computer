from PySide6.QtCore import QObject, QTimer

from GUI.RouteButton import RouteButton


class ButtonManager(QObject):
    def __init__(self, window, lcd):
        """Handler for physical buttons on the LCD display"""
        super().__init__()
        self.window = window
        self.lcd = lcd

        # Create polling timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_buttons)
        self.timer.start(100)  # Poll every 100ms

        print("Button Manager initialized")

    def poll_buttons(self):
        """Check all button states and trigger actions on press"""
        if self.lcd.digital_read(self.lcd.GPIO_KEY1_PIN) == 1:
            self.zoom_in()
            print("Upper button pressed!")

        if self.lcd.digital_read(self.lcd.GPIO_KEY2_PIN) == 1:
            # Check if navigation overlay is visible
            if hasattr(self.window.osm_viewer, 'nav_overlay') and self.window.osm_viewer.nav_overlay.isVisible():
                # Start navigation if overlay is visible
                self.window.route_button.start_navigation()
                print("Navigation started via middle button")
            else:
                # Calculate route if overlay is not visible
                print("Middle button pressed - calculating route")
                self.trigger_route_button()

        if self.lcd.digital_read(self.lcd.GPIO_KEY3_PIN) == 1:
            self.zoom_out()
            print("Lower button pressed!")

        # Handle D-pad differently in navigation mode
        if hasattr(self.window.osm_viewer, 'navigation_active') and self.window.osm_viewer.navigation_active:
            # D-pad controls navigation marker
            if self.lcd.digital_read(self.lcd.GPIO_KEY_RIGHT_PIN) == 1:
                self.window.route_button.move_navigation_marker('right')
            if self.lcd.digital_read(self.lcd.GPIO_KEY_LEFT_PIN) == 1:
                self.window.route_button.move_navigation_marker('left')
            if self.lcd.digital_read(self.lcd.GPIO_KEY_UP_PIN) == 1:
                self.window.route_button.move_navigation_marker('up')
            if self.lcd.digital_read(self.lcd.GPIO_KEY_DOWN_PIN) == 1:
                self.window.route_button.move_navigation_marker('down')
        else:
            # Normal map navigation with D-pad
            if self.lcd.digital_read(self.lcd.GPIO_KEY_RIGHT_PIN) == 1:
                self.move_map_right()
            if self.lcd.digital_read(self.lcd.GPIO_KEY_LEFT_PIN) == 1:
                self.move_map_left()
            if self.lcd.digital_read(self.lcd.GPIO_KEY_UP_PIN) == 1:
                self.move_map_up()
            if self.lcd.digital_read(self.lcd.GPIO_KEY_DOWN_PIN) == 1:
                self.move_map_down()

        if self.lcd.digital_read(self.lcd.GPIO_KEY_PRESS_PIN) == 1:
            if hasattr(self.window.osm_viewer, 'nav_overlay') and self.window.osm_viewer.nav_overlay.isVisible():
                # Cancel navigation if overlay is visible
                self.window.route_button.cancel_navigation()
                print("Navigation cancelled via lower button")
            else:
                # Normal zoom out functionality
                self.load_tiles()
                print("Tiles loaded")

    def trigger_route_button(self):
        """Trigger the route button in the main GUI"""
        self.window.route_button.route_button.click()
        print("Route button clicked via physical middle button")

    def move_map_right(self):
        """Move the map view to the right"""
        # Define scroll step (pixels)
        scroll_step = 50

        # Get the horizontal scrollbar and scroll right
        h_scrollbar = self.window.osm_viewer.horizontalScrollBar()
        current_value = h_scrollbar.value()
        h_scrollbar.setValue(current_value + scroll_step)

    def move_map_left(self):
        """Move the map view to the left"""
        # Define scroll step (pixels)
        scroll_step = 50

        # Get the horizontal scrollbar and scroll left
        h_scrollbar = self.window.osm_viewer.horizontalScrollBar()
        current_value = h_scrollbar.value()
        h_scrollbar.setValue(current_value - scroll_step)

    def move_map_up(self):
        """Move the map view upward"""
        # Define scroll step (pixels)
        scroll_step = 50

        # Get the vertical scrollbar and scroll up
        v_scrollbar = self.window.osm_viewer.verticalScrollBar()
        current_value = v_scrollbar.value()
        v_scrollbar.setValue(current_value - scroll_step)

    def move_map_down(self):
        """Move the map view downward"""
        # Define scroll step (pixels)
        scroll_step = 50

        # Get the vertical scrollbar and scroll down
        v_scrollbar = self.window.osm_viewer.verticalScrollBar()
        current_value = v_scrollbar.value()
        v_scrollbar.setValue(current_value + scroll_step)

    def zoom_in(self):
        """Zoom in on the map"""
        zoom_factor = 1.25
        self.window.osm_viewer.scale(zoom_factor, zoom_factor)

    def zoom_out(self):
        """Zoom out on the map"""
        zoom_factor = 1 / 1.25
        self.window.osm_viewer.scale(zoom_factor, zoom_factor)

    def load_tiles(self):
        """Manually trigger tile loading for current viewport"""
        if hasattr(self.window, 'osm_viewer'):
            self.window.osm_viewer.manual_load_tiles()
