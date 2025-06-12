import pygame
import math
import random
from src.tetris import TetrisBoard, TetrisPiece

class MenuButton:
    def __init__(self, text, x, y, width, height, action):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.action = action
        self.hovered = False
        self.font = pygame.font.Font(None, 48)
        
    def handle_event(self, event, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                return self.action
        return None
    
    def draw(self, screen, animation_time):
        # Colores dinámicos
        if self.hovered:
            bg_color = (60, 100, 160)
            text_color = (255, 255, 255)
            border_color = (100, 150, 255)
            scale = 1.05 + 0.02 * math.sin(animation_time * 0.2)
        else:
            bg_color = (40, 50, 70)
            text_color = (200, 200, 200)
            border_color = (80, 100, 130)
            scale = 1.0
        
        scaled_width = int(self.rect.width * scale)
        scaled_height = int(self.rect.height * scale)
        scaled_x = self.rect.centerx - scaled_width // 2
        scaled_y = self.rect.centery - scaled_height // 2
        scaled_rect = pygame.Rect(scaled_x, scaled_y, scaled_width, scaled_height)
        
        shadow_rect = scaled_rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 15, 25), shadow_rect, border_radius=10)
        
        pygame.draw.rect(screen, bg_color, scaled_rect, border_radius=10)
        pygame.draw.rect(screen, border_color, scaled_rect, 3, border_radius=10)
        
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=scaled_rect.center)
        screen.blit(text_surface, text_rect)

class MainMenu:
    def __init__(self, screen, settings, music_manager=None):
        self.screen = screen
        self.settings = settings
        self.animation_time = 0
        self.music_manager = music_manager  # Nuevo: referencia al music_manager

        # Fuentes modernas
        self.font_title = pygame.font.Font(None, 96)
        self.font_subtitle = pygame.font.Font(None, 48)
        self.font_info = pygame.font.Font(None, 28)
        
        # Colores naturales
        self.bg_gradient_top = (25, 35, 55)
        self.bg_gradient_bottom = (15, 20, 35)
        self.title_color = (255, 255, 255)
        self.subtitle_color = (100, 150, 255)
        self.accent_color = (80, 150, 200)
        
        # Crear botones
        button_width = 300
        button_height = 60
        button_spacing = 80
        start_y = 350
        center_x = screen.get_width() // 2

        self.buttons = [
            MenuButton("JUGAR", center_x - button_width//2, start_y, button_width, button_height, "play"),
            MenuButton("CARTAS", center_x - button_width//2, start_y + button_spacing, button_width, button_height, "cards"),
            MenuButton("CONFIGURACIÓN", center_x - button_width//2, start_y + button_spacing*2, button_width, button_height, "settings"),
            MenuButton("SALIR", center_x - button_width//2, start_y + button_spacing*3, button_width, button_height, "quit")
        ]
        
        self.floating_tetrominos = []
        self.init_floating_tetrominos()
        self.dragging_idx = None
        self.drag_offset = (0, 0)
        # NEW: posición y estado de arrastre del reproductor
        self.music_player_pos = [20, screen.get_height() - 80]  # Posición inicial
        self.dragging_music_player = False
        self.drag_offset = (0, 0)

    def init_floating_tetrominos(self):
        # Crea piezas de tetris flotando con posiciones y velocidades aleatorias
        self.floating_tetrominos = []
        piece_types = list(TetrisPiece.SHAPES.keys())
        for _ in range(10):
            piece_type = random.choice(piece_types)
            color = self.get_marina_color(piece_type, 0)
            self.floating_tetrominos.append({
                "type": piece_type,
                "x": random.randint(60, self.screen.get_width() - 120),
                "y": random.randint(60, self.screen.get_height() - 250),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.1, 0.1),
                "angle": random.uniform(0, 2 * math.pi),
                "va": random.uniform(-0.01, 0.01),
                "color": color,
                "size": random.randint(32, 48),
                "color_phase": random.uniform(0, 1000)
            })

    def get_marina_color(self, piece_type, t):
        # Colores marinos alternando con la música (bpm)
        bpm = 120
        if self.music_manager:
            bpm = self.music_manager.get_current_bpm(default=120)
        phase = t * 0.02 + bpm * 0.001
        # Marino: azul profundo, verde mar, cian, azul oscuro
        base_colors = [
            (20, 40, 80),   # azul marino
            (30, 80, 100),  # verde mar
            (40, 120, 160), # cian marino
            (10, 30, 60)    # azul oscuro
        ]
        idx = hash(piece_type) % len(base_colors)
        r, g, b = base_colors[idx]
        # Oscila el color suavemente
        osc = 40 * math.sin(phase + idx)
        r = max(0, min(255, int(r + osc)))
        g = max(0, min(255, int(g + osc * 0.7)))
        b = max(0, min(255, int(b + osc * 1.2)))
        return (r, g, b)

    def handle_event(self, event, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        # --- Reproductor de música draggable ---
        music_rect = pygame.Rect(self.music_player_pos[0], self.music_player_pos[1], 320, 54)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if music_rect.collidepoint(mouse_pos):
                self.dragging_music_player = True
                self.drag_offset = (
                    mouse_pos[0] - self.music_player_pos[0],
                    mouse_pos[1] - self.music_player_pos[1]
                )
            # Interacción con piezas flotantes
            else:
                mx, my = mouse_pos
                for idx, block in reversed(list(enumerate(self.floating_tetrominos))):
                    if self.tetromino_hit_test(block, mx, my):
                        self.dragging_idx = idx
                        self.drag_offset = (mx - block["x"], my - block["y"])
                        break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_music_player = False
            self.dragging_idx = None
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_music_player:
                self.music_player_pos[0] = mouse_pos[0] - self.drag_offset[0]
                self.music_player_pos[1] = mouse_pos[1] - self.drag_offset[1]
                # Mantener dentro de la pantalla
                self.music_player_pos[0] = max(0, min(self.music_player_pos[0], 
                    self.screen.get_width() - 320))
                self.music_player_pos[1] = max(0, min(self.music_player_pos[1], 
                    self.screen.get_height() - 54))
            if self.dragging_idx is not None:
                mx, my = mouse_pos
                block = self.floating_tetrominos[self.dragging_idx]
                block["x"] = mx - self.drag_offset[0]
                block["y"] = my - self.drag_offset[1]
                for i, other in enumerate(self.floating_tetrominos):
                    if i != self.dragging_idx and self.tetromino_overlap(block, other):
                        block["vx"], other["vx"] = -block["vx"], -other["vx"]
                        block["vy"], other["vy"] = -block["vy"], -other["vy"]
        # --- Botones del menú ---
        for button in self.buttons:
            result = button.handle_event(event, mouse_pos)
            if result:
                return result
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return "play"
            elif event.key == pygame.K_ESCAPE:
                return "menu"  # Asegura volver al menú principal
        return None

    def tetromino_hit_test(self, block, mx, my):
        # Hit test para la pieza flotante (bounding box)
        size = block["size"] * 2
        return (block["x"] - size//2 < mx < block["x"] + size//2 and
                block["y"] - size//2 < my < block["y"] + size//2)

    def tetromino_overlap(self, a, b):
        # Colisión simple por bounding box
        size_a = a["size"] * 2
        size_b = b["size"] * 2
        return (abs(a["x"] - b["x"]) < (size_a + size_b)//2 and
                abs(a["y"] - b["y"]) < (size_a + size_b)//2)

    def draw(self, current_player=None):
        self.animation_time += 1

        # Fondo con gradiente
        self.draw_gradient_background()

        # Piezas de Tetris flotantes
        self.draw_floating_tetrominos()

        # Título principal con efecto
        self.draw_title()

        # Botones
        for button in self.buttons:
            button.draw(self.screen, self.animation_time)

        # Información del jugador
        if current_player:
            self.draw_player_info(current_player)

        # Versión
        version_text = self.font_info.render("Natural Edition v2.0", True, (100, 100, 100))
        self.screen.blit(version_text, (20, self.screen.get_height() - 30))

        # Dibuja el reproductor de música en la esquina inferior izquierda
        self.draw_music_player()

    def draw_gradient_background(self):
        """Dibuja un fondo con gradiente suave"""
        height = self.screen.get_height()
        for y in range(height):
            ratio = y / height
            r = int(self.bg_gradient_top[0] * (1 - ratio) + self.bg_gradient_bottom[0] * ratio)
            g = int(self.bg_gradient_top[1] * (1 - ratio) + self.bg_gradient_bottom[1] * ratio)
            b = int(self.bg_gradient_top[2] * (1 - ratio) + self.bg_gradient_bottom[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.screen.get_width(), y))
    
    def draw_floating_tetrominos(self):
        t = self.animation_time
        for block in self.floating_tetrominos:
            # Movimiento solo si no está siendo arrastrado
            if self.dragging_idx is None or self.floating_tetrominos[self.dragging_idx] is not block:
                block["x"] += block["vx"]
                block["y"] += block["vy"]
                block["angle"] += block["va"]
                # Rebote en bordes
                if block["x"] < 30 or block["x"] > self.screen.get_width() - 90:
                    block["vx"] *= -1
                if block["y"] < 30 or block["y"] > self.screen.get_height() - 120:
                    block["vy"] *= -1
            # Color marino animado según la música
            block["color"] = self.get_marina_color(block["type"], t + block["color_phase"])
            # Dibuja la pieza de tetris flotando
            self.draw_tetromino(block["type"], block["x"], block["y"], block["size"], block["angle"], block["color"])

    def draw_tetromino(self, piece_type, x, y, size, angle, color):
        # Dibuja la pieza de tetris en (x, y) con rotación y color
        shape = TetrisPiece.SHAPES[piece_type][0]
        block_size = size // len(shape)
        surf_size = block_size * len(shape)
        surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        for row_idx, row in enumerate(shape):
            for col_idx, cell in enumerate(row):
                if cell != '.' and cell != ' ':
                    rect = pygame.Rect(col_idx * block_size, row_idx * block_size, block_size, block_size)
                    pygame.draw.rect(surf, color, rect, border_radius=4)
                    pygame.draw.rect(surf, (255,255,255,60), rect, 2, border_radius=4)
        # Rotar la superficie
        rotated = pygame.transform.rotate(surf, math.degrees(angle))
        rect = rotated.get_rect(center=(int(x), int(y)))
        self.screen.blit(rotated, rect)

    def draw_title(self):
        """Dibuja el título con efectos visuales sincronizados al BPM de la música"""
        # --- Sincronización con BPM ---
        bpm = 120  # Valor por defecto
        if self.music_manager:
            bpm = self.music_manager.get_current_bpm(default=120)
        # Calcula el tiempo de beat en frames (asumiendo 60 FPS)
        beat_time = 60 * 60 / bpm if bpm > 0 else 60
        # Oscilación sincronizada al beat
        beat_phase = (self.animation_time % beat_time) / beat_time
        scale = 1 + 0.06 * (0.5 - abs(beat_phase - 0.5))  # Pulso triangular

        # Título principal
        title_font = pygame.font.Font(None, int(96 * scale))
        title = title_font.render("TETRACARDS SAGA", True, self.title_color)

        # Sombra del título
        shadow = title_font.render("TETRACARDS SAGA", True, (50, 50, 50))
        shadow_rect = shadow.get_rect(center=(self.screen.get_width()//2 + 3, 120 + 3))
        self.screen.blit(shadow, shadow_rect)

        # Título principal
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 120))
        self.screen.blit(title, title_rect)

        # Subtítulo con efecto de color
        hue_shift = math.sin(self.animation_time * 0.01) * 50
        subtitle_color = (
            max(50, min(255, int(self.subtitle_color[0] + hue_shift))),
            max(50, min(255, int(self.subtitle_color[1] + hue_shift))),
            max(50, min(255, int(self.subtitle_color[2] + hue_shift)))
        )

        subtitle = self.font_subtitle.render("Natural Edition", True, subtitle_color)
        subtitle_rect = subtitle.get_rect(center=(self.screen.get_width()//2, 180))
        self.screen.blit(subtitle, subtitle_rect)

        # Línea decorativa
        line_width = int(200 + 50 * math.sin(self.animation_time * 0.03))
        line_y = 210
        line_start = self.screen.get_width()//2 - line_width//2
        line_end = self.screen.get_width()//2 + line_width//2

        for i in range(3):
            alpha = 255 - i * 80
            line_surf = pygame.Surface((line_width, 2))
            line_surf.set_alpha(alpha)
            line_surf.fill(self.accent_color)
            self.screen.blit(line_surf, (line_start, line_y + i))

    def draw_player_info(self, player):
        """Dibuja información del jugador actual"""
        info_x = self.screen.get_width() - 300
        info_y = 50
        
        # Fondo semi-transparente
        info_bg = pygame.Surface((280, 150))
        info_bg.set_alpha(180)
        info_bg.fill((20, 30, 50))
        self.screen.blit(info_bg, (info_x, info_y))
        
        # Borde
        pygame.draw.rect(self.screen, self.accent_color, (info_x, info_y, 280, 150), 2, border_radius=10)
        
        # Información del jugador
        info_texts = [
            f"Jugador: {player['name']}",
            f"Puntuación Total: {player['total_score']:,}",
            f"Mejor Puntuación: {player.get('best_score', 0):,}",
            f"Cartas: {len(player.get('unlocked_cards', []))}/18",
            f"Partidas: {player.get('games_played', 0)}"
        ]
        
        for i, text in enumerate(info_texts):
            rendered = self.font_info.render(text, True, (255, 255, 255))
            self.screen.blit(rendered, (info_x + 10, info_y + 10 + i * 25))

    def draw_music_player(self):
        """Dibuja el reproductor de música en su posición actual"""
        x, y = self.music_player_pos
        width = 320
        height = 54
        
        # Dibuja el fondo del reproductor
        pygame.draw.rect(self.screen, (30, 40, 60), (x, y, width, height), border_radius=10)
        pygame.draw.rect(self.screen, (80, 100, 130), (x, y, width, height), 2, border_radius=10)
        
        btn_size = 36
        btn_y = y + (height - btn_size) // 2
        btn_prev = pygame.Rect(x + 10, btn_y, btn_size, btn_size)
        btn_next = pygame.Rect(x + 60, btn_y, btn_size, btn_size)
        pygame.draw.rect(self.screen, (60, 80, 120), btn_prev, border_radius=8)
        pygame.draw.rect(self.screen, (60, 80, 120), btn_next, border_radius=8)
        pygame.draw.polygon(self.screen, (255,255,255), [
            (btn_prev.x + 26, btn_prev.y + 8),
            (btn_prev.x + 12, btn_prev.y + 18),
            (btn_prev.x + 26, btn_prev.y + 28)
        ])
        pygame.draw.polygon(self.screen, (255,255,255), [
            (btn_next.x + 10, btn_next.y + 8),
            (btn_next.x + 24, btn_next.y + 18),
            (btn_next.x + 10, btn_next.y + 28)
        ])
        if self.music_manager:
            current_song = self.music_manager.get_current_song() or "Sin Música"
        else:
            current_song = "No MusicManager"
        font = pygame.font.Font(None, 28)
        song_text = font.render(current_song, True, (255,255,255))
        self.screen.blit(song_text, (x + 110, y + (height - song_text.get_height()) // 2))