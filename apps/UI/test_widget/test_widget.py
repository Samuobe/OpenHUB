from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class TestWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Usa lo stesso stile dei tuoi widget in app.py
        self.setStyleSheet("""
            QWidget {
                background-color: #e6ffe6;
                color: black;
                border-radius: 15px;
            }
        """)
        
        # Crea il layout e gli elementi del widget
        layout = QVBoxLayout(self)
        
        titolo = QLabel("🌤️ Meteo")
        titolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        temperatura = QLabel("22°C - Soleggiato")
        temperatura.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(titolo)
        layout.addWidget(temperatura)
        
    def on_enable(self):
        # Qui il creatore può far partire timer o richieste API per aggiornare il meteo
        print("Widget Meteo Avviato!")
        
    def get_widget(self):
        # Ritorna l'oggetto QWidget pronto da mostrare
        return self