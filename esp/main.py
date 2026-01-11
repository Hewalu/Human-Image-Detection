import sys
from machine import Pin
import time
import select

# Pin Konfiguration
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

    while True:
        try:
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

            time.sleep(0.05)

        except Exception as e:
            # Fehler protokollieren aber weiter laufen
            # print(f"ERR: {e}")
            pass


if __name__ == "__main__":
    main()
