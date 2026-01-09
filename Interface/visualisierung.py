import pygame
import pygame.freetype
from pygame import gfxdraw
import math
import sys
import os
import serial.tools.list_ports

try:
    from esp_control import ESPController
except ImportError:
    # Falls das hier als Modul geladen wird oder der Pfad anders ist
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from esp_control import ESPController

try:
    from traffic_logic import TrafficLightLogic
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from traffic_logic import TrafficLightLogic

# ==========================================
#      KONFIGURATION
# ==========================================


def get_auto_port():
    try:
        ports = list(serial.tools.list_ports.comports())
        # Suche nach typischen ESP/Arduino Treibern
        for p in ports:
            if "CP210" in p.description or "CH340" in p.description or "USB Serial" in p.description:
                print(f"[Auto-Detect] ESP gefunden: {p.device} ({p.description})")
                return p.device

        # Fallback: Nimm den ersten verfügbaren Port
        if ports:
            print(f"[Auto-Detect] Standard-Port gewählt: {ports[0].device}")
            return ports[0].device

    except Exception as e:
        print(f"[Auto-Detect] Fehler bei Port-Suche: {e}")

    print("[Auto-Detect] Kein Port gefunden, nutze Fallback COM3")
    return "COM3"


ESP_PORT = get_auto_port()
SCALE_FACTOR = 0.3

# 1. PERSONEN LOGIK
MAX_PERSON_CAP = 15
MAX_VISUAL_PERSONS = 8
BONUS_TIME_PER_PERSON_MS = 600  # Bonuszeit pro Person für Grünphase

# 2. LED VISUALISIERUNG
VISUAL_LED_COUNT = 20    # Feste Anzahl an Punkten
BONUS_LEDS_COUNT = 3     # Visuelle Überlauf-Punkte

# 3. BASIS ZEITEN (Millisekunden)
# Diese steuern wie lange der Ring braucht um voll zu werden
DURATION_RED_BASE_MS = 20000   # Basisdauer Rot
DURATION_GREEN_BASE_MS = 12000  # Basisdauer Grün

# 5. OPTIK
TIMER_FONT_SIZE = 280
ORIGINAL_LED_RADIUS = 235
ORIGINAL_DOT_SIZE = 20
WAITING_ICON_SCALE = 0.22

# 6. LOGIK
CLEARANCE_TIME_MS = 4000
TIME_FACTOR_SLOW = 0.7
CROWD_BONUS_FACTOR = 0.2

# 7. POSITIONIERUNG
OFFSET_ROT_Y = -230
OFFSET_GRUEN_Y = 230
OFFSET_RING_Y = -2
OFFSET_TRAM_Y = -2

# 8. FARBEN
COLOR_LED_ON = (255, 255, 255)
COLOR_LED_OFF = (40, 40, 40)     # Dunkelgrauer Hintergrund
COLOR_CLEARANCE = (255, 50, 50)
COLOR_WALKER = (255, 255, 255)

# ==========================================
# SYSTEM CODE
# ==========================================

WIDTH, HEIGHT = 0, 0
CENTER_X, CENTER_Y = 0, 0
LED_RADIUS = 0
DOT_SIZE_BASE = 0
images = {}
waiting_images = []
game_font = None

STATE_GREEN = "GREEN"
STATE_RED = "RED"
STATE_CLEARANCE = "CLEARANCE"
STATE_TRAM = "TRAM"


def debug_log(message):
    print(f"[DEBUG] {message}", flush=True)


def load_and_scale_image(path, scale=SCALE_FACTOR):
    try:
        if not os.path.exists(path):
            if "tram" in path or "waiting" in path:
                return None
            else:
                raise FileNotFoundError(f"Datei fehlt: {path}")

        img = pygame.image.load(path).convert_alpha()
        new_width = int(img.get_width() * scale)
        new_height = int(img.get_height() * scale)
        return pygame.transform.smoothscale(img, (new_width, new_height))
    except Exception as e:
        debug_log(f"Fehler bei {path}: {e}")
        sys.exit()


def load_images():
    global game_font, waiting_images
    script_dir = os.path.dirname(os.path.abspath(__file__))
    asset_dir = os.path.join(script_dir, "assets")

    if not os.path.exists(asset_dir):
        debug_log("Assets Ordner fehlt!")
        sys.exit()

    images['housing'] = load_and_scale_image(os.path.join(asset_dir, 'gehaeuse.png'))
    images['red_on'] = load_and_scale_image(os.path.join(asset_dir, 'mann_rot_an.png'))
    images['red_off'] = load_and_scale_image(os.path.join(asset_dir, 'mann_rot_aus.png'))
    images['green_on'] = load_and_scale_image(os.path.join(asset_dir, 'mann_gruen_an.png'))
    images['green_off'] = load_and_scale_image(os.path.join(asset_dir, 'mann_gruen_aus.png'))
    images['tram'] = load_and_scale_image(os.path.join(asset_dir, 'tram.png'))

    for i in range(1, MAX_VISUAL_PERSONS + 1):
        filename = f"waiting_{i}.png"
        full_path = os.path.join(asset_dir, filename)
        img = load_and_scale_image(full_path, scale=WAITING_ICON_SCALE)
        if img:
            waiting_images.append(img)
        else:
            waiting_images.append(None)

    global WIDTH, HEIGHT, CENTER_X, CENTER_Y, LED_RADIUS, DOT_SIZE_BASE
    WIDTH = images['housing'].get_width()
    HEIGHT = images['housing'].get_height()
    CENTER_X = WIDTH // 2
    CENTER_Y = HEIGHT // 2

    LED_RADIUS = int(ORIGINAL_LED_RADIUS * SCALE_FACTOR)
    DOT_SIZE_BASE = int(ORIGINAL_DOT_SIZE * SCALE_FACTOR)
    if DOT_SIZE_BASE < 2:
        DOT_SIZE_BASE = 2

    font_size = int(TIMER_FONT_SIZE * SCALE_FACTOR)
    game_font = pygame.freetype.SysFont("Arial", font_size, bold=True)

# --- ZEICHNEN ---


def draw_crowd_image(screen, person_count):
    if person_count <= 0:
        return
    image_index = min(person_count, MAX_VISUAL_PERSONS) - 1

    if waiting_images and 0 <= image_index < len(waiting_images):
        current_img = waiting_images[image_index]
        if current_img:
            rect = current_img.get_rect(center=(CENTER_X, CENTER_Y + OFFSET_RING_Y))
            screen.blit(current_img, rect)
        else:
            pygame.draw.circle(screen, (100, 100, 100), (CENTER_X, CENTER_Y + OFFSET_RING_Y), 30)
            text = str(person_count)
            game_font.render_to(screen, (CENTER_X-10, CENTER_Y+OFFSET_RING_Y-10), text, (255, 255, 255))


def draw_countdown_timer(screen, remaining_ms):
    seconds = math.ceil(remaining_ms / 1000)
    if seconds < 1:
        seconds = 1
    text = str(seconds)
    text_rect = game_font.get_rect(text)
    x = CENTER_X - (text_rect.width // 2)
    y = CENTER_Y + OFFSET_RING_Y - (text_rect.height // 2)
    game_font.render_to(screen, (x, y), text, (255, 255, 255))


def draw_led_ring(screen, active_leds, total_leds, state, breathing_alpha=255, is_slow_mode=False, pulse_factor=0.0):
    ring_center_y = CENTER_Y + OFFSET_RING_Y

    # Basisgröße
    current_dot_size = DOT_SIZE_BASE

    # ATEM-GRÖSSE (weich berechnet)
    pulsing_size = current_dot_size
    if pulse_factor > 0:
        # Punkte wachsen um bis zu 35%
        pulsing_size = int(current_dot_size + (current_dot_size * 0.35 * pulse_factor))

    # Surface Größe (Großzügiger Puffer gegen Vierecke)
    surf_size = (pulsing_size * 2) + 10
    center_offset = surf_size // 2

    for i in range(total_leds):
        # -90 Grad ist 12 Uhr
        angle = math.radians(-90 + (360 / total_leds) * i)
        x_int = int(CENTER_X + LED_RADIUS * math.cos(angle))
        y_int = int(ring_center_y + LED_RADIUS * math.sin(angle))

        is_lit = False
        is_bonus = False

        # LOGIK FÜR GRÜN PHASE
        if state == STATE_GREEN:
            # actvie_leds zeigt hier an wie viele NOCH leuchten sollen (Countdown)
            if i < active_leds:
                is_lit = True

            # Bonus-Punkte Visualisierung (die ersten paar Punkte sind Bonus)
            if is_slow_mode:
                if i < BONUS_LEDS_COUNT:
                    is_bonus = True

        # LOGIK FÜR ROT / TRAM
        elif state == STATE_RED or state == STATE_TRAM:
            if i < active_leds:
                is_lit = True

        # LOGIK FÜR CLEARANCE
        elif state == STATE_CLEARANCE:
            is_lit = True

        # --- ZEICHNEN ---

        if is_lit:
            if is_bonus and state == STATE_GREEN:
                # BONUS PUNKTE: Atmen (Alpha & Größe)
                dot_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
                # Kreis mittig auf Surface zeichnen
                pygame.draw.circle(dot_surf, COLOR_LED_ON, (center_offset, center_offset), pulsing_size)
                dot_surf.set_alpha(breathing_alpha)
                screen.blit(dot_surf, (x_int - center_offset, y_int - center_offset))

            elif state == STATE_CLEARANCE:
                # CLEARANCE: Nur Alpha Blinken
                dot_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
                pygame.draw.circle(dot_surf, COLOR_CLEARANCE, (center_offset, center_offset), current_dot_size)
                dot_surf.set_alpha(breathing_alpha)
                screen.blit(dot_surf, (x_int - center_offset, y_int - center_offset))

            else:
                # NORMALE PUNKTE: Statisch Weiß
                gfxdraw.filled_circle(screen, x_int, y_int, current_dot_size, COLOR_LED_ON)
                gfxdraw.aacircle(screen, x_int, y_int, current_dot_size, COLOR_LED_ON)
        else:
            # INAKTIVE PUNKTE: Immer sichtbar in Dunkelgrau (Hintergrund)
            gfxdraw.filled_circle(screen, x_int, y_int, current_dot_size, COLOR_LED_OFF)
            gfxdraw.aacircle(screen, x_int, y_int, current_dot_size, COLOR_LED_OFF)


def main():
    debug_log("Starte Programm...")
    pygame.init()
    pygame.display.set_mode((100, 100))
    load_images()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Traffic Light Control")

    # ESP Initialisierung
    esp = ESPController(port=ESP_PORT)
    esp.connect()
    last_esp_values = None

    # Logik Initialisierung
    logic = TrafficLightLogic()

    clock = pygame.time.Clock()

    current_state = STATE_RED

    # Zeitvariablen
    timer_state_elapsed = logic.get_first_green_time_ms()  # Startwert für Auto=Grün
    timer_total_duration = DURATION_RED_BASE_MS

    clearance_start_time = 0
    tram_display_timer = 0
    person_count = 0

    running = True
    while running:
        dt = clock.tick(60)
        now = pygame.time.get_ticks()

        keys = pygame.key.get_pressed()
        slow_walker_detected = keys[pygame.K_SPACE]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    current_state = STATE_TRAM
                    tram_display_timer = pygame.time.get_ticks()

                if event.key == pygame.K_UP:
                    person_count = min(MAX_PERSON_CAP, person_count + 1)

                if event.key == pygame.K_DOWN:
                    person_count = max(0, person_count - 1)

        # ZEIT-FAKTOR (Geschwindigkeit der Zeit)
        current_time_factor = 1.0
        if current_state == STATE_GREEN:
            if slow_walker_detected:
                current_time_factor = TIME_FACTOR_SLOW
        elif current_state == STATE_RED:
            current_time_factor = 1.0 + ((person_count / 5) * CROWD_BONUS_FACTOR)

        # ATEM-BERECHNUNG (Sehr flüssige Sinuswelle)
        pulse = 0.0
        breath_alpha = 255

        if current_state == STATE_GREEN and slow_walker_detected:
            # Frequenz 0.003 für ruhiges Atmen
            pulse = (math.sin(now * 0.003) + 1) / 2
            # Alpha Range: 100 bis 255
            breath_alpha = int(100 + (155 * pulse))

        # Clearance Blink Alpha
        clearance_alpha = 255
        if current_state == STATE_CLEARANCE:
            clearance_alpha = int(128 + 127 * math.sin(now * 0.020))

        if current_state == STATE_TRAM:
            if now - tram_display_timer > 2000:
                current_state = STATE_RED
                timer_state_elapsed = 0
                timer_total_duration = DURATION_RED_BASE_MS

        elif current_state == STATE_CLEARANCE:
            if now - clearance_start_time > CLEARANCE_TIME_MS:
                current_state = STATE_RED
                timer_state_elapsed = 0
                timer_total_duration = DURATION_RED_BASE_MS
                person_count = 0
                debug_log("Reset: Personenanzahl auf 0.")

        else:
            # Zeitfortschritt
            timer_state_elapsed += dt * current_time_factor

            # Zustandswechsel prüfen
            if timer_state_elapsed >= timer_total_duration:
                if current_state == STATE_GREEN:
                    current_state = STATE_CLEARANCE
                    clearance_start_time = now
                    timer_state_elapsed = 0

                elif current_state == STATE_RED:
                    current_state = STATE_GREEN
                    # Berechne Dauer der neuen Grünphase: Basis + Bonus
                    bonus_time = person_count * BONUS_TIME_PER_PERSON_MS
                    timer_total_duration = DURATION_GREEN_BASE_MS + bonus_time
                    timer_state_elapsed = 0

        # Berechnungen für Visualisierung LEDS
        # Mapping von Zeit -> Anzahl LEDs (VISUAL_LED_COUNT)
        active_leds_visual = 0
        if current_state == STATE_RED:
            ratio = timer_state_elapsed / timer_total_duration
            if ratio > 1:
                ratio = 1
            active_leds_visual = int(ratio * VISUAL_LED_COUNT)

        elif current_state == STATE_GREEN:
            ratio = timer_state_elapsed / timer_total_duration
            if ratio > 1:
                ratio = 1
            # Grün zählt runter
            remaining_ratio = 1.0 - ratio
            active_leds_visual = int(remaining_ratio * VISUAL_LED_COUNT)

        # ESP Update Logik (getrennt in traffic_logic.py)
        # Berechne Soll-Zustand aller Lampen
        lights = logic.calculate_lights(current_state, timer_state_elapsed, timer_total_duration)

        # Sende nur bei Änderung
        current_values = (lights["main_red"], lights["main_green"],
                          lights["car_red"], lights["car_yellow"], lights["car_green"])

        if current_values != last_esp_values:
            esp.update_leds(*current_values)
            last_esp_values = current_values

        # ZEICHNEN
        screen.fill((0, 0, 0))

        housing_rect = images['housing'].get_rect(center=(CENTER_X, CENTER_Y))
        screen.blit(images['housing'], housing_rect)

        pos_rot = (CENTER_X, CENTER_Y + OFFSET_ROT_Y)
        pos_gruen = (CENTER_X, CENTER_Y + OFFSET_GRUEN_Y)
        pos_tram = (CENTER_X, CENTER_Y + OFFSET_TRAM_Y)

        if current_state == STATE_GREEN:
            screen.blit(images['red_off'], images['red_off'].get_rect(center=pos_rot))
            screen.blit(images['green_on'], images['green_on'].get_rect(center=pos_gruen))
        else:
            screen.blit(images['red_on'], images['red_on'].get_rect(center=pos_rot))
            screen.blit(images['green_off'], images['green_off'].get_rect(center=pos_gruen))

        if current_state == STATE_TRAM:
            tram_rect = images['tram'].get_rect(center=pos_tram)
            screen.blit(images['tram'], tram_rect)
            draw_led_ring(screen, VISUAL_LED_COUNT, VISUAL_LED_COUNT, STATE_TRAM, 255)

        elif current_state == STATE_CLEARANCE:
            draw_led_ring(screen, VISUAL_LED_COUNT, VISUAL_LED_COUNT, STATE_CLEARANCE, clearance_alpha)
            time_left = CLEARANCE_TIME_MS - (now - clearance_start_time)
            draw_countdown_timer(screen, time_left)

        elif current_state == STATE_GREEN:
            # Ring zeichnen
            draw_led_ring(screen, active_leds_visual, VISUAL_LED_COUNT, STATE_GREEN, breath_alpha, is_slow_mode=slow_walker_detected, pulse_factor=pulse)

        else:  # STATE_RED
            draw_crowd_image(screen, person_count)
            draw_led_ring(screen, active_leds_visual, VISUAL_LED_COUNT, STATE_RED, 255)

        pygame.display.flip()

    esp.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
