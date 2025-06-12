import pygame
import time
import math
import random
from src.tetris import TetrisBoard, TetrisPiece
from src.cards import CardManager

class TetrisGame:
    def __init__(self, screen, settings, player):
        self.screen = screen
        self.settings = settings
        self.player = player
        self.board = TetrisBoard()
        self.card_manager = CardManager()
        
        # Estado del juego
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.fall_timer = 0
        self.fall_timer_max = settings.fall_speed
        
        # Efectos de cartas
        self.score_multiplier = 1
        self.multiplier_timer = 0
        self.slow_time_timer = 0
        self.ghost_mode = False
        self.ghost_timer = 0
        self.gravity_reversed = False
        self.gravity_timer = 0
        self.time_frozen = False
        self.freeze_timer = 0
        self.golden_mode = False
        self.golden_timer = 0
        
        # Configuración visual mejorada
        self.cell_size = 35
        self.board_x = 80
        self.board_y = 80
        
        # Fuentes modernas
        self.font_large = pygame.font.Font(None, 42)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        
        # Efectos visuales
        self.particles = []
        self.line_clear_animation = []
        
        # Suavizado de animaciones
        self.smooth_anim = None
        self.line_clear_text = None  # (texto, timer, color, scale, rainbow)
        self.line_clear_particles = []
        self.hard_drop_particles = []
        self.confetti_particles = []
        self.last_speedup_time = pygame.time.get_ticks()
        self.speedup_interval = 30000  # 30 segundos
        self.speedup_amount = 60  # ms menos por nivel
        self.base_fall_speed = settings.fall_speed
        # --- Hold piece ---
        self.hold_piece = None
        self.hold_used = False
        # --- Movimiento rápido al holdear ---
        self.move_left_held = False
        self.move_right_held = False
        self.move_timer = 0
        self.move_delay = 10  # frames antes de repetir
        self.move_repeat = 2  # frames entre repeticiones
        
        # Generar cartas iniciales
        if settings.unlocked_cards:
            for _ in range(2):  # Empezar con 2 cartas
                self.card_manager.draw_card(settings.unlocked_cards)
    
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "menu"
            elif event.key == self.settings.controls['left']:
                self.board.move_piece(-1, 0)
                self.move_left_held = True
                self.move_timer = 0
            elif event.key == self.settings.controls['right']:
                self.board.move_piece(1, 0)
                self.move_right_held = True
                self.move_timer = 0
            elif event.key == self.settings.controls['down']:
                self.board.move_piece(0, 1)
            elif event.key == self.settings.controls['rotate'] or event.key == pygame.K_r:
                self.board.rotate_piece_clockwise()
            elif event.key == pygame.K_q:
                self.board.rotate_piece_counterclockwise()
            elif event.key == self.settings.controls['drop']:
                # Hard drop instantáneo y efecto de partículas
                if self.board.current_piece:
                    from_y = self.board.current_piece.y
                    to_y = self.board.ghost_y
                    self.board.current_piece.y = to_y
                    self.create_hard_drop_particles(self.board.current_piece)
                    self.board.drop_piece()
                    self.board.current_piece.lock_timer = 9999
                    self.board.update()
                return None
            elif event.key == pygame.K_1:
                self.card_manager.use_card(0, self)
            elif event.key == pygame.K_2:
                self.card_manager.use_card(1, self)
            elif event.key == pygame.K_3:
                self.card_manager.use_card(2, self)
            elif event.key == self.settings.controls.get('hold', pygame.K_c):
                self.handle_hold_piece()
        elif event.type == pygame.KEYUP:
            if event.key in [self.settings.controls['left'], pygame.K_a]:
                self.move_left_held = False
            elif event.key in [self.settings.controls['right'], pygame.K_d]:
                self.move_right_held = False
        return None
    
    def handle_hold_piece(self):
        if self.hold_used:
            return
        current = self.board.current_piece
        if current is None:
            return
        if self.hold_piece is None:
            # Guarda la pieza actual y saca la siguiente
            self.hold_piece = current
            self.board.current_piece = self.board.next_piece
            self.board.next_piece = TetrisPiece(random.choice(list(TetrisPiece.SHAPES.keys())), self.board.width // 2 - 1, 0)
        else:
            # Intercambia la pieza actual con la del hold
            temp = self.hold_piece
            self.hold_piece = current
            temp.x = self.board.width // 2 - 1
            temp.y = 0
            temp.rotation = 0
            temp.shape = temp.SHAPES[temp.type][0]
            self.board.current_piece = temp
        self.hold_used = True

    def update(self):
        # --- Movimiento rápido al holdear ---
        if self.move_left_held or self.move_right_held:
            self.move_timer += 1
            if self.move_timer > self.move_delay:
                if self.move_timer % self.move_repeat == 0:
                    if self.move_left_held:
                        self.board.move_piece(-1, 0)
                    if self.move_right_held:
                        self.board.move_piece(1, 0)
        else:
            self.move_timer = 0
        
        # Actualizar efectos de cartas
        self.update_card_effects()
        
        # Actualizar partículas
        self.update_particles()
        
        # Caída automática de piezas (si no está congelado)
        if not self.time_frozen:
            self.fall_timer += 16  # Aproximadamente 60 FPS
            if self.fall_timer >= self.fall_timer_max:
                self.fall_timer = 0
                result = self.board.update()
                if result == "game_over":
                    return "menu"
                elif isinstance(result, int) and result > 0:
                    self.handle_line_clear(result)
        
        # Reset hold_used cuando se coloca una pieza
        if self.board.current_piece is None and self.hold_used:
            self.hold_used = False
        # Aumenta la velocidad cada 30s
        now = pygame.time.get_ticks()
        if now - self.last_speedup_time > self.speedup_interval:
            self.last_speedup_time = now
            self.fall_timer_max = max(80, self.fall_timer_max - self.speedup_amount)
            self.settings.fall_speed = self.fall_timer_max
        
        # Smooth animation para drop
        if self.smooth_anim and self.board.current_piece:
            from_y, to_y, progress, duration = self.smooth_anim
            if progress < duration:
                interp_y = from_y + (to_y - from_y) * (progress + 1) / duration
                self.board.current_piece.y = int(interp_y)
                self.smooth_anim = (from_y, to_y, progress + 1, duration)
                return  # Pausa el update normal mientras anima
            else:
                self.board.current_piece.y = to_y
                self.board.drop_piece()
                self.board.current_piece.lock_timer = 9999
                self.board.update()
                self.smooth_anim = None
    
    def update_card_effects(self):
        """Actualiza todos los efectos activos de las cartas"""
        # Multiplicador de puntuación
        if self.multiplier_timer > 0:
            self.multiplier_timer -= 1
            if self.multiplier_timer <= 0:
                self.score_multiplier = 1
        
        # Tiempo lento
        if self.slow_time_timer > 0:
            self.slow_time_timer -= 1
            if self.slow_time_timer <= 0:
                self.fall_timer_max = self.settings.fall_speed
        
        # Modo fantasma
        if self.ghost_timer > 0:
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                self.ghost_mode = False
        
        # Gravedad invertida
        if self.gravity_timer > 0:
            self.gravity_timer -= 1
            if self.gravity_timer <= 0:
                self.gravity_reversed = False
        
        # Tiempo congelado
        if self.freeze_timer > 0:
            self.freeze_timer -= 1
            if self.freeze_timer <= 0:
                self.time_frozen = False
        
        # Modo dorado
        if self.golden_timer > 0:
            self.golden_timer -= 1
            if self.golden_timer <= 0:
                self.golden_mode = False
                if self.score_multiplier > 3:  # Solo resetear si es del modo dorado
                    self.score_multiplier = 1
    
    def handle_line_clear(self, lines_cleared):
        """Maneja la limpieza de líneas y efectos"""
        # Calcular puntos
        base_points = [0, 100, 300, 500, 800, 1200, 1600, 2000, 3000]
        idx = min(lines_cleared, len(base_points) - 1)
        points = base_points[idx] * self.level * self.score_multiplier

        # Bonus por modo dorado
        if self.golden_mode:
            points *= 2
            self.create_golden_particles()

        self.score += points
        self.lines_cleared += lines_cleared
        self.level = self.lines_cleared // 10 + 1

        # Efecto de texto y partículas según líneas
        line_names = [
            "SIMPLE", "DOBLE", "TRIPLE", "CUÁDRUPLE", "QUÍNTUPLE", "SÉXTUPLE", "SÉPTUPLE", "OCTUPLE", "MASTER TETRA"
        ]
        if lines_cleared >= 2:
            name = line_names[lines_cleared - 1] if lines_cleared - 1 < len(line_names) else f"x{lines_cleared}"
            color = [
                (200,255,200), (100,200,255), (255,180,180), (255,255,100),
                (255,140,0), (255,0,255), (0,255,255), (255,255,255), (255,255,255)
            ][lines_cleared - 1 if lines_cleared - 1 < 9 else -1]
            scale = 1.2 + (lines_cleared - 2) * 0.25
            rainbow = (lines_cleared >= 8)
            self.line_clear_text = (name, 90 + (lines_cleared - 2)*10, color, scale, rainbow)
            self.create_line_clear_particles(lines_cleared, color, lines_cleared - 2, rainbow)
            self.create_confetti(lines_cleared, rainbow)
            self.play_firework_sound()
            if lines_cleared >= 8:
                self.score += 5000

        # Si te quedas sin cartas en la mano, genera una nueva basada en tu inventario
        if len(self.card_manager.hand) == 0 and hasattr(self.settings, "unlocked_cards") and self.settings.unlocked_cards:
            self.card_manager.draw_card(self.settings.unlocked_cards)

    def create_line_clear_particles(self, lines_count, color=None, idx=0, rainbow=False):
        n_particles = lines_count * 30 + idx * 20
        for _ in range(n_particles):
            angle = random.uniform(-3.14, 3.14)
            speed = random.uniform(4 + idx*2, 12 + idx*4)
            if rainbow:
                color = self.get_rainbow_color(random.uniform(0, 1))
            self.line_clear_particles.append({
                'x': self.board_x + self.board.width * self.cell_size // 2,
                'y': self.board_y + self.board.height * self.cell_size // 2,
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle),
                'color': color,
                'life': 50 + lines_count * 8 + idx*10,
                'max_life': 50 + lines_count * 8 + idx*10
            })

    def create_confetti(self, lines, rainbow):
        for _ in range(40 + lines * 20):
            angle = random.uniform(-math.pi, math.pi)
            speed = random.uniform(3, 10 + lines * 2)
            color = self.get_rainbow_color(random.uniform(0, 1)) if rainbow else (
                random.randint(80, 255), random.randint(80, 255), random.randint(120, 255)
            )
            self.confetti_particles.append({
                'x': self.board_x + self.board.width * self.cell_size // 2,
                'y': self.board_y + 60,
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle) - 2,
                'color': color,
                'life': random.randint(30, 60),
                'max_life': 60
            })

    def play_firework_sound(self):
        try:
            pygame.mixer.Sound("firework.wav").play()
        except Exception:
            pass  # Si no existe el archivo, ignora

    def get_rainbow_color(self, t):
        t = t % 1.0
        r = int(255 * abs(math.sin(math.pi * t)))
        g = int(255 * abs(math.sin(math.pi * t + 2*math.pi/3)))
        b = int(255 * abs(math.sin(math.pi * t + 4*math.pi/3)))
        return (r, g, b)

    def update_particles(self):
        """Actualiza todas las partículas"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.2  # Gravedad
            particle['life'] -= 1
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
        
        # Actualiza partículas de líneas
        for particle in self.line_clear_particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.18 + 0.05 * (particle['max_life'] // 30)
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.line_clear_particles.remove(particle)
        for particle in self.confetti_particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.25
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.confetti_particles.remove(particle)
        # Actualiza partículas de hard drop
        for particle in self.hard_drop_particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.5
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.hard_drop_particles.remove(particle)
    
    def draw(self):
        # Fondo con gradiente
        self.draw_gradient_background()
        
        # Dibujar tablero
        self.draw_board()
        
        # Dibujar pieza fantasma
        if self.settings.show_ghost_piece and self.board.current_piece:
            self.draw_ghost_piece()
        
        # Dibujar pieza actual
        if self.board.current_piece:
            self.draw_piece(self.board.current_piece)
        
        # Dibujar siguiente pieza
        self.draw_next_piece()
        
        # Dibujar información del juego
        self.draw_game_info()
        
        # Dibujar cartas
        self.card_manager.draw_hand(self.screen, 500, 500)
        
        # Dibujar efectos activos
        self.draw_effects()
        
        # Dibujar partículas
        self.draw_particles()
        
        # Dibujar partículas de hard drop
        self.draw_hard_drop_particles()
        
        # Efectos de limpieza de líneas
        self.draw_line_clear_effect()
        self.draw_confetti()
        self.draw_hard_drop_particles()
    
    def draw_gradient_background(self):
        """Dibuja un fondo con gradiente dinámico"""
        height = self.screen.get_height()
        base_color = (15, 20, 35)
        
        if self.golden_mode:
            accent_color = (40, 35, 15)
        elif self.time_frozen:
            accent_color = (15, 35, 40)
        else:
            accent_color = (25, 15, 35)
        
        for y in range(height):
            ratio = y / height
            r = int(base_color[0] * (1 - ratio) + accent_color[0] * ratio)
            g = int(base_color[1] * (1 - ratio) + accent_color[1] * ratio)
            b = int(base_color[2] * (1 - ratio) + accent_color[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.screen.get_width(), y))
    
    def draw_board(self):
        # Fondo del tablero con efecto de profundidad
        board_width = self.board.width * self.cell_size
        board_height = self.board.height * self.cell_size
        
        # Sombra del tablero
        shadow_rect = pygame.Rect(self.board_x + 5, self.board_y + 5, board_width, board_height)
        pygame.draw.rect(self.screen, (10, 15, 25), shadow_rect, border_radius=10)
        
        # Fondo principal
        board_rect = pygame.Rect(self.board_x, self.board_y, board_width, board_height)
        pygame.draw.rect(self.screen, (30, 40, 60), board_rect, border_radius=10)
        
        # Líneas de la cuadrícula (opcionales)
        if self.settings.show_grid:
            grid_color = (50, 60, 80)
            for x in range(self.board.width + 1):
                pygame.draw.line(self.screen, grid_color,
                               (self.board_x + x * self.cell_size, self.board_y),
                               (self.board_x + x * self.cell_size, self.board_y + board_height))
            
            for y in range(self.board.height + 1):
                pygame.draw.line(self.screen, grid_color,
                               (self.board_x, self.board_y + y * self.cell_size),
                               (self.board_x + board_width, self.board_y + y * self.cell_size))
        
        # Dibujar bloques colocados con efectos
        for y in range(self.board.height):
            for x in range(self.board.width):
                if self.board.grid[y][x] is not None:
                    self.draw_block(x, y, self.board.grid[y][x])
    
    def draw_block(self, x, y, color, alpha=255):
        """Dibuja un bloque individual con efectos visuales"""
        cell_x = self.board_x + x * self.cell_size
        cell_y = self.board_y + y * self.cell_size
        
        # Crear superficie para efectos de alpha
        block_surf = pygame.Surface((self.cell_size - 2, self.cell_size - 2))
        block_surf.set_alpha(alpha)
        
        # Color base
        if self.golden_mode:
            # Efecto dorado
            golden_color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] // 2))
            block_surf.fill(golden_color)
        else:
            block_surf.fill(color)
        
        # Efecto de brillo en los bordes
        pygame.draw.rect(block_surf, (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 40)), 
                        (0, 0, self.cell_size - 2, 3))
        pygame.draw.rect(block_surf, (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 40)), 
                        (0, 0, 3, self.cell_size - 2))
        
        # Sombra interior
        pygame.draw.rect(block_surf, (max(0, color[0] - 40), max(0, color[1] - 40), max(0, color[2] - 40)), 
                        (self.cell_size - 5, self.cell_size - 5, 3, 3))
        
        self.screen.blit(block_surf, (cell_x + 1, cell_y + 1))
    
    def draw_ghost_piece(self):
        """Dibuja la pieza fantasma"""
        if self.board.current_piece:
            ghost_alpha = 80
            for x, y in self.board.current_piece.get_cells():
                ghost_y = y + (self.board.ghost_y - self.board.current_piece.y)
                if ghost_y >= 0 and ghost_y != y:  # No dibujar si coincide con la pieza actual
                    self.draw_block(x, ghost_y, self.board.current_piece.color, ghost_alpha)
    
    def draw_piece(self, piece):
        alpha = 128 if self.ghost_mode else 255
        
        for x, y in piece.get_cells():
            if y >= 0:
                self.draw_block(x, y, piece.color, alpha)
    
    def draw_next_piece(self):
        if self.board.next_piece:
            next_x = 500
            next_y = 120
            
            # Fondo de la sección
            bg_rect = pygame.Rect(next_x - 10, next_y - 40, 160, 120)
            pygame.draw.rect(self.screen, (40, 50, 70), bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, (80, 100, 130), bg_rect, 2, border_radius=8)
            
            # Título
            title = self.font_medium.render("SIGUIENTE", True, (255, 255, 255))
            self.screen.blit(title, (next_x, next_y - 35))
            
            # Pieza
            piece_start_x = next_x + 20
            piece_start_y = next_y
            
            for row_idx, row in enumerate(self.board.next_piece.shape):
                for col_idx, cell in enumerate(row):
                    if cell != '.' and cell != ' ':
                        cell_x = piece_start_x + col_idx * 25
                        cell_y = piece_start_y + row_idx * 25
                        
                        # Mini bloque con efectos
                        mini_surf = pygame.Surface((23, 23))
                        mini_surf.fill(self.board.next_piece.color)
                        
                        # Brillo
                        pygame.draw.rect(mini_surf, (min(255, self.board.next_piece.color[0] + 40), 
                                                   min(255, self.board.next_piece.color[1] + 40), 
                                                   min(255, self.board.next_piece.color[2] + 40)), 
                                       (0, 0, 23, 3))
                        pygame.draw.rect(mini_surf, (min(255, self.board.next_piece.color[0] + 40), 
                                                   min(255, self.board.next_piece.color[1] + 40), 
                                                   min(255, self.board.next_piece.color[2] + 40)), 
                                       (0, 0, 3, 23))
                        
                        self.screen.blit(mini_surf, (cell_x, cell_y))
    
    def draw_game_info(self):
        info_x = 500
        info_y = 260

        # Fondo de información
        info_bg = pygame.Rect(info_x - 10, info_y - 10, 200, 200)
        pygame.draw.rect(self.screen, (35, 45, 65), info_bg, border_radius=8)
        pygame.draw.rect(self.screen, (70, 90, 120), info_bg, 2, border_radius=8)

        info_texts = [
            f"Jugador: {self.player['name']}",
            f"Puntuación: {self.score:,}",
            f"Líneas: {self.lines_cleared}",
            f"Nivel: {self.level}",
            "",
            "CONTROLES:",
            "IZQ / DER / ARR / ABA - Mover/Rotar",
            "R - Rotar inverso",
            "ESPACIO - Caída rápida",
            "1, 2, 3 - Usar cartas"
        ]

        for i, text in enumerate(info_texts):
            if text == "":
                continue
            color = (255, 255, 255) if not text.startswith(("CONTROLES", "IZQ", "R", "ESPACIO", "1, 2, 3")) else (150, 200, 255)
            if text.startswith("CONTROLES"):
                color = (255, 200, 100)

            rendered = self.font_small.render(text, True, color)
            self.screen.blit(rendered, (info_x, info_y + i * 18))
    
    def draw_effects(self):
        effects_x = 50
        effects_y = 600
        
        active_effects = []
        
        if self.score_multiplier > 1:
            active_effects.append(f"Multiplicador x{self.score_multiplier} ({self.multiplier_timer//60 + 1}s)")
        
        if self.slow_time_timer > 0:
            active_effects.append(f"Tiempo Lento ({self.slow_time_timer//60 + 1}s)")
        
        if self.ghost_mode:
            active_effects.append(f"Modo Fantasma ({self.ghost_timer//60 + 1}s)")
        
        if self.gravity_reversed:
            active_effects.append(f"Gravedad Invertida ({self.gravity_timer//60 + 1}s)")
        
        if self.time_frozen:
            active_effects.append(f"Tiempo Congelado ({self.freeze_timer//60 + 1}s)")
        
        if self.golden_mode:
            active_effects.append(f"Modo Dorado ({self.golden_timer//60 + 1}s)")
        
        if active_effects:
            # Fondo para efectos
            effects_height = len(active_effects) * 25 + 20
            effects_bg = pygame.Rect(effects_x - 10, effects_y - 10, 300, effects_height)
            pygame.draw.rect(self.screen, (50, 30, 70), effects_bg, border_radius=8)
            pygame.draw.rect(self.screen, (150, 100, 200), effects_bg, 2, border_radius=8)
            
            title = self.font_medium.render("EFECTOS ACTIVOS", True, (255, 200, 255))
            self.screen.blit(title, (effects_x, effects_y - 5))
            
            for i, effect in enumerate(active_effects):
                color = (255, 255, 100) if "Multiplicador" in effect else (100, 255, 255)
                if "Dorado" in effect:
                    color = (255, 215, 0)
                
                rendered = self.font_small.render(effect, True, color)
                self.screen.blit(rendered, (effects_x, effects_y + 20 + i * 25))
    
    def draw_particles(self):
        """Dibuja todas las partículas activas"""
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            size = max(1, int(4 * (particle['life'] / particle['max_life'])))
            
            # Crear superficie con alpha
            particle_surf = pygame.Surface((size * 2, size * 2))
            particle_surf.set_alpha(alpha)
            particle_surf.fill(particle['color'])
            
            # Dibujar como círculo
            pygame.draw.circle(particle_surf, particle['color'], (size, size), size)
            self.screen.blit(particle_surf, (int(particle['x']), int(particle['y'])))
    
    def draw_hard_drop_particles(self):
        for particle in self.hard_drop_particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            size = max(2, int(4 * (particle['life'] / particle['max_life'])))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, particle['color'] + (alpha,), (size, size), size)
            self.screen.blit(surf, (int(particle['x']), int(particle['y'])))
    
    def draw_line_clear_effect(self):
        if self.line_clear_text:
            text, timer, color, scale, rainbow = self.line_clear_text
            font_size = int(90 * scale if timer > 30 else 70 * scale)
            font = pygame.font.Font(None, font_size)
            alpha = int(255 * min(1, timer / 90))
            if rainbow:
                surf = font.render(text, True, (255,255,255))
                for i in range(surf.get_width()):
                    c = self.get_rainbow_color((i / surf.get_width() + pygame.time.get_ticks()/1000)%1)
                    pygame.draw.line(surf, c, (i,0), (i,surf.get_height()))
                surf.set_alpha(alpha)
            else:
                surf = font.render(text, True, color)
                surf.set_alpha(alpha)
            rect = surf.get_rect(center=(self.board_x + self.board.width * self.cell_size // 2, self.board_y + 120))
            self.screen.blit(surf, rect)
            self.line_clear_text = (text, timer - 1, color, scale, rainbow) if timer > 0 else None

        for particle in self.line_clear_particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            size = max(3, int(8 * (particle['life'] / particle['max_life'])))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, particle['color'] + (alpha,), (size, size), size)
            self.screen.blit(surf, (int(particle['x']), int(particle['y'])))

    def draw_confetti(self):
        for particle in self.confetti_particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            size = max(2, int(6 * (particle['life'] / particle['max_life'])))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.rect(surf, particle['color'] + (alpha,), (0, 0, size*2, size*2))
            self.screen.blit(surf, (int(particle['x']), int(particle['y'])))

    def draw_hold_piece(self):
        if self.hold_piece:
            font = pygame.font.Font(None, 28)
            label = font.render("HOLD", True, (200, 200, 255))
            self.screen.blit(label, (self.board_x - 90, self.board_y + 10))
            # Dibuja la pieza en el hold
            shape = self.hold_piece.SHAPES[self.hold_piece.type][0]
            block_size = 22
            for row_idx, row in enumerate(shape):
                for col_idx, cell in enumerate(row):
                    if cell != '.' and cell != ' ':
                        cell_x = self.board_x - 80 + col_idx * block_size
                        cell_y = self.board_y + 40 + row_idx * block_size
                        pygame.draw.rect(self.screen, self.hold_piece.color, (cell_x, cell_y, block_size, block_size), border_radius=4)
                        pygame.draw.rect(self.screen, (255,255,255), (cell_x, cell_y, block_size, block_size), 2, border_radius=4)

    def create_hard_drop_particles(self, piece):
        """Crea partículas de impacto al hacer hard drop"""
        color = piece.color if hasattr(piece, "color") else (255, 255, 255)
        for x, y in piece.get_cells():
            if y >= self.board.height - 1 or (y + 1 < self.board.height and self.board.grid[y + 1][x] is not None):
                for _ in range(10):
                    self.hard_drop_particles.append({
                        'x': self.board_x + x * self.cell_size + self.cell_size // 2,
                        'y': self.board_y + (y + 1) * self.cell_size - 2,
                        'vx': random.uniform(-2, 2),
                        'vy': random.uniform(0, 3),
                        'color': color,
                        'life': 18,
                        'max_life': 18
                    })