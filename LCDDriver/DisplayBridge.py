from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QSize, Qt, QTimer, QPoint
import numpy as np
from PIL import Image
import sys
import os

# Import LCD driver modules
import LCDDriver.LCD_1in44 as LCD
import LCDDriver.config as config


class DisplayBridge:
    def __init__(self, window, refresh_rate_ms=100):
        """Bridge between PySide6 GUI and LCD display"""
        self.window = window
        self.width = 128
        self.height = 128

        # For zooming/focusing on specific elements
        self.zoom_factor = 1.0  # Increase this to zoom in more
        self.focus_x = 0  # Center X position to focus on
        self.focus_y = 0 # Center Y position to focus on (adjusted to find buttons)
        self.focus_mode = False # Enable focus mode

        # Initialize the LCD
        self.lcd = LCD.LCD()
        self.lcd.LCD_Init(LCD.SCAN_DIR_DFT)

        # Create a refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(refresh_rate_ms)

        print("LCD Display Bridge initialized")
        

    def update_display(self):
        """Capture the GUI content and send to LCD"""
        # Get the actual window size
        window_size = self.window.size()

        if self.focus_mode:
            # Create QImage for full window first
            capture_image = QImage(QSize(self.width, self.height), QImage.Format.Format_RGB32)
            capture_image.fill(Qt.GlobalColor.white)

            # Paint the window content onto the image
            painter = QPainter(capture_image)

            # Get the scene if we're using QGraphicsView
            if hasattr(self.window, 'osm_viewer') and hasattr(self.window.osm_viewer, 'scene'):
                scene = self.window.osm_viewer.scene
                scene_rect = scene.sceneRect()

                # Scale to fit the capture image
                painter.scale(self.width / scene_rect.width(), self.height / scene_rect.height())
                scene.render(painter)
            else:
                # Render the full window
                self.window.render(painter)

            painter.end()

            # Calculate the viewport for zooming
            view_width = self.width / self.zoom_factor
            view_height = self.height / self.zoom_factor
            x_offset = self.focus_x - (view_width / 2)
            y_offset = self.focus_y - (view_height / 2)

            # Clamp to prevent going out of bounds
            x_offset = max(0, min(x_offset, self.width - view_width))
            y_offset = max(0, min(y_offset, self.height - view_height))

            # Extract the focused region
            output_image = QImage(QSize(self.width, self.height), QImage.Format.Format_RGB32)
            output_image.fill(Qt.GlobalColor.black)

            output_painter = QPainter(output_image)
            output_painter.drawImage(
                0, 0,
                capture_image,
                int(x_offset), int(y_offset),
                int(view_width), int(view_height)
            )
            output_painter.end()
        else:
            # Create QImage at the window's native size
            image = QImage(window_size, QImage.Format.Format_RGB32)
            image.fill(Qt.GlobalColor.white)

            # Paint the full window content onto the image
            painter = QPainter(image)
            self.window.render(painter, QPoint(0, 0))
            painter.end()

            # Scale the image to fit the LCD display
            output_image = image.scaled(
                self.width, self.height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # Convert to PIL image for LCD
        buffer = output_image.bits().tobytes()
        pil_image = Image.frombytes("RGB", (self.width, self.height), buffer, 'raw', "BGRX", 0, 1)

        # Send to LCD
        self.lcd.LCD_ShowImage(pil_image, 0, 0)

    def set_focus(self, x, y, zoom=2.0):
        """Change focus point and zoom level"""
        self.focus_x = x
        self.focus_y = y
        self.zoom_factor = zoom

    def toggle_focus_mode(self):
        """Toggle between focused and full view"""
        self.focus_mode = not self.focus_mode

    def clear(self):
        """Clear the display"""
        self.lcd.LCD_Clear()