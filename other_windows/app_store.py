# app_store.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt

store_window = None  # riferimento globale per mantenerla viva

def open_store_page():
    global store_window
    if store_window is not None:
        store_window.show()  # se già aperta, solo la mostriamo
        store_window.raise_()
        return store_window

    store_window = QMainWindow()
    store_window.setWindowTitle("OpenHomeHUB - Store")

    central_widget = QWidget()
    store_window.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)

    # Up bar
    up_bar_layout = QHBoxLayout()
    microphone_icon = QPushButton("🎤")
    status_label = QLabel("Benvenuto nello Store!")
    settings_button = QPushButton("⚙️")

    up_bar_layout.addWidget(microphone_icon, alignment=Qt.AlignmentFlag.AlignLeft)
    up_bar_layout.addWidget(status_label)
    up_bar_layout.addWidget(settings_button, alignment=Qt.AlignmentFlag.AlignRight)
    up_bar_layout.addStretch()

    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addLayout(up_bar_layout)

    # Contenuto centrale
    label_time = QLabel("Qui ci sarà il contenuto dello store")
    label_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(label_time)

    store_window.showMaximized()
    return store_window