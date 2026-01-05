import pygame
import pygame.freetype 
from pygame import gfxdraw
import math
import sys
import os

# ==========================================
#      KONFIGURATION
# ==========================================

SCALE_FACTOR = 0.3   

# 1. PERSONEN LOGIK
MAX_PERSON_CAP = 15      
MAX_VISUAL_PERSONS = 8   
ADD_LEDS_PER_PERSON = 2  

# 2. LED ANZAHL
BASE_LEDS_GREEN = 12     
TOTAL_LEDS_RED   = 34    
MAX_LEDS_LIMIT = 34      

# 3. GESCHWINDIGKEIT
SECONDS_PER_LED_GREEN = 1.0  
SECONDS_PER_LED_RED   = 0.3  

# 4. OPTIK
TIMER_FONT_SIZE = 280     
ORIGINAL_LED_RADIUS = 235  
ORIGINAL_DOT_SIZE   = 20
WAITING_ICON_SCALE = 0.22 

# 5. LOGIK
CLEARANCE_TIME_MS = 4000 
TIME_FACTOR_SLOW = 0.7   
CROWD_BONUS_FACTOR = 0.2 

# 6. POSITIONIERUNG
OFFSET_ROT_Y   = -230  
OFFSET_GRUEN_Y = 230   
OFFSET_RING_Y  = -2    
OFFSET_TRAM_Y  = -2    

# 7. FARBEN
COLOR_LED_ON  = (255, 255, 255)  
COLOR_LED_OFF = (60, 60, 60)
COLOR_CLEARANCE = (255, 50, 50) 
COLOR_WALKER = (255, 255, 255) 

# ==========================================
# SYSTEM CODE
# ==========================================

MS_PER_LED_GREEN = int(SECONDS_PER_LED_GREEN * 1000)
MS_PER_LED_RED   = int(SECONDS_PER_LED_RED * 1000)

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
            if "tram" in path or "waiting" in path: return None 
            else: raise FileNotFoundError(f"Datei fehlt: {path}")

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
    
    # Großes Grünes Männchen für die Mitte laden (wir nutzen das gleiche Bild wie oben)
    # Aber wir wollen es vielleicht etwas größer skalieren für die Mitte?
    # Wir laden es einfach nochmal mit dem Standard-Scale
    images['center_green_man'] = load_and_scale_image(os.path.join(asset_dir, 'mann_gruen_an.png'))

    # Wartende Personen Icons
    for i in range(1, MAX_VISUAL_PERSONS + 1):
        filename = f"waiting_{i}.png"
        full_path = os.path.join(asset_dir, filename)
        img = load_and_scale_image(full_path, scale=WAITING_ICON_SCALE)
        if img: waiting_images.append(img)
        else: waiting_images.append(None)

    global WIDTH, HEIGHT, CENTER_X, CENTER_Y, LED_RADIUS, DOT_SIZE_BASE
    WIDTH = images['housing'].get_width()
    HEIGHT = images['housing'].get_height()
    CENTER_X = WIDTH // 2
    CENTER_Y = HEIGHT // 2
    
    LED_RADIUS = int(ORIGINAL_LED_RADIUS * SCALE_FACTOR)
    DOT_SIZE_BASE = int(ORIGINAL_DOT_SIZE * SCALE_FACTOR)
    if DOT_SIZE_BASE < 2: DOT_SIZE_BASE = 2
    
    font_size = int(TIMER_FONT_SIZE * SCALE_FACTOR)
    game_font = pygame.freetype.SysFont("Arial", font_size, bold=True)

# --- NEU: STATISCHES MÄNNCHEN MIT BREATHING EFFEKT ---

def draw_green_man_responsive(screen, is_slow_mode, ticks):
    """
    Zeichnet das grüne Männchen.
    Wenn is_slow_mode = True, dann "atmet" es (Skalierung + Alpha).
    """
    base_img = images['center_green_man']
    if not base_img: return

    x, y = CENTER_X, CENTER_Y + OFFSET_RING_Y
    
    if is_slow_mode:
        # BREATHING MATHEMATIK
        # Sinus Welle für sanftes Pulsieren (Langsam: Speed 0.003)
        # Wert zwischen 0.0 und 1.0
        pulse = (math.sin(ticks * 0.004) + 1) / 2 
        
        # 1. SKALIERUNG (Es wird ca. 10% größer und wieder kleiner)
        # Basis ist 1.0, Max ist 1.1
        scale_factor = 1.0 + (0.1 * pulse)
        
        # Bild skalieren
        orig_w = base_img.get_width()
        orig_h = base_img.get_height()
        new_w = int(orig_w * scale_factor)
        new_h = int(orig_h * scale_factor)
        
        scaled_img = pygame.transform.smoothscale(base_img, (new_w, new_h))
        
        # 2. ALPHA BLENDING (Es leuchtet heller/dunkler)
        # Wir machen es etwas transparenter beim Ausatmen
        # Alpha zwischen 180 und 255
        current_alpha = int(180 + (75 * pulse))
        scaled_img.set_alpha(current_alpha)
        
        rect = scaled_img.get_rect(center=(x, y))
        screen.blit(scaled_img, rect)
        
    else:
        # NORMAL MODUS: Einfach statisch zeichnen (volle Deckkraft)
        base_img.set_alpha(255)
        rect = base_img.get_rect(center=(x, y))
        screen.blit(base_img, rect)


def draw_crowd_image(screen, person_count):
    if person_count <= 0: return
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
    if seconds < 1: seconds = 1 
    text = str(seconds)
    text_rect = game_font.get_rect(text)
    x = CENTER_X - (text_rect.width // 2)
    y = CENTER_Y + OFFSET_RING_Y - (text_rect.height // 2)
    game_font.render_to(screen, (x, y), text, (255, 255, 255))

def draw_led_ring(screen, active_leds, total_leds, state, breathing_alpha=255):
    ring_center_y = CENTER_Y + OFFSET_RING_Y
    
    current_dot_size = DOT_SIZE_BASE
    if total_leds > 60:
        factor = 60 / total_leds
        current_dot_size = max(2, int(DOT_SIZE_BASE * factor))
    
    for i in range(total_leds):
        angle = math.radians(-90 + (360 / total_leds) * i)
        x_int = int(CENTER_X + LED_RADIUS * math.cos(angle))
        y_int = int(ring_center_y + LED_RADIUS * math.sin(angle))
        
        is_lit = False
        current_color = COLOR_LED_OFF

        if state == STATE_GREEN:
            leds_gone = total_leds - active_leds
            if i >= leds_gone: 
                is_lit = True
                current_color = COLOR_LED_ON
        elif state == STATE_RED:
            if i < active_leds: 
                is_lit = True
                current_color = COLOR_LED_ON
        elif state == STATE_CLEARANCE:
            is_lit = True
            current_color = COLOR_CLEARANCE
        elif state == STATE_TRAM:
            is_lit = True
            current_color = COLOR_LED_ON

        if is_lit:
            if breathing_alpha < 255 or state == STATE_CLEARANCE:
                target_surface = pygame.Surface((current_dot_size*2, current_dot_size*2), pygame.SRCALPHA)
                r, g, b = current_color
                pygame.draw.circle(target_surface, (r, g, b, breathing_alpha), (current_dot_size, current_dot_size), current_dot_size)
                screen.blit(target_surface, (x_int-current_dot_size, y_int-current_dot_size))
            else:
                gfxdraw.filled_circle(screen, x_int, y_int, current_dot_size, current_color)
                gfxdraw.aacircle(screen, x_int, y_int, current_dot_size, current_color)
        else:
            # gfxdraw.filled_circle(screen, x_int, y_int, current_dot_size, COLOR_LED_OFF)
            pass 

def main():
    debug_log("Starte Programm...")
    pygame.init()
    pygame.display.set_mode((100, 100))
    load_images()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Traffic Light Control")
    
    clock = pygame.time.Clock()
    
    current_state = STATE_RED 
    led_counter = 0
    current_total_leds = TOTAL_LEDS_RED 
    
    timer_accumulator = 0 
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

        # ZEIT-FAKTOR
        current_time_factor = 1.0 
        if current_state == STATE_GREEN:
            if slow_walker_detected: current_time_factor = TIME_FACTOR_SLOW
        elif current_state == STATE_RED:
            current_time_factor = 1.0 + ((person_count / 5) * CROWD_BONUS_FACTOR)

        # Breathing Alpha (für den Ring)
        # Wir nutzen den gleichen Rhythmus wie für das Männchen
        breath_alpha = 255
        if current_state == STATE_GREEN and slow_walker_detected:
             pulse = (math.sin(now * 0.004) + 1) / 2 
             breath_alpha = int(100 + (155 * pulse)) # Ring dimmt stärker

        if current_state == STATE_TRAM:
            if now - tram_display_timer > 2000:
                current_state = STATE_RED 
                current_total_leds = TOTAL_LEDS_RED 
                led_counter = 0

        elif current_state == STATE_CLEARANCE:
            if now - clearance_start_time > CLEARANCE_TIME_MS:
                current_state = STATE_RED
                current_total_leds = TOTAL_LEDS_RED 
                led_counter = 0
                person_count = 0 
                debug_log("Reset: Personenanzahl auf 0.")

        else:
            timer_accumulator += dt * current_time_factor
            time_threshold = MS_PER_LED_GREEN if current_state == STATE_GREEN else MS_PER_LED_RED
            
            if timer_accumulator >= time_threshold:
                timer_accumulator -= time_threshold
                
                if current_state == STATE_GREEN:
                    led_counter -= 1
                    if led_counter < 0:
                        current_state = STATE_CLEARANCE
                        clearance_start_time = now
                        led_counter = 0
                        timer_accumulator = 0
                
                elif current_state == STATE_RED:
                    led_counter += 1
                    if led_counter > TOTAL_LEDS_RED:
                        current_state = STATE_GREEN
                        bonus_leds = person_count * ADD_LEDS_PER_PERSON
                        total_green = BASE_LEDS_GREEN + bonus_leds
                        if total_green > MAX_LEDS_LIMIT: total_green = MAX_LEDS_LIMIT
                        current_total_leds = total_green
                        led_counter = total_green
                        timer_accumulator = 0

        # ZEICHNEN
        screen.fill((0,0,0)) 
        
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
            draw_led_ring(screen, TOTAL_LEDS_RED, TOTAL_LEDS_RED, STATE_TRAM, 255)

        elif current_state == STATE_CLEARANCE:
            flash_alpha = int(128 + 127 * math.sin(now * 0.020)) 
            draw_led_ring(screen, current_total_leds, current_total_leds, STATE_CLEARANCE, flash_alpha)
            time_left = CLEARANCE_TIME_MS - (now - clearance_start_time)
            draw_countdown_timer(screen, time_left)

        elif current_state == STATE_GREEN:
            # NEU: Responsive Green Man
            draw_green_man_responsive(screen, slow_walker_detected, now)
            draw_led_ring(screen, led_counter, current_total_leds, STATE_GREEN, breath_alpha)
            
        else: # STATE_RED
            draw_crowd_image(screen, person_count)
            draw_led_ring(screen, led_counter, TOTAL_LEDS_RED, STATE_RED, 255)

        pygame.display.flip() 

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()