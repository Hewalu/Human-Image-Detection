import cv2
import os
from ultralytics import YOLO
from collections import defaultdict
import numpy as np

# --- KONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "assets")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
MODEL_NAME = "yolo11x.pt"  # 'x' ist das größte/beste Modell (da keine Echtzeit nötig)
TRACK_HISTORY = defaultdict(lambda: [])
MAX_TRAIL_LENGTH = 30  # Wie lang soll der Schweif sein? (Anzahl Frames)
# ---------------------


def process_video(video_file):
    input_path = os.path.join(INPUT_FOLDER, video_file)
    output_path = os.path.join(OUTPUT_FOLDER, "tracked_" + video_file)

    # Modell laden
    model = YOLO(MODEL_NAME)

    cap = cv2.VideoCapture(input_path)

    # Video-Eigenschaften für den Output Writer holen
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Video Writer initialisieren
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    print(f"Verarbeite: {video_file}...")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # YOLO Tracking ausführen
        # persist=True ist wichtig, damit das Tracking über Frames hinweg funktioniert
        results = model.track(frame, persist=True, classes=[0], verbose=False)  # classes=[0] filtert nur Personen

        if results[0].boxes.id is not None:
            # IDs und Boxen holen
            boxes = results[0].boxes.xywh.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()

            # Plotten der Standard-Boxen (optional, kann man auch weglassen für nur Linien)
            annotated_frame = results[0].plot()

            for box, track_id in zip(boxes, track_ids):
                x, y, w, h = box
                center = (float(x), float(y))

                # Position zur History hinzufügen
                track = TRACK_HISTORY[track_id]
                track.append(center)
                if len(track) > MAX_TRAIL_LENGTH:
                    track.pop(0)

                # Linie zeichnen
                points = np.hstack(track).astype(np.int32).reshape((-1, 1, 2))
                # Farbe: Gelb, Dicke: 4
                cv2.polylines(annotated_frame, [points], isClosed=False, color=(0, 255, 255), thickness=4)
        else:
            annotated_frame = frame

        out.write(annotated_frame)

    cap.release()
    out.release()
    print(f"Fertig! Gespeichert unter: {output_path}")

    # History für das nächste Video zurücksetzen
    TRACK_HISTORY.clear()


# --- MAIN ---
if __name__ == "__main__":
    # Ordner erstellen, falls nicht vorhanden
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Alle Videodateien im assets Ordner finden
    video_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]

    if not video_files:
        print(f"Keine Videos im Ordner '{INPUT_FOLDER}' gefunden.")
    else:
        for video in video_files:
            process_video(video)
