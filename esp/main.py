import sys
from machine import Pin, PWM
import time
import select
import math

# --- Konfiguration aus test.py ---
PIN_ALWAYS_ON = 14  # Immer AN
PIN_LED_PULSE = 27  # LED Output (Pulse)
PIN_BTN1 = 39       # Button 1 Input (Start Trigger)
PIN_BTN2 = 36       # Button 2 Input

# Pin Konfiguration Ampeln
# Hauptampel (Fußgänger)
PIN_MAIN_RED = 13
PIN_MAIN_GREEN = 32

# Autoampel (Invertiert/Neben)
PIN_CAR_RED = 12
PIN_CAR_YELLOW = 26
PIN_CAR_GREEN = 33

# Hall Sensoren Ampel 1
PIN_AMPEL1_SENSOR1 = 18
PIN_AMPEL1_SENSOR2 = 19
PIN_AMPEL1_SENSOR3 = 21

# Hall Sensoren Ampel 2
PIN_AMPEL2_SENSOR1 = 16
PIN_AMPEL2_SENSOR2 = 17
PIN_AMPEL2_SENSOR3 = 5

# Hall Sensoren Bahnhof
PIN_TRAIN_SENSOR1 = 15
PIN_TRAIN_SENSOR2 = 4

led_main_red = Pin(PIN_MAIN_RED, Pin.OUT)
led_main_green = Pin(PIN_MAIN_GREEN, Pin.OUT)
led_car_red = Pin(PIN_CAR_RED, Pin.OUT)
led_car_yellow = Pin(PIN_CAR_YELLOW, Pin.OUT)
led_car_green = Pin(PIN_CAR_GREEN, Pin.OUT)

# --- Neue Pins Setup ---
# 1. Always On
try:
    p_always_on = Pin(PIN_ALWAYS_ON, Pin.OUT)
    p_always_on.value(1)
except Exception:
    pass

# 2. Pulse LED
pwm_pulse = None
try:
    pwm_pulse = PWM(Pin(PIN_LED_PULSE), freq=1000, duty=0)
except Exception:
    pwm_pulse = None

# 3. Buttons (Input only, no pullup on 34-39 usually)
try:
    btn1 = Pin(PIN_BTN1, Pin.IN)
except:
    btn1 = None
try:
    btn2 = Pin(PIN_BTN2, Pin.IN)
except:
    btn2 = None


# Sensoren initialisieren (Pullup, da Hall-Sensoren oft Open-Drain sind oder Active Low)
ampel1_sensor1 = Pin(PIN_AMPEL1_SENSOR1, Pin.IN, Pin.PULL_UP)
ampel1_sensor2 = Pin(PIN_AMPEL1_SENSOR2, Pin.IN, Pin.PULL_UP)
ampel1_sensor3 = Pin(PIN_AMPEL1_SENSOR3, Pin.IN, Pin.PULL_UP)

ampel2_sensor1 = Pin(PIN_AMPEL2_SENSOR1, Pin.IN, Pin.PULL_UP)
ampel2_sensor2 = Pin(PIN_AMPEL2_SENSOR2, Pin.IN, Pin.PULL_UP)
ampel2_sensor3 = Pin(PIN_AMPEL2_SENSOR3, Pin.IN, Pin.PULL_UP)

train_sensor1 = Pin(PIN_TRAIN_SENSOR1, Pin.IN, Pin.PULL_UP)
train_sensor2 = Pin(PIN_TRAIN_SENSOR2, Pin.IN, Pin.PULL_UP)

all_sensors = [
    ampel1_sensor1, ampel1_sensor2, ampel1_sensor3,
    ampel2_sensor1, ampel2_sensor2, ampel2_sensor3,
    train_sensor1, train_sensor2
]


def set_lights(m_red, m_green, c_red, c_yellow, c_green):
    led_main_red.value(m_red)
    led_main_green.value(m_green)
    led_car_red.value(c_red)
    led_car_yellow.value(c_yellow)
    led_car_green.value(c_green)


def main():
    # Initialer Test
    print("ESP32 Ready. Waiting for LED commands + Sensing...")
    # Format: L <MR> <MG> <CR> <CY> <CG>

    # Non-blocking Input Setup
    poll_obj = select.poll()
    poll_obj.register(sys.stdin, select.POLLIN)

    last_states = []
    pulsing_active = False
    last_btn1_val = 0
    last_btn2_val = 0

    while True:
        try:
            # 0. Pulsing Logic (PWM Breathing)
            if pulsing_active and pwm_pulse:
                # Breathing effect: Sinus-Welle
                # Periode ca. 1.5 - 2 Sekunden für "Atmen"
                # ticks_ms() läuft kontinuierlich
                t = time.ticks_ms() / 1000.0  # Sekunden
                # sin(t * speed) -> -1..1 -> in 0..1023 mappen
                # speed factor: pi wäre 2s periode, 3*t wäre schneller
                val = (math.sin(t * 3) + 1) / 2  # 0.0 bis 1.0
                duty = int(val * 1023)
                pwm_pulse.duty(duty)
            elif pwm_pulse:
                pwm_pulse.duty(0)

            # 1. Befehle lesen (Nicht blockierend)
            poll_results = poll_obj.poll(0)  # 0ms wait
            if poll_results:
                line = sys.stdin.readline()
                if line:
                    parts = line.strip().split()
                    if len(parts) > 0:
                        cmd = parts[0].upper()
                        if cmd == "L" and len(parts) >= 6:
                            mr = int(parts[1])
                            mg = int(parts[2])
                            cr = int(parts[3])
                            cy = int(parts[4])
                            cg = int(parts[5])
                            set_lights(mr, mg, cr, cy, cg)
                        elif cmd == "P" and len(parts) >= 2:
                            # Pulse Command: P 1 (an), P 0 (aus)
                            val = int(parts[1])
                            pulsing_active = (val == 1)

            # 2. Sensoren lesen
            # Annahme: PULL_UP + Magnet zieht auf GND (LOW) -> Active Low
            current_states = []
            for s in all_sensors:
                val = 1 if s.value() == 0 else 0
                current_states.append(val)

            # Wenn sich der Status ändert, senden wir Details
            if current_states != last_states:
                # Format: S <s1> <s2> <s3> <s4> <s5> <s6>
                msg_parts = [str(x) for x in current_states]
                print(f"S {' '.join(msg_parts)}")
                last_states = current_states

            # 3. Buttons lesen
            if btn1:
                b1_val = btn1.value()
                # Rising Edge Detection (0 -> 1)
                # Oder High-State transmission. "B 1" senden bei Drücken.
                # Wir senden einmalig bei Änderung auf 1
                if b1_val == 1 and last_btn1_val == 0:
                    print("B 1")
                    # Sofortiges Feedback (optional, aber User meint 'sobald man drückt')
                    pulsing_active = True
                last_btn1_val = b1_val

            if btn2:
                b2_val = btn2.value()
                if b2_val == 1 and last_btn2_val == 0:
                    print("B 2")
                last_btn2_val = b2_val

            time.sleep(0.05)

        except Exception as e:
            # Fehler protokollieren aber weiter laufen
            # print(f"ERR: {e}")
            pass


if __name__ == "__main__":
    main()
