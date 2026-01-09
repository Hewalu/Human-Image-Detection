import serial
import time
import sys

class ESPController:
    def __init__(self, port="COM3", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        
    def connect(self):
        """Verbindet mit dem ESP32 über Serial."""
        try:
            # Timeout wichtig, damit read nicht ewig blockiert, falls nötig
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            # Kurz warten bis Verbindung stabil
            time.sleep(2)
            self.connected = True
            print(f"[ESP] Verbunden an {self.port}")
        except serial.SerialException as e:
            print(f"[ESP] Konnte keine Verbindung zu {self.port} herstellen: {e}")
            self.connected = False
            
    def send_command(self, command):
        """Sendet einen Befehl an den ESP32."""
        if not self.connected or not self.ser:
            return
            
        try:
            msg = f"{command}\n"
            self.ser.write(msg.encode('utf-8'))
        except Exception as e:
            print(f"[ESP] Sende-Fehler: {e}")
            self.connected = False
            
    def update_leds(self, main_red, main_green, car_red, car_yellow, car_green):
        """Sendet den Status aller 5 LEDs an den ESP."""
        # Konvertiere bool in int (0/1)
        vals = [int(main_red), int(main_green), int(car_red), int(car_yellow), int(car_green)]
        cmd = f"L {' '.join(map(str, vals))}"
        self.send_command(cmd)

    def set_red(self):
        # Legacy support, falls noch benötigt (setzt nur Hauptampel, Rest aus/default)
        # Wir nehmen an: Main Rot -> Car Grün (vereinfacht)
        self.update_leds(1, 0, 0, 0, 1)
        
    def set_green(self):
        # Legacy: Main Grün -> Car Rot
        self.update_leds(0, 1, 1, 0, 0)
        
    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False

# Für einfachen Test wenn man diese Datei direkt ausführt
if __name__ == "__main__":
    port = input("COM Port eingeben (z.B. COM3): ").strip()
    if not port: port = "COM3"
    
    esp = ESPController(port)
    esp.connect()
    
    print("Drücke 'r' für Rot, 'g' für Grün, 'q' zum Beenden")
    while True:
        val = input().lower()
        if val == 'r': esp.set_red()
        elif val == 'g': esp.set_green()
        elif val == 'q': break
    
    esp.close()
