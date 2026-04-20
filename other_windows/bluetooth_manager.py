import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import subprocess
import time
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QMessageBox, QListWidgetItem, QCheckBox, QFrame
)
from PyQt6.QtBluetooth import QBluetoothDeviceDiscoveryAgent
import functions.lpak as lpak
import configparser

language = None

def test_mode_enable():    
    return os.path.isfile("test.txt")

class BluetoothScanner(QWidget):
    def __init__(self):
        super().__init__()
        self.init_bluetooth()

        self.setWindowTitle(lpak.get("Bluetooth settings", language))
        self.resize(500, 700)

        self.paired_macs = set()

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        up_bar_layout = QHBoxLayout()
        status_label = QLabel(lpak.get("Bluetooth settings", language))
        status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        close_button = QPushButton("❌")

        close_button.clicked.connect(self.close)

        up_bar_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignLeft)
        up_bar_layout.addWidget(status_label)
        up_bar_layout.addStretch()

        layout.addLayout(up_bar_layout)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)


        self.chk_unnamed = QCheckBox(lpak.get("Show unknow devices", language))
        self.chk_unnamed.setChecked(False) 
        self.chk_unnamed.stateChanged.connect(self.apply_filters)
        layout.addWidget(self.chk_unnamed)

        self.lbl_paired = QLabel(f"<h3 style='margin-bottom:0;'>📱 {lpak.get('Paired devices', language)}</h3>")
        layout.addWidget(self.lbl_paired)
        
        self.list_paired = QListWidget()
        self.list_paired.setStyleSheet("QListWidget { font-size: 14px; }")
        layout.addWidget(self.list_paired)

        btn_layout_paired = QHBoxLayout()
        self.btn_connect = QPushButton(lpak.get("Connect", language))
        self.btn_disconnect = QPushButton(lpak.get("Disconnect", language))
        self.btn_remove = QPushButton(lpak.get("Forget", language))
        
        self.btn_connect.clicked.connect(self.connect_device_ui)
        self.btn_disconnect.clicked.connect(self.disconnect_device)
        self.btn_remove.clicked.connect(self.remove_device)
        
        btn_layout_paired.addWidget(self.btn_connect)
        btn_layout_paired.addWidget(self.btn_disconnect)
        btn_layout_paired.addWidget(self.btn_remove)
        layout.addLayout(btn_layout_paired)

        self.lbl_new = QLabel(f"<h3 style='margin-bottom:0;'>🔍 {lpak.get('New devices', language)}</h3>")
        layout.addWidget(self.lbl_new)
        
        self.list_new = QListWidget()
        self.list_new.setStyleSheet("QListWidget { font-size: 14px; }")
        layout.addWidget(self.list_new)

        btn_layout_new = QHBoxLayout()
        self.btn_scan = QPushButton(lpak.get("Start scan", language))
        self.btn_pair = QPushButton(lpak.get("Pair", language))
        
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_pair.clicked.connect(self.pair_device)
        
        btn_layout_new.addWidget(self.btn_scan)
        btn_layout_new.addWidget(self.btn_pair)
        layout.addLayout(btn_layout_new)

        self.setLayout(layout)

        self.agent = QBluetoothDeviceDiscoveryAgent()
        self.agent.deviceDiscovered.connect(self.device_found)
        self.agent.finished.connect(self.scan_finished)

        self.load_paired_devices()

    def init_bluetooth(self):
        commands = [
            ["bluetoothctl", "power", "on"],
            ["bluetoothctl", "agent", "on"],
            ["bluetoothctl", "default-agent"],
            ["bluetoothctl", "discoverable", "on"],
            ["bluetoothctl", "pairable", "on"]
        ]
        for cmd in commands:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)

    def is_device_unnamed(self, name, mac):
        if not name or name == "Unknow":
            return True
        if name.replace("-", ":").upper() == mac:
            return True
        return False

    def apply_filters(self, state=None): 
        show_unnamed = self.chk_unnamed.isChecked()
        
        for list_widget in [self.list_paired, self.list_new]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                is_unnamed = item.data(257)
                if is_unnamed:
                    item.setHidden(not show_unnamed)

    def load_paired_devices(self):
        self.list_paired.clear()
        self.paired_macs.clear()
        
        devices = self.get_paired_devices_list()
        
        for dev in devices:
            self.paired_macs.add(dev['mac'])
            status_str = f"🟢 {lpak.get('Connected', language)}" if dev['connected'] else f"🔴 {lpak.get('Disconnected', language)}"
            is_unnamed = self.is_device_unnamed(dev['name'], dev['mac'])
            
            item = QListWidgetItem(f"📱 {dev['name']}\n      {dev['mac']}  |  {status_str}")
            item.setData(Qt.ItemDataRole.UserRole, dev['mac'])
            item.setData(257, is_unnamed)
            
            if is_unnamed and not self.chk_unnamed.isChecked():
                item.setHidden(True)
                
            self.list_paired.addItem(item)
                        
        for i in reversed(range(self.list_new.count())):
            item = self.list_new.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in self.paired_macs:
                self.list_new.takeItem(i)

    def start_scan(self):
        self.list_new.clear()
        self.lbl_new.setText("<h3 style='margin-bottom:0;'>⏳ Scansione in corso...</h3>")
        self.agent.start()

    def device_found(self, device):
        name = device.name() or "Unknow"
        mac = device.address().toString().strip().upper()

        if mac in self.paired_macs:
            return

        for i in range(self.list_new.count()):
            if self.list_new.item(i).data(Qt.ItemDataRole.UserRole) == mac:
                return

        is_unnamed = self.is_device_unnamed(name, mac)

        item = QListWidgetItem(f"🔍 {name}\n      {mac}")
        item.setData(Qt.ItemDataRole.UserRole, mac)
        item.setData(257, is_unnamed)
        
        if is_unnamed and not self.chk_unnamed.isChecked():
            item.setHidden(True)

        self.list_new.addItem(item)

    def scan_finished(self):
        self.lbl_new.setText(f"<h3 style='margin-bottom:0;'>🔍 {lpak.get('New devices', language)}</h3>")

    
    def get_selected_mac(self, list_widget):
        selected = list_widget.currentItem()
        if not selected:
            QMessageBox.warning(self, lpak.get("Attenction", language), lpak.get("Select a device from the list.", language))
            return None
        return selected.data(Qt.ItemDataRole.UserRole)

    def pair_device(self):
        mac = self.get_selected_mac(self.list_new)
        if mac:
            self.lbl_new.setText(f"<h3 style='margin-bottom:0;'>⏳ {lpak.get('Pairing', language)}...</h3>")
            QApplication.processEvents()

            subprocess.run(["bluetoothctl", "pair", mac], capture_output=True)
            time.sleep(2) 

            info = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
            
            if "Paired: yes" in info:
                QMessageBox.information(self, lpak.get("Succes", language), lpak.get("Device paired succesfully!", language))
                self.load_paired_devices()
            else:
                QMessageBox.warning(self, lpak.get("Error", language), lpak.get("Error during connection, verify if the device has bluetooth on and it is nearby.", language))
            
            self.lbl_new.setText(f"<h3 style='margin-bottom:0;'>🔍 {lpak.get('New devices', language)}</h3>")

    def connect_device_ui(self):
        mac = self.get_selected_mac(self.list_paired)
        if mac:
            self.lbl_paired.setText(f"<h3 style='margin-bottom:0;'>⏳ {lpak.get('Connecting', language)}...</h3>")
            QApplication.processEvents()

            success = self.connect_device_by_mac(mac)

            if success:
                self.load_paired_devices()
                QMessageBox.information(self, lpak.get("Connected", language), lpak.get("Successfully connected", language))
            else:
                QMessageBox.warning(self, lpak.get("Error", language), lpak.get("Error during connection, verify if the device has bluetooth on and it is nearby.", language))

            self.lbl_paired.setText(f"<h3 style='margin-bottom:0;'>📱 {lpak.get('Paired devices', language)}</h3>")

    def disconnect_device(self):
        mac = self.get_selected_mac(self.list_paired)
        if mac:
            self.lbl_paired.setText(f"<h3 style='margin-bottom:0;'>⏳ {lpak.get('Disconnecting', language)}...</h3>")
            QApplication.processEvents()

            subprocess.run(["bluetoothctl", "disconnect", mac], capture_output=True)
            time.sleep(1)
            self.load_paired_devices()
            QMessageBox.information(self, lpak.get("Disconnected", language), lpak.get("Successfully disconnected", language))
            self.lbl_paired.setText(f"<h3 style='margin-bottom:0;'>📱 {lpak.get('Paired devices', language)}</h3>")

    def remove_device(self):
        mac = self.get_selected_mac(self.list_paired)
        if mac:
            subprocess.run(["bluetoothctl", "remove", mac], capture_output=True)
            time.sleep(1)
            self.load_paired_devices()
            self.start_scan()

    def get_paired_devices_list(self) -> list:
        """
        It returns
        [{'name': 'Mouse', 'mac': '00:11:...', 'connected': True}, ...]
        """
        devices = []
        result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
        
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Device"):
                parts = line.split(" ", 2)
                if len(parts) >= 2:
                    mac = parts[1].strip().upper()
                    name = parts[2].strip() if len(parts) > 2 else "Sconosciuto"
                    
                    info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
                    
                    if "Paired: yes" in info_text:
                        is_connected = "Connected: yes" in info_text
                        devices.append({
                            "name": name,
                            "mac": mac,
                            "connected": is_connected
                        })
        return devices

    def connect_device_by_mac(self, mac: str) -> bool:
        """
        Try to connect from external functions
        Return: True if success or False.
        """
        subprocess.run(["bluetoothctl", "connect", mac], capture_output=True)
        time.sleep(1.5) 
        info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
        return "Connected: yes" in info_text

    def disconnect_device_by_mac(self, mac: str) -> bool:
        """
        Try to disconnect from external functions
        Return: True if success (disconnected) or False.
        """
        subprocess.run(["bluetoothctl", "disconnect", mac], capture_output=True)
        time.sleep(1.5) 
        info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
        return "Connected: yes" not in info_text


bt_window_instance = None 

def open_bluetooth_window():
    global language, bt_window_instance
    data_path = ""
    config = configparser.ConfigParser()
    config.optionxform = str
    try:
        config.read(f"{data_path}config.conf")
        language = config.get("User data", "Language")
    except:
        language = "English"

    app = QApplication.instance()
    is_standalone = False
    
    if app is None:
        app = QApplication(sys.argv)
        is_standalone = True

    bt_window_instance = BluetoothScanner()
    bt_window_instance.setWindowFlags(Qt.WindowType.Window) 


    if test_mode_enable():
        bt_window_instance.showMaximized()
    else:
        bt_window_instance.showFullScreen()

    if is_standalone:
        sys.exit(app.exec())

if __name__ == "__main__":
    open_bluetooth_window()