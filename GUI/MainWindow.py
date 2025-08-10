import sys

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QMainWindow, QPushButton, QWidget, \
    QApplication

from GUI.OSMViewer import OSMViewer
from GUI.RouteButton import RouteButton
from Map.MapCache import MapCacheManager


class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Coordinates")

        self.layout = QVBoxLayout(self)

        self.latitude_input = QLineEdit(self)
        self.latitude_input.setPlaceholderText("Enter Latitude")
        self.layout.addWidget(self.latitude_input)

        self.longitude_input = QLineEdit(self)
        self.longitude_input.setPlaceholderText("Enter Longitude")
        self.layout.addWidget(self.longitude_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                                           self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_coordinates(self):
        return self.latitude_input.text(), self.longitude_input.text()


class MainWindow(QMainWindow):
    def __init__(self, handler):
        super().__init__()

        self.setWindowTitle("OSM Viewer")
        self.setGeometry(100, 100, 400, 400)

        self.osm_viewer = OSMViewer("tile_config_dynamic/regensburg_config.txt", handler)
        # self.cacheManager = MapCacheManager(self.osm_viewer)


        self.route_button = RouteButton(self.osm_viewer, handler)

        self.button = QPushButton("Enter Coordinates", self)
        self.button.clicked.connect(self.show_coordinate_dialog)

        layout = QVBoxLayout()
        # layout.addWidget(self.button)
        layout.addWidget(self.osm_viewer)
        # layout.addWidget(self.route_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)



    def show_coordinate_dialog(self):
        dialog = CustomDialog(self)
        if dialog.exec():
            lat, lon = dialog.get_coordinates()
            self.osm_viewer.update_map(float(lat), float(lon))


