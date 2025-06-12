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
        self.combo_bonus_text = None # (texto, timer, color, scale, rainbow)
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
            
        # Nuevo: Bonus adicional por múltiples líneas (2+)
        if lines_cleared >= 2:
            combo_bonus = 200 * (lines_cleared - 1) * self.level
            points += combo_bonus
            self.show_combo_bonus_text(combo_bonus)

        # ARREGLO: sumar puntos aunque sea una sola línea
        self.score += int(points)
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
        # Más confeti para más líneas
        particle_count = 40 + lines * 30
        
        for _ in range(particle_count):
            angle = random.uniform(-math.pi, math.pi)
            speed = random.uniform(3, 10 + lines * 2)
            
            if rainbow:
                color = self.get_rainbow_color(random.uniform(0, 1))
            elif lines >= 4:
                color_options = [
                    (255, 215, 0), (255, 100, 100), (100, 255, 100),
                    (100, 100, 255), (255, 255, 100)
                ]
                color = random.choice(color_options)
            else:
                color = (random.randint(80, 255), random.randint(80, 255), random.randint(120, 255))
            
            size_factor = 1.0 + (lines >= 4) * 0.5
            
            self.confetti_particles.append({
                'x': self.board_x + self.board.width * self.cell_size // 2,
                'y': self.board_y + 60,
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle) - 2,
                'color': color,
                'life': random.randint(30, 60 + lines * 5),
                'max_life': 60 + lines * 5,
                'size': random.uniform(2, 6) * size_factor
            })

    def play_firework_sound(self):
        try:
            pygame.mixer.Sound("firework.wav").play()
        except Exception:
            pass

    def get_rainbow_color(self, t):
        t = t % 1.0
        r = int(255 * abs(math.sin(math.pi * t)))
        g = int(255 * abs(math.sin(math.pi * t + 2*math.pi/3)))
        b = int(255 * abs(math.sin(math.pi * t + 4*math.pi/3)))
        return (r, g, b)

    def show_combo_bonus_text(self, bonus_points):
        """Muestra un texto de bonus por combo"""
        text = f"+{int(bonus_points)} COMBO!"
        color = (255, 220, 100)
        self.combo_bonus_text = (text, 60, color, 1.0, False)
    
    def update_particles(self):
        """Actualiza todas las partículas"""
        for particles_list in [self.particles, self.line_clear_particles, self.confetti_particles, self.hard_drop_particles]:
            for particle in particles_list[:]:
                particle['x'] += particle.get('vx', 0)
                particle['y'] += particle.get('vy', 0)
                particle['vy'] += particle.get('gravity', 0.2)
                particle['life'] -= 1
                if particle['life'] <= 0:
                    particles_list.remove(particle)
        
        # Actualizar texto de bonus
        if hasattr(self, 'combo_bonus_text') and self.combo_bonus_text:
            text, timer, color, scale, rainbow = self.combo_bonus_text
            if timer > 0:
                self.combo_bonus_text = (text, timer - 1, color, scale, rainbow)
            else:
                self.combo_bonus_text = None
    
    def draw(self):
        self.draw_gradient_background()
        self.draw_board()
        if self.settings.show_ghost_piece and self.board.current_piece:
            self.draw_ghost_piece()
        if self.board.current_piece:
            self.draw_piece(self.board.current_piece)
        self.draw_next_piece()
        self.draw_game_info()
        self.card_manager.draw_hand(self.screen, 500, 500)
        self.draw_effects()
        self.draw_particles()
        self.draw_hard_drop_particles()
        self.draw_line_clear_effect()
        self.draw_confetti()
    
    def draw_gradient_background(self):
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
        board_width = self.board.width * self.cell_size
        board_height = self.board.height * self.cell_size
        shadow_rect = pygame.Rect(self.board_x + 5, self.board_y + 5, board_width, board_height)
        pygame.draw.rect(self.screen, (10, 15, 25), shadow_rect, border_radius=10)
        board_rect = pygame.Rect(self.board_x, self.board_y, board_width, board_height)
        pygame.draw.rect(self.screen, (30, 40, 60), board_rect, border_radius=10)
        if self.settings.show_grid:
            grid_color = (50, 60, 80)
            for x in range(self.board.width + 1):
                pygame.draw.line(self.screen, grid_color, (self.board_x + x * self.cell_size, self.board_y), (self.board_x + x * self.cell_size, self.board_y + board_height))
            for y in range(self.board.height + 1):
                pygame.draw.line(self.screen, grid_color, (self.board_x, self.board_y + y * self.cell_size), (self.board_x + board_width, self.board_y + y * self.cell_size))
        for y in range(self.board.height):
            for x in range(self.board.width):
                if self.board.grid[y][x] is not None:
                    self.draw_block(x, y, self.board.grid[y][x])
    
    def draw_block(self, x, y, color, alpha=255):
        cell_x = self.board_x + x * self.cell_size
        cell_y = self.board_y + y * self.cell_size
        block_surf = pygame.Surface((self.cell_size - 2, self.cell_size - 2), pygame.SRCALPHA)
        block_surf.set_alpha(alpha)
        base_color = color
        if self.golden_mode:
            base_color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] // 2))
        block_surf.fill(base_color)
        bright_color = tuple(min(255, c + 40) for c in base_color)
        pygame.draw.rect(block_surf, bright_color, (0, 0, self.cell_size - 2, 3))
        pygame.draw.rect(block_surf, bright_color, (0, 0, 3, self.cell_size - 2))
        self.screen.blit(block_surf, (cell_x + 1, cell_y + 1))

    def draw_next_piece(self):
        if self.board.next_piece:
            next_x, next_y = 500, 120
            bg_rect = pygame.Rect(next_x - 10, next_y - 40, 160, 120)
            pygame.draw.rect(self.screen, (40, 50, 70), bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, (80, 100, 130), bg_rect, 2, border_radius=8)
            title = self.font_medium.render("SIGUIENTE", True, (255, 255, 255))
            self.screen.blit(title, (next_x, next_y - 35))
            # Dibuja la pieza siguiente con su color real
            piece = self.board.next_piece
            shape = piece.shape
            color = piece.color
            for row_idx, row in enumerate(shape):
                for col_idx, cell in enumerate(row):
                    if cell != '.' and cell != ' ':
                        mini_surf = pygame.Surface((23, 23), pygame.SRCALPHA)
                        mini_surf.fill(color)
                        pygame.draw.rect(mini_surf, tuple(min(255, c + 40) for c in color), (0, 0, 23, 3))
                        pygame.draw.rect(mini_surf, tuple(min(255, c + 40) for c in color), (0, 0, 3, 23))
                        self.screen.blit(mini_surf, (next_x + 20 + col_idx * 25, next_y + row_idx * 25))

    def draw_game_info(self):
        info_x, info_y = 500, 260
        info_bg = pygame.Rect(info_x - 10, info_y - 10, 220, 200)
        pygame.draw.rect(self.screen, (35, 45, 65), info_bg, border_radius=8)
        pygame.draw.rect(self.screen, (70, 90, 120), info_bg, 2, border_radius=8)
        info_texts = [f"Jugador: {self.player['name']}", f"Puntuación: {self.score:,}", f"Líneas: {self.lines_cleared}", f"Nivel: {self.level}", "", "CONTROLES:", "IZQ/DER/ARR/ABA - Mover/Rotar", "ESPACIO - Caída rápida", "1,2,3 - Usar cartas"]
        for i, text in enumerate(info_texts):
            color = (255, 200, 100) if text.startswith("CONTROLES") else (150, 200, 255) if any(k in text for k in ["IZQ","ESPACIO","1,2,3"]) else (255, 255, 255)
            self.screen.blit(self.font_small.render(text, True, color), (info_x, info_y + i * 20))
    
    def draw_effects(self):
        effects_x, effects_y = 50, 600
        active_effects = []
        if self.score_multiplier > 1: active_effects.append(f"Multiplicador x{self.score_multiplier} ({self.multiplier_timer//60 + 1}s)")
        if self.slow_time_timer > 0: active_effects.append(f"Tiempo Lento ({self.slow_time_timer//60 + 1}s)")
        if self.ghost_mode: active_effects.append(f"Modo Fantasma ({self.ghost_timer//60 + 1}s)")
        if self.gravity_reversed: active_effects.append(f"Gravedad Invertida ({self.gravity_timer//60 + 1}s)")
        if self.time_frozen: active_effects.append(f"Tiempo Congelado ({self.freeze_timer//60 + 1}s)")
        if self.golden_mode: active_effects.append(f"Modo Dorado ({self.golden_timer//60 + 1}s)")
        if active_effects:
            effects_bg = pygame.Rect(effects_x - 10, effects_y - 10, 300, len(active_effects) * 25 + 40)
            pygame.draw.rect(self.screen, (50, 30, 70), effects_bg, border_radius=8)
            pygame.draw.rect(self.screen, (150, 100, 200), effects_bg, 2, border_radius=8)
            self.screen.blit(self.font_medium.render("EFECTOS ACTIVOS", True, (255, 200, 255)), (effects_x, effects_y))
            for i, effect in enumerate(active_effects):
                self.screen.blit(self.font_small.render(effect, True, (255,215,0) if "Dorado" in effect else (255,255,100) if "Multiplicador" in effect else (100,255,255)), (effects_x, effects_y + 30 + i * 25))

    def draw_particles(self):
        for p in self.particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            size = max(1, int(4 * (p['life'] / p['max_life'])))
            pygame.draw.circle(self.screen, p['color'] + (alpha,), (int(p['x']), int(p['y'])), size)

    def draw_hard_drop_particles(self):
        for p in self.hard_drop_particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            size = max(2, int(4 * (p['life'] / p['max_life'])))
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, p['color'] + (alpha,), (size,size), size)
            self.screen.blit(surf, (int(p['x']), int(p['y'])))
    
    def draw_line_clear_effect(self):
        if self.line_clear_text:
            text, timer, color, scale, rainbow = self.line_clear_text
            font_size = int(90 * scale * (0.5 + abs(0.5 - timer/90)))
            font = pygame.font.Font(None, font_size)
            alpha = int(255 * min(1, timer / 45))
            surf = font.render(text, True, self.get_rainbow_color(pygame.time.get_ticks()/1000) if rainbow else color)
            surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(self.board_x + self.board.width*self.cell_size//2, self.board_y + 120)))
            if timer-1 <= 0: self.line_clear_text = None 
            else: self.line_clear_text = (text, timer-1, color, scale, rainbow)

    def draw_confetti(self):
        for p in self.confetti_particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            size = max(2, int(p.get('size', 6) * (p['life'] / p['max_life'])))
            pygame.draw.rect(self.screen, p['color'] + (alpha,), (int(p['x']), int(p['y']), size, size))
        if hasattr(self, 'combo_bonus_text') and self.combo_bonus_text:
            text, timer, color, scale, _ = self.combo_bonus_text
            if timer > 0:
                font = pygame.font.Font(None, int(36 * scale))
                alpha = int(255 * min(1, timer / 30))
                surf = font.render(text, True, color)
                surf.set_alpha(alpha)
                y_pos = self.board_y + 170
                if self.line_clear_text:
                    y_pos = self.board_y + 120 + 45 + 20
                self.screen.blit(surf, surf.get_rect(center=(self.board_x + self.board.width * self.cell_size // 2, y_pos)))

    def create_hard_drop_particles(self, piece):
        color = piece.color
        for x, y in piece.get_cells():
            if y + 1 >= self.board.height or self.board.grid[y + 1][x]:
                for _ in range(10):
                    self.hard_drop_particles.append({'x': self.board_x + x * self.cell_size + self.cell_size // 2, 'y': self.board_y + (y+1) * self.cell_size - 2, 'vx': random.uniform(-2,2), 'vy': random.uniform(0,3), 'color': color, 'life': 18, 'max_life': 18, 'gravity': 0.5})

    def draw_ghost_piece(self):
        """Dibuja la pieza fantasma en el tablero"""
        if self.board.current_piece:
            ghost_alpha = 80
            for x, y in self.board.current_piece.get_cells():
                ghost_y = y + (self.board.ghost_y - self.board.current_piece.y)
                if ghost_y >= 0 and ghost_y != y:
                    self.draw_block(x, ghost_y, self.board.current_piece.color, ghost_alpha)

    def draw_piece(self, piece):
        """Dibuja la pieza actual en el tablero"""
        alpha = 128 if self.ghost_mode else 255
        for x, y in piece.get_cells():
            if y >= 0:
                self.draw_block(x, y, piece.color, alpha)