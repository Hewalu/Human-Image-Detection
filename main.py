import cv2
import time
import numpy as np
from ultralytics import YOLO

# Konfiguration
RED_DURATION = 40
GREEN_DURATION = 15
DEBOUNCE_TIME = 0.25  # Reduziert auf 0.25 Sekunden
PERSON_REDUCE_DURATION = 10


class TrafficLight:
    def __init__(self):
        self.state = "RED"
        self.start_time = time.time()
        self.current_timer = RED_DURATION

    def update(self, person_count):
        now = time.time()
        elapsed = now - self.start_time

        if self.state == "RED":
            # Dynamische Dauer
            effective_duration = max(0, RED_DURATION - (person_count * PERSON_REDUCE_DURATION))

            if elapsed >= effective_duration:
                # Wechsel zu Grün
                self.state = "GREEN"
                self.start_time = now
                self.current_timer = GREEN_DURATION
            else:
                self.current_timer = int(effective_duration - elapsed) + 1

        elif self.state == "GREEN":
            # Feste Dauer für Grün
            if elapsed >= GREEN_DURATION:
                # Wechsel zurück zu Rot
                self.state = "RED"
                self.start_time = now
                self.current_timer = RED_DURATION
            else:
                self.current_timer = int(GREEN_DURATION - elapsed) + 1

    def get_state(self):
        return self.state, self.current_timer


class CountSmoother:
    def __init__(self):
        self.display_count = 0
        self.pending_count = 0
        self.pending_start_time = time.time()

    def update(self, raw_count):
        # Wenn sich der rohe Wert ändert, setze den Timer zurück
        if raw_count != self.pending_count:
            self.pending_count = raw_count
            self.pending_start_time = time.time()
        else:
            # Wenn der Wert stabil ist, prüfe wie lange schon
            if time.time() - self.pending_start_time >= DEBOUNCE_TIME:
                self.display_count = self.pending_count

        return self.display_count


def list_available_cameras(max_check=5):
    """Listet verfügbare Kamera-Indizes auf."""
    print("Suche nach verfügbaren Kameras...")
    available = []
    for i in range(max_check):
        temp_cap = cv2.VideoCapture(i)
        if temp_cap.isOpened():
            print(f" [✓] Kamera gefunden auf Index {i}")
            available.append(i)
            temp_cap.release()
    if not available:
        print(" [!] Keine Kameras gefunden.")
    print("-" * 30)
    return available


def draw_interface(frame, traffic_light, person_count, width=1920, height=1080):
    # Erstelle Hintergrund (Dunkelgrau für besseren Kontrast)
    canvas = np.full((height, width, 3), 30, dtype=np.uint8)

    # --- Linke Seite: Kamera Feed (70% der Breite) ---
    left_w = int(width * 0.7)
    h, w = frame.shape[:2]

    # Skaliere Frame, damit er in die linke Hälfte passt (Aspect Ratio beibehalten)
    scale = min(left_w / w, height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized_frame = cv2.resize(frame, (new_w, new_h))

    # Zentriere das Bild im linken Bereich
    y_offset = (height - new_h) // 2
    x_offset = (left_w - new_w) // 2

    # Zeichne Rahmen um das Kamerabild
    cv2.rectangle(canvas, (x_offset-2, y_offset-2), (x_offset+new_w+2, y_offset+new_h+2), (100, 100, 100), 2)
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_frame

    # --- Rechte Seite: UI (30% der Breite) ---
    right_center_x = left_w + (width - left_w) // 2

    # 1. Ampel (Oben)
    state, timer = traffic_light.get_state()
    light_y = height // 4
    radius = 120  # Etwas größer

    if state == "RED":
        color = (0, 0, 255)  # Rot
        status_text = "WARTEN"
    else:
        color = (0, 255, 0)  # Grün
        status_text = "GEHEN"

    # Ampel-Hintergrund (Dunklerer Kreis)
    cv2.circle(canvas, (right_center_x, light_y), radius + 10, (50, 50, 50), -1)
    # Aktives Licht
    cv2.circle(canvas, (right_center_x, light_y), radius, color, -1)

    # Status Text in der Ampel
    text_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
    cv2.putText(canvas, status_text, (right_center_x - text_size[0]//2, light_y + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

    # Timer Text unter der Ampel
    timer_text = f"{timer}s"
    text_size = cv2.getTextSize(timer_text, cv2.FONT_HERSHEY_SIMPLEX, 4, 8)[0]
    text_x = right_center_x - text_size[0] // 2
    cv2.putText(canvas, timer_text, (text_x, light_y + radius + 100),
                cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 8)

    # 2. Personen Counter Visualisierung (Unten)
    # Rechteck Bereich
    rect_size = 400
    rect_y = height // 2 + 150
    top_left = (right_center_x - rect_size // 2, rect_y)
    bottom_right = (right_center_x + rect_size // 2, rect_y + rect_size)

    # Rahmen für Counter
    cv2.rectangle(canvas, top_left, bottom_right, (80, 80, 80), -1)  # Hintergrund
    cv2.rectangle(canvas, top_left, bottom_right, (200, 200, 200), 2)  # Rahmen

    # Titel für Counter
    title = f"Personen: {person_count}"
    title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
    cv2.putText(canvas, title, (right_center_x - title_size[0]//2, rect_y - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

    # Kreise für Personen (3x3 Grid)
    display_circles = min(person_count, 9)
    cell_size = rect_size // 3

    for i in range(display_circles):
        row = i // 3
        col = i % 3

        cx = top_left[0] + col * cell_size + cell_size // 2
        cy = top_left[1] + row * cell_size + cell_size // 2

        # Zeichne Kreis (Gelb/Orange mit leichtem Glow-Effekt)
        cv2.circle(canvas, (cx, cy), 45, (0, 165, 255), -1)  # Orange
        cv2.circle(canvas, (cx, cy), 40, (0, 200, 255), -1)  # Gelb Kern

    return canvas


def main():
    # Zeige verfügbare Kameras an
    available_cams = list_available_cameras()

    # Lade das YOLOv11 Nano Modell
    print("Lade Modell (YOLOv11n)...")
    try:
        model = YOLO("yolo11n.pt")
    except Exception as e:
        print(f"Fehler beim Laden des Modells: {e}")
        return

    # Initialisiere Logik-Klassen
    traffic_light = TrafficLight()
    smoother = CountSmoother()

    # Öffne die Webcam
    source = 0
    if len(available_cams) > 1 and source not in available_cams:
        print(f"Warnung: Kamera {source} nicht gefunden. Versuche {available_cams[0]}...")
        source = available_cams[0]

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"Fehler: Konnte Videoquelle '{source}' nicht öffnen.")
        return

    # Fenster erstellen und auf Vollbild setzen
    window_name = "Personenerkennung Interface"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    print("Starte Personenerkennung.")
    print(" [q] Beenden")
    print(" [c] Kamera wechseln")

    while True:
        success, frame = cap.read()
        if not success:
            print("Ende des Videostreams oder Fehler beim Lesen.")
            # Kurze Pause, um CPU nicht zu überlasten, falls Kamera weg ist
            time.sleep(0.1)
            continue

        # Führe YOLO Inference auf dem Frame aus
        results = model(frame, classes=[0], verbose=False)

        # Zeichne Boxen auf den Frame (für die linke Ansicht)
        annotated_frame = results[0].plot()

        # Zähle Personen (Rohdaten)
        raw_count = len(results[0].boxes)

        # Glätte den Wert (Debouncing)
        smooth_count = smoother.update(raw_count)

        # Aktualisiere Ampel-Logik
        traffic_light.update(smooth_count)

        # Erstelle das UI
        # Wir nehmen an, der Bildschirm ist 1920x1080.
        # Falls dein Bildschirm anders ist, passt sich das Fenster an,
        # aber die interne Canvas-Größe bleibt fix.
        ui_frame = draw_interface(annotated_frame, traffic_light, smooth_count)

        # Zeige das Bild an
        cv2.imshow(window_name, ui_frame)

        # Tastensteuerung
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            # Kamera wechseln
            if len(available_cams) > 0:
                print("Wechsle Kamera...")
                cap.release()

                try:
                    current_idx = available_cams.index(source)
                    next_idx = (current_idx + 1) % len(available_cams)
                except ValueError:
                    next_idx = 0

                source = available_cams[next_idx]
                print(f"Versuche Kamera {source} zu öffnen...")
                cap = cv2.VideoCapture(source)

                if not cap.isOpened():
                    print(f"Warnung: Konnte Kamera {source} nicht öffnen.")
            else:
                print("Keine Kameras in der Liste verfügbar.")

    # Ressourcen freigeben
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
