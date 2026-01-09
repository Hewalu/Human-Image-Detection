
class TrafficLightLogic:
    def __init__(self):
        # Zeit-Konfiguration für Auto-Ampel in Millisekunden
        # Diese Werte können angepasst werden, ohne die Punktezahl zu ändern
        self.t_start_buffer = 2000      # Beide Rot am Anfang (nach Fußgänger Grün)
        self.t_red_yellow = 1200        # Rot-Gelb Phase
        self.t_yellow = 2000            # Gelb Phase (vor Auto-Rot)
        self.t_end_buffer = 1000        # Beide Rot am Ende (vor Fußgänger Grün)
        
    def get_first_green_time_ms(self):
        """Gibt die Zeit in ms zurück, ab der die Autoampel Grün wird."""
        return self.t_start_buffer + self.t_red_yellow

    def calculate_lights(self, ped_state, elapsed_time_ms, total_red_duration_ms):
        """
        Berechnet den Zustand aller Lampen (zeitbasiert).
        
        Args:
            ped_state (str): "GREEN", "RED", "CLEARANCE", "TRAM"
            elapsed_time_ms (float): Vergangene Zeit in der aktuellen Phase
            total_red_duration_ms (float): Gesamtdauer der aktuellen Rot-Phase (nur relevant wenn ped_state="RED")
        """
        
        # Standard: Alles aus
        res = {
            "main_red": False, "main_green": False,
            "car_red": False, "car_yellow": False, "car_green": False
        }
        
        # 1. HAUPTAMPEL (Fußgänger)
        if ped_state == "GREEN":
            res["main_green"] = True
        else:
            res["main_red"] = True
            
        # 2. AUTOAMPEL LOGIK
        
        if ped_state == "GREEN":
            # Fußgänger Grün -> Autos Rot
            res["car_red"] = True
            
        elif ped_state == "CLEARANCE":
            # Fußgänger räumen -> Autos Rot (Sicherheitszeit)
            res["car_red"] = True
            
        elif ped_state == "RED":
            # Fußgänger Rot -> Auto Ampelphasen durchlaufen
            # Wir nutzen die absoluten Zeiten von Anfang und Ende der Phase
            
            # Zeitpunkte berechnen
            t = elapsed_time_ms
            total = total_red_duration_ms
            
            # Startsequenz
            t_green_start = self.t_start_buffer + self.t_red_yellow
            
            # Endsequenz (Rückwärts von Total)
            t_yellow_start = total - (self.t_yellow + self.t_end_buffer)
            t_red_exit_start = total - self.t_end_buffer
            
            # Sicherheitscheck: Falls Phase zu kurz für volle Sequenz, kürzen wir Grün
            if t_green_start > t_yellow_start:
                 # Phase extrem kurz -> Notfallverhalten (rot lassen oder gequetscht)
                 # Wir lassen einfach Rot, wenn kein Platz für Grün ist
                 res["car_red"] = True
            else:
                if t < self.t_start_buffer:
                    # Anfang: Alle Rot
                    res["car_red"] = True
                elif t < t_green_start:
                    # Rot-Gelb (Vorbereitung Grün) -> ACHTUNG: User wollte nur Gelb? 
                    # Vorhin war Änderung: "Nur Gelb, ohne Rot" für die Vorbereitunsphase?
                    # Standard in DE ist Rot+Gelb. User wollte "nur gelb" leuchten sehen.
                    # Wir übernehmen "Nur Gelb" wie zuletzt gewünscht.
                    res["car_yellow"] = True 
                    # Falls Rot doch an sein soll: res["car_red"] = True
                    
                elif t < t_yellow_start:
                    # Grün
                    res["car_green"] = True
                    
                elif t < t_red_exit_start:
                    # Gelb (Ende)
                    res["car_yellow"] = True
                    
                else:
                    # Ende: Alle Rot
                    res["car_red"] = True
                
        elif ped_state == "TRAM":
             res["car_red"] = True
             
        return res
