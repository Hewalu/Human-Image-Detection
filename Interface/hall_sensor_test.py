import pygame
import sys
import serial.tools.list_ports
from esp_control import ESPController

# Konfiguration
WIDTH, HEIGHT = 600, 400
BACKGROUND_COLOR = (30, 30, 30)
TEXT_COLOR = (255, 255, 255)


def get_auto_port():
    try:
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            # Gängige Chipsätze für ESP32
            if "CP210" in p.description or "CH340" in p.description or "USB Serial" in p.description:
                return p.device
        if ports:
            return ports[0].device
    except Exception:
        pass
    return "COM3"


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hall Sensor Test")

    # Fonts
    font = pygame.font.SysFont("Arial", 40)
    small_font = pygame.font.SysFont("Arial", 24)

    port = get_auto_port()
    print(f"Versuche Verbindung auf {port}...")

    # ESP Verbindung initialisieren
    esp = ESPController(port=port)
    esp.connect()

    person_count = 0
    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Daten vom ESP lesen
        # Wir rufen es hier einmal pro Frame auf. Wenn viele Daten kommen,
        # könnte man es in einer kleinen Schleife `while esp.ser.in_waiting > 0:` machen,
        # aber für manuelle Sensor-Tests reicht das polling meist.
        if esp.connected:
            new_count = esp.read_sensor_data()
            if new_count is not None:
                person_count = new_count
                print(f"Neuer Wert empfangen: {person_count}")

        # Zeichnen
        screen.fill(BACKGROUND_COLOR)

        # Titel
        title_surf = font.render("Hall Sensor Test", True, TEXT_COLOR)
        screen.blit(title_surf, (20, 20))

        # Verbindungsstatus
        if esp.connected:
            status_text = f"Verbunden: {port}"
            status_color = (0, 255, 0)
        else:
            status_text = f"Nicht verbunden ({port})"
            status_color = (255, 50, 50)

        status_surf = small_font.render(status_text, True, status_color)
        screen.blit(status_surf, (20, 70))

        # Anzahl anzeigen
        count_label = small_font.render("Aktuelle Personenanzahl:", True, (200, 200, 200))
        screen.blit(count_label, (WIDTH//2 - count_label.get_width()//2, 110))

        # Kleinerer Font für die Summe
        count_text = str(person_count)
        count_surf = pygame.font.SysFont("Arial", 80, bold=True).render(count_text, True, (100, 200, 255))
        screen.blit(count_surf, (WIDTH//2 - count_surf.get_width()//2, 140))

        # DEBUG: Array anzeigen
        if hasattr(esp, 'sensor_values'):
            debug_text = f"Raw: {esp.sensor_values}"
            debug_surf = small_font.render(debug_text, True, (100, 100, 100))
            screen.blit(debug_surf, (20, HEIGHT - 30))

        # ==========================================
        # DETAIL ANSICHT SENSOREN
        # ==========================================
        # Daten holen (Standard: Nullen)
        vals = esp.sensor_values if hasattr(esp, 'sensor_values') and len(esp.sensor_values) == 8 else [0]*8

        detail_y = 280
        radius = 20
        gap = 60
        start_x_1 = 50
        start_x_2 = 250
        start_x_3 = 450

        # Labels
        lbl_1 = small_font.render("Ampel 1", True, (200, 200, 200))
        screen.blit(lbl_1, (start_x_1, detail_y - 50))

        lbl_2 = small_font.render("Ampel 2", True, (200, 200, 200))
        screen.blit(lbl_2, (start_x_2, detail_y - 50))

        lbl_3 = small_font.render("Bahnhof", True, (200, 200, 200))
        screen.blit(lbl_3, (start_x_3, detail_y - 50))

        # Pins Beschriftung
        pins_1 = ["18", "19", "21"]
        pins_2 = ["16", "17", "5"]
        pins_3 = ["15", "4"]

        # Ampel 1 zeichnen (erste 3 Werte)
        for i in range(3):
            is_active = (vals[i] == 1)
            col = (0, 255, 0) if is_active else (60, 60, 60)

            cx = start_x_1 + i * gap
            pygame.draw.circle(screen, col, (cx, detail_y), radius)
            pygame.draw.circle(screen, (255, 255, 255), (cx, detail_y), radius, 2)

            p_surf = small_font.render(pins_1[i], True, (255, 255, 255))
            screen.blit(p_surf, (cx - p_surf.get_width()//2, detail_y + 25))

        # Ampel 2 zeichnen (nächste 3 Werte)
        for i in range(3):
            is_active = (vals[i+3] == 1)
            col = (0, 255, 0) if is_active else (60, 60, 60)

            cx = start_x_2 + i * gap
            pygame.draw.circle(screen, col, (cx, detail_y), radius)
            pygame.draw.circle(screen, (255, 255, 255), (cx, detail_y), radius, 2)

            p_surf = small_font.render(pins_2[i], True, (255, 255, 255))
            screen.blit(p_surf, (cx - p_surf.get_width()//2, detail_y + 25))

        # Bahnhof zeichnen (letzte 2 Werte)
        for i in range(2):
            is_active = (vals[i+6] == 1)
            col = (0, 255, 0) if is_active else (60, 60, 60)

            cx = start_x_3 + i * gap
            pygame.draw.circle(screen, col, (cx, detail_y), radius)
            pygame.draw.circle(screen, (255, 255, 255), (cx, detail_y), radius, 2)

            p_surf = small_font.render(pins_3[i], True, (255, 255, 255))
            screen.blit(p_surf, (cx - p_surf.get_width()//2, detail_y + 25))

        pygame.display.flip()
        clock.tick(60)

    esp.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
