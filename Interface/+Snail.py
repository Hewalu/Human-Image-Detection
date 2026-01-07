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

# 3. BONUS PUNKTE (Nicht mehr relevant für neue Logik, aber drin gelassen)
BONUS_LEDS_COUNT = 3     

# 4. GESCHWINDIGKEIT
SECONDS_PER_LED_GREEN = 1.0  
SECONDS_PER_LED_RED   = 0.3  

# 5. OPTIK
TIMER_FONT_SIZE = 280     
ORIGINAL_LED_RADIUS = 235  
ORIGINAL_DOT_SIZE   = 20
WAITING_ICON_SCALE = 0.22 
SNAIL_ICON_SCALE = 0.07 # Skalierung für die Schnecke

# 6. LOGIK
CLEARANCE_TIME_MS = 4000 
TIME_FACTOR_SLOW = 0.7   # Faktor für langsameres Ablaufen
CROWD_BONUS_FACTOR = 0.2 

# 7. POSITIONIERUNG
OFFSET_ROT_Y   = -230  
OFFSET_GRUEN_Y = 230   
OFFSET_RING_Y  = -2    
OFFSET_TRAM_Y  = -2    

# 8. FARBEN
COLOR_LED_ON  = (255, 255, 255)  
COLOR_LED_OFF = (40, 40, 40)     # Dunkelgrauer Hintergrund
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
            if "tram" in path or "waiting" in path or "snail" in path: return None 
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
    
    # Lade Snail Bild
    images['snail'] = load_and_scale_image(os.path.join(asset_dir, 'snail.png'), scale=SNAIL_ICON_SCALE)

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

# --- ZEICHNEN ---

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

def draw_snail(screen, alpha):
    snail_img = images.get('snail')
    if snail_img:
        # Erstelle eine Kopie des Bildes, um Alpha zu setzen, ohne das Original zu ändern
        temp_snail = snail_img.copy()
        temp_snail.set_alpha(alpha)
        rect = temp_snail.get_rect(center=(CENTER_X, CENTER_Y + OFFSET_RING_Y))
        screen.blit(temp_snail, rect)

def draw_countdown_timer(screen, remaining_ms):
    seconds = math.ceil(remaining_ms / 1000)
    if seconds < 1: seconds = 1 
    text = str(seconds)
    text_rect = game_font.get_rect(text)
    x = CENTER_X - (text_rect.width // 2)
    y = CENTER_Y + OFFSET_RING_Y - (text_rect.height // 2)
    game_font.render_to(screen, (x, y), text, (255, 255, 255))

def draw_led_ring(screen, active_leds, total_leds, state, breathing_alpha=255, is_slow_mode=False, pulse_factor=0.0):
    ring_center_y = CENTER_Y + OFFSET_RING_Y
    
    # Basisgröße
    current_dot_size = DOT_SIZE_BASE
    if total_leds > 60:
        factor = 60 / total_leds
        current_dot_size = max(2, int(DOT_SIZE_BASE * factor))
    
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
        current_color = COLOR_LED_OFF

        # LOGIK FÜR GRÜN PHASE
        if state == STATE_GREEN:
            # Reguläre LEDs (Die Schlange)
            leds_gone = total_leds - active_leds
            if i >= leds_gone: 
                is_lit = True
                current_color = COLOR_LED_ON
            
        # LOGIK FÜR ROT / TRAM
        elif state == STATE_RED or state == STATE_TRAM:
            if i < active_leds: 
                is_lit = True
                current_color = COLOR_LED_ON
        
        # LOGIK FÜR CLEARANCE
        elif state == STATE_CLEARANCE:
            is_lit = True
            current_color = COLOR_CLEARANCE

        # --- ZEICHNEN ---
        
        if is_lit:
            # Surface erstellen für Alpha-Transparenz und Größe
            # Wenn Slow Mode aktiv ist (state == STATE_GREEN und is_slow_mode), 
            # dann atmen ALLE aktiven Punkte.
            # Ebenso bei Clearance.
            # Bei normalem Grün (ohne Slow Mode) sind sie statisch.
            
            use_breathing = False
            use_pulsing_size = False
            
            if state == STATE_GREEN and is_slow_mode:
                use_breathing = True
                use_pulsing_size = True
            elif state == STATE_CLEARANCE:
                use_breathing = True
                # Bei Clearance keine Größenänderung im original Code, kann aber auch aktiviert werden
            
            final_size = pulsing_size if use_pulsing_size else current_dot_size
            surf_size_local = (final_size * 2) + 10
            center_offset_local = surf_size_local // 2
            
            if use_breathing:
                dot_surf = pygame.Surface((surf_size_local, surf_size_local), pygame.SRCALPHA)
                pygame.draw.circle(dot_surf, current_color, (center_offset_local, center_offset_local), final_size)
                dot_surf.set_alpha(breathing_alpha)
                screen.blit(dot_surf, (x_int - center_offset_local, y_int - center_offset_local))
            else:
                # NORMALE PUNKTE: Statisch, Weiß, Hart
                gfxdraw.filled_circle(screen, x_int, y_int, current_dot_size, current_color)
                gfxdraw.aacircle(screen, x_int, y_int, current_dot_size, current_color)
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
            # 
            if slow_walker_detected: current_time_factor = TIME_FACTOR_SLOW
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
            draw_led_ring(screen, current_total_leds, current_total_leds, STATE_CLEARANCE, clearance_alpha)
            time_left = CLEARANCE_TIME_MS - (now - clearance_start_time)
            draw_countdown_timer(screen, time_left)

        elif current_state == STATE_GREEN:
            # Wenn Slow Mode (Leertaste) aktiv ist, zeichne die blinkende Schnecke
            if slow_walker_detected:
                draw_snail(screen, breath_alpha)
            
            # Ring zeichnen (Wenn slow_walker_detected, dann blinken ALLE aktiven Punkte)
            draw_led_ring(screen, led_counter, current_total_leds, STATE_GREEN, breath_alpha, is_slow_mode=slow_walker_detected, pulse_factor=pulse)
            
        else: # STATE_RED
            draw_crowd_image(screen, person_count)
            draw_led_ring(screen, led_counter, TOTAL_LEDS_RED, STATE_RED, 255)

        pygame.display.flip() 

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()