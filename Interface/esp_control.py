import serial
import time
import sys


class ESPController:
    def __init__(self, port="COM3", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        self.sensor_values = [0] * 8  # Status der 8 Sensoren

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

    def read_sensor_data(self):
        """Liest Daten vom ESP, falls verfügbar. Gibt die Anzahl Personen zurück oder None."""
        if not self.connected or not self.ser:
            return None

        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()

                # Format: S <s1> ... <s8>
                if line.startswith("S"):
                    parts = line.split()
                    if len(parts) >= 9:
                        vals = [int(p) for p in parts[1:9]]
                        self.sensor_values = vals
                        # Nur die ersten 6 Sensoren (Ampeln) zählen zur Personenanzahl
                        # Die letzten 2 (Bahnhof) werden ignoriert für den Count
                        return sum(vals[:6])

                # Fallback Format: P <count>
                if line.startswith("P"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1])
        except Exception as e:
            # print(f"[ESP] Read Error: {e}")
            pass
        return None

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
    if not port:
        port = "COM3"

    esp = ESPController(port)
    esp.connect()

    print("Drücke 'r' für Rot, 'g' für Grün, 'q' zum Beenden")
    while True:
        val = input().lower()
        if val == 'r':
            esp.set_red()
        elif val == 'g':
            esp.set_green()
        elif val == 'q':
            break

    esp.close()
