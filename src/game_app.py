import pygame
import sys
from enum import Enum
from src.menu import MainMenu
from src.game import TetrisGame
from src.settings import Settings
from src.music_manager import MusicManager
from src.player_manager import PlayerManager
from src.tetris import TetrisBoard, TetrisPiece

class GameState(Enum):
    MENU = 1
    PLAYING = 2
    SETTINGS = 3
    CARDS = 4
    PLAYER_SELECT = 5

class GameApp:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.settings = Settings()
        self.screen = pygame.display.set_mode(self.settings.resolution)
        pygame.display.set_caption("Tetracards Saga - Natural Edition")
        self.clock = pygame.time.Clock()
        self.state = GameState.PLAYER_SELECT
        self.music_manager = MusicManager()
        self.player_manager = PlayerManager()
        self.menu = MainMenu(self.screen, self.settings, music_manager=self.music_manager)
        self.tetris_game = None
        self.current_player = None
        self.debug_menu = False
        self.debug_card_hover = None  # (section, idx) o None
        self.fullscreen = False
        self.loading = False
        self.dev_mode = False
        self.last_card_click = {}  # dict to track last click time per card index

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.current_player:
                    self.player_manager.save_player_data(self.current_player)
                return False

            # Activar modo DEV con ctrl+shift+d
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_SHIFT) and event.key == pygame.K_d:
                    self.dev_mode = True
                    # Agregar temporalmente "(DEV)" al nombre del jugador
                    if self.current_player and "(DEV)" not in self.current_player["name"]:
                        self.current_player["name"] += " (DEV)"
            # For CARDS state, corregir ESC para volver al menú
            if self.state == GameState.CARDS:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = GameState.MENU
                # Procesar clics en el menú de cartas
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    current_time = pygame.time.get_ticks()
                    if hasattr(self.menu, "debug_card_rects") and self.menu.debug_card_rects:
                        for rect, card_idx in self.menu.debug_card_rects:
                            if rect.collidepoint(mouse_pos):
                                last_click = self.last_card_click.get(card_idx, 0)
                                if current_time - last_click < 400:  # doble click en 400 ms
                                    # Mostrar demostración de la carta
                                    if card_idx in self.current_player.get("unlocked_cards", []):
                                        self.show_card_demo(card_idx)
                                        self.create_double_click_effect(rect.center)
                                    else:
                                        self.show_error_message("No la desbloqueaste")
                                    self.last_card_click[card_idx] = 0
                                else:
                                    # Simple click: alterna el bloqueo en modo debug
                                    if self.debug_menu and self.current_player:
                                        if card_idx in self.current_player["unlocked_cards"]:
                                            self.current_player["unlocked_cards"].remove(card_idx)
                                        else:
                                            self.current_player["unlocked_cards"].append(card_idx)
                                    self.last_card_click[card_idx] = current_time
            if self.state == GameState.PLAYER_SELECT:
                # Solo reproducir la música de pre-menu si no está sonando
                if not self.music_manager.get_current_song() or not self.music_manager.get_current_song().lower().startswith("premenu"):
                    self.music_manager.play_premenu_music()
                result = self.handle_player_select_events(event)
                if result:
                    self.current_player = result
                    self.settings.load_player_data(result)
                    self.state = GameState.MENU
                    # Solo aquí inicia la música de menú
                    self.music_manager.play_menu_music()

            elif self.state == GameState.MENU:
                # Cambia música si es necesario
                if not self.music_manager.get_current_song() or not self.music_manager.get_current_song().lower().startswith("menu"):
                    self.music_manager.play_menu_music()
                # --- Manejo de reproductor de música de menú ---
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if hasattr(self.menu, "music_player_btn_prev") and self.menu.music_player_btn_prev.collidepoint(mouse_pos):
                        idx = self.music_manager.get_menu_song_index()
                        menu_songs = self.music_manager.get_menu_songs()
                        if menu_songs:
                            idx = (idx - 1) % len(menu_songs)
                            self.music_manager.play_menu_song_by_index(idx)
                    elif hasattr(self.menu, "music_player_btn_next") and self.menu.music_player_btn_next.collidepoint(mouse_pos):
                        idx = self.music_manager.get_menu_song_index()
                        menu_songs = self.music_manager.get_menu_songs()
                        if menu_songs:
                            idx = (idx + 1) % len(menu_songs)
                            self.music_manager.play_menu_song_by_index(idx)
                action = self.menu.handle_event(event, mouse_pos)
                if action == "play":
                    self.start_game_with_loading()
                elif action == "settings":
                    self.state = GameState.SETTINGS
                elif action == "cards":
                    self.state = GameState.CARDS
                elif action == "quit":
                    if self.current_player:
                        self.player_manager.save_player_data(self.current_player)
                    return False
            
            elif self.state == GameState.PLAYING:
                # Cambia música si es necesario
                if (self.music_manager.get_current_song() and
                    self.music_manager.get_current_song().lower().startswith("menu")):
                    self.music_manager.play_ingame_music()
                if self.tetris_game:
                    result = self.tetris_game.handle_event(event)
                    if result == "menu":
                        # Actualizar datos del jugador
                        self.current_player['total_score'] += self.tetris_game.score
                        self.current_player['games_played'] += 1
                        if self.tetris_game.score > self.current_player.get('best_score', 0):
                            self.current_player['best_score'] = self.tetris_game.score
                        
                        self.check_card_unlocks()
                        self.player_manager.save_player_data(self.current_player)
                        self.settings.load_player_data(self.current_player)
                        self.state = GameState.MENU
            
            elif self.state == GameState.SETTINGS:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = GameState.MENU
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.handle_settings_click(mouse_pos):
                        pass
                    # Botón de pantalla completa
                    fullscreen_btn = pygame.Rect(300, 300, 250, 50)
                    if fullscreen_btn.collidepoint(mouse_pos):
                        self.toggle_fullscreen()
        
        return True

    def handle_player_select_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                # Crear nuevo jugador o seleccionar existente
                return self.show_name_input()
        return None
    
    def show_name_input(self):
        """Muestra un diálogo para ingresar el nombre del jugador"""
        input_active = True
        player_name = ""
        font = pygame.font.Font(None, 48)
        
        while input_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and player_name.strip():
                        return self.player_manager.get_or_create_player(player_name.strip())
                    elif event.key == pygame.K_ESCAPE:
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    else:
                        if len(player_name) < 20:
                            player_name += event.unicode
            
            # Dibujar pantalla de entrada
            self.screen.fill((15, 20, 35))
            
            # Título
            title = font.render("INGRESA TU NOMBRE", True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.screen.get_width()//2, 200))
            self.screen.blit(title, title_rect)
            
            # Campo de entrada
            input_box = pygame.Rect(self.screen.get_width()//2 - 200, 300, 400, 50)
            pygame.draw.rect(self.screen, (40, 50, 70), input_box)
            pygame.draw.rect(self.screen, (100, 150, 200), input_box, 3)
            
            # Texto ingresado
            text_surface = font.render(player_name, True, (255, 255, 255))
            self.screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))
            
            # Cursor parpadeante
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_x = input_box.x + 10 + text_surface.get_width()
                pygame.draw.line(self.screen, (255, 255, 255), 
                               (cursor_x, input_box.y + 10), 
                               (cursor_x, input_box.y + 40), 2)
            
            # Instrucciones
            inst_font = pygame.font.Font(None, 32)
            inst_text = inst_font.render("Presiona ENTER para continuar, ESC para cancelar", True, (150, 150, 150))
            inst_rect = inst_text.get_rect(center=(self.screen.get_width()//2, 400))
            self.screen.blit(inst_text, inst_rect)
            
            pygame.display.flip()
            self.clock.tick(60)
        
        return None
    
    def handle_settings_click(self, mouse_pos):
        # Botón para seleccionar música
        music_button = pygame.Rect(50, 300, 200, 50)
        if music_button.collidepoint(mouse_pos):
            self.music_manager.select_music_folder()
            return True
        return False
    
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            pygame.display.set_mode(self.settings.resolution, pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(self.settings.resolution)

    def check_card_unlocks(self):
        """Verifica si se deben desbloquear nuevas cartas y logros"""
        total_score = self.current_player['total_score']
        
        # Cartas comunes (0-5)
        common_thresholds = [100, 300, 600, 1000, 1500, 2000]
        # Cartas épicas (6-11)
        epic_thresholds = [3000, 5000, 7500, 10000, 15000, 20000]
        # Cartas legendarias (12-17)
        legendary_thresholds = [25000, 35000, 50000, 75000, 100000, 150000]
        
        all_thresholds = common_thresholds + epic_thresholds + legendary_thresholds
        
        for i, threshold in enumerate(all_thresholds):
            if total_score >= threshold and i not in self.current_player['unlocked_cards']:
                self.current_player['unlocked_cards'].append(i)
    
        # Logros y sistema de niveles/monedas
        unlocked = self.player_manager.check_achievements(self.current_player)
        if unlocked:
            # Puedes mostrar un popup/logro desbloqueado aquí si quieres
            pass
    
    def update(self):
        if self.state == GameState.PLAYING and self.tetris_game:
            self.tetris_game.update()
        
        self.music_manager.update()
    
    def draw(self):
        if self.loading:
            self.draw_loading_screen()
        elif self.state == GameState.PLAYER_SELECT:
            self.draw_player_select()
        elif self.state == GameState.MENU:
            self.menu.draw(self.current_player)
        elif self.state == GameState.PLAYING and self.tetris_game:
            self.tetris_game.draw()
        elif self.state == GameState.SETTINGS:
            self.draw_settings()
        elif self.state == GameState.CARDS:
            self.draw_cards()
        pygame.display.flip()

    def start_game_with_loading(self):
        self.loading = True
        self.draw()
        pygame.display.flip()
        pygame.time.delay(1200)  # 1.2 segundos de pantalla de carga
        self.tetris_game = TetrisGame(self.screen, self.settings, self.current_player)
        self.loading = False
        self.state = GameState.PLAYING

    def draw_loading_screen(self):
        self.screen.fill((15, 20, 35))
        font = pygame.font.Font(None, 72)
        text = font.render("Cargando...", True, (100, 200, 255))
        rect = text.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
        self.screen.blit(text, rect)
        # Puedes agregar animación si quieres
    
    def draw_player_select(self):
        self.screen.fill((15, 20, 35))
        
        # Título principal con gradiente
        font_large = pygame.font.Font(None, 96)
        font_medium = pygame.font.Font(None, 48)
        
        title = font_large.render("TETRIS BALATRO", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 200))
        self.screen.blit(title, title_rect)
        
        subtitle = font_medium.render("Natural Edition", True, (100, 150, 255))
        subtitle_rect = subtitle.get_rect(center=(self.screen.get_width()//2, 260))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Instrucciones
        inst_text = font_medium.render("Presiona ENTER para comenzar", True, (200, 200, 200))
        inst_rect = inst_text.get_rect(center=(self.screen.get_width()//2, 400))
        self.screen.blit(inst_text, inst_rect)
    
    def draw_settings(self):
        self.screen.fill((20, 25, 40))
        font = pygame.font.Font(None, 48)
        medium_font = pygame.font.Font(None, 36)
        
        # Título
        title = font.render("CONFIGURACIÓN", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 80))
        self.screen.blit(title, title_rect)
        
        # Sección de música
        music_title = medium_font.render("MÚSICA", True, (100, 200, 255))
        self.screen.blit(music_title, (50, 200))
        
        # Botón para seleccionar carpeta de música
        music_button = pygame.Rect(50, 300, 200, 50)
        pygame.draw.rect(self.screen, (60, 80, 120), music_button)
        pygame.draw.rect(self.screen, (100, 150, 200), music_button, 2)
        
        button_text = medium_font.render("Seleccionar Música", True, (255, 255, 255))
        button_rect = button_text.get_rect(center=music_button.center)
        self.screen.blit(button_text, button_rect)
        
        # Botón de pantalla completa
        fullscreen_btn = pygame.Rect(300, 300, 250, 50)
        pygame.draw.rect(self.screen, (60, 120, 60), fullscreen_btn)
        pygame.draw.rect(self.screen, (100, 200, 100), fullscreen_btn, 2)
        btn_text = medium_font.render(
            "Pantalla Completa: ON" if self.fullscreen else "Pantalla Completa: OFF",
            True, (255, 255, 255)
        )
        btn_rect = btn_text.get_rect(center=fullscreen_btn.center)
        self.screen.blit(btn_text, btn_rect)

        # Estado actual de la música (debajo de los botones)
        current_song = self.music_manager.get_current_song()
        if current_song:
            song_text = medium_font.render(f"Reproduciendo: {current_song}", True, (150, 255, 150))
            self.screen.blit(song_text, (50, 370 + 30))  # +30 para dejar margen debajo de los botones
        
        # Controles
        controls_y = 450 + 30  # +30 para dejar margen debajo del texto de música
        controls_title = medium_font.render("CONTROLES", True, (100, 200, 255))
        self.screen.blit(controls_title, (50, controls_y))
        
        controls = [
            "Mover: IZQ / DER",
            "Rotar: ARRIBA o R",
            "Caída Rápida: ABAJO",
            "Caída Instantánea: ESPACIO",
            "Usar Cartas: 1, 2, 3"
        ]
        
        small_font = pygame.font.Font(None, 28)
        for i, control in enumerate(controls):
            text = small_font.render(control, True, (200, 200, 200))
            self.screen.blit(text, (50, controls_y + 40 + i * 30))
        
        # Instrucciones
        inst_text = medium_font.render("ESC - Volver al menú", True, (150, 150, 150))
        self.screen.blit(inst_text, (50, self.screen.get_height() - 50))
    
    def draw_cards(self):
        self.screen.fill((15, 20, 30))
        font = pygame.font.Font(None, 48)
        medium_font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 24)

        # Título de la colección
        title = font.render("COLECCIÓN DE CARTAS", True, (255,255,255))
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 60))
        self.screen.blit(title, title_rect)

        # Estadísticas del jugador
        stats_y = 110
        if self.current_player:
            stats = [
                f"Jugador: {self.current_player['name']}",
                f"Puntuación Total: {self.current_player['total_score']:,}",
                f"Mejor Puntuación: {self.current_player.get('best_score', 0):,}",
                f"Partidas Jugadas: {self.current_player.get('games_played', 0)}"
            ]
            for i, stat in enumerate(stats):
                text = small_font.render(stat, True, (200,200,200))
                self.screen.blit(text, (50, stats_y + i*25))

        # Espaciado mayor para evitar solapamiento
        y_offset = stats_y + 4*25 + 40

        # Dibujar secciones de cartas
        self.draw_card_section("COMUNES", (150,255,150), y_offset, 0, 6)
        y_offset += 150
        self.draw_card_section("ÉPICAS", (255,150,255), y_offset, 6, 12)
        y_offset += 150
        self.draw_card_section("LEGENDARIAS", (255,215,0), y_offset, 12, 18)

        # Instrucciones de vuelta
        inst_text = medium_font.render("ESC - Volver", True, (150,150,150))
        self.screen.blit(inst_text, (50, self.screen.get_height()-40))
        
        # Reproductor de música de menú (solo se activa en el menú)
        # Se reutiliza el reproductor del menú, pero aquí se posiciona fijo abajo a la izquierda
        music_rect = pygame.Rect(20, self.screen.get_height()-80, 320, 54)
        pygame.draw.rect(self.screen, (30,40,60), music_rect, border_radius=10)
        pygame.draw.rect(self.screen, (80,100,130), music_rect, 2, border_radius=10)
        btn_size = 36
        btn_y = self.screen.get_height()-80 + (54 - btn_size)//2
        btn_prev = pygame.Rect(20+10, btn_y, btn_size, btn_size)
        btn_next = pygame.Rect(20+60, btn_y, btn_size, btn_size)
        pygame.draw.rect(self.screen, (60,80,120), btn_prev, border_radius=8)
        pygame.draw.rect(self.screen, (60,80,120), btn_next, border_radius=8)
        pygame.draw.polygon(self.screen, (255,255,255), [
            (btn_prev.x+26, btn_prev.y+8),
            (btn_prev.x+12, btn_prev.y+18),
            (btn_prev.x+26, btn_prev.y+28)
        ])
        pygame.draw.polygon(self.screen, (255,255,255), [
            (btn_next.x+10, btn_next.y+8),
            (btn_next.x+24, btn_next.y+18),
            (btn_next.x+10, btn_next.y+28)
        ])
        song_text = medium_font.render(self.music_manager.get_current_menu_song_name() or "Sin música", True, (255,255,255))
        self.screen.blit(song_text, (20+110, self.screen.get_height()-80 + (54 - song_text.get_height())//2))

    def draw_card_section(self, title, color, y, start_idx, end_idx):
        medium_font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 22)
        from src.cards import CardManager
        card_manager = CardManager()

        # Título de la sección
        section_title = medium_font.render(title, True, color)
        title_width = section_title.get_width()
        section_width = self.screen.get_width() - 100  # Margen de 50px a cada lado
        self.screen.blit(section_title, (50 + (section_width - title_width) // 2, y))

        # Espaciado mejorado para cartas
        cards_per_row = 3
        card_width = 220  # Aumentado para dar más espacio
        card_height = 70  # Aumentado para dar más espacio
        card_margin_x = 40
        card_margin_y = 30  # Más espacio vertical
        total_width = cards_per_row * card_width + (cards_per_row - 1) * card_margin_x
        base_x = (self.screen.get_width() - total_width) // 2
        base_y = y + 40

        mouse_pos = pygame.mouse.get_pos()
        if not hasattr(self, "debug_card_rects"):
            self.debug_card_rects = []
        if start_idx == 0:
            self.debug_card_rects = []  # Limpiar al inicio de la primera sección

        for i in range(start_idx, min(end_idx, len(card_manager.all_cards))):
            card = card_manager.all_cards[i]
            row = (i - start_idx) // cards_per_row
            col = (i - start_idx) % cards_per_row

            card_x = base_x + col * (card_width + card_margin_x)
            card_y = base_y + row * (card_height + card_margin_y)

            unlocked = i in self.current_player.get('unlocked_cards', []) if self.current_player else False

            bg_color = (60, 80, 100) if unlocked else (40, 40, 40)
            border_color = color if unlocked else (100, 100, 100)
            text_color = (255, 255, 255) if unlocked else (130, 130, 130)

            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)

            # Debug: hover efecto y registro de rects para click
            if self.debug_menu:
                if card_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(self.screen, (255, 255, 0), card_rect, 3)
                else:
                    pygame.draw.rect(self.screen, border_color, card_rect, 2)
                self.debug_card_rects.append((card_rect, i))
            else:
                pygame.draw.rect(self.screen, border_color, card_rect, 2)

            pygame.draw.rect(self.screen, bg_color, card_rect)

            # Nombre de la carta centrado
            name_font = pygame.font.Font(None, 26)
            name_text = name_font.render(card.name, True, text_color)
            name_rect = name_text.get_rect(centerx=card_x + card_width//2, y=card_y + 15)
            self.screen.blit(name_text, name_rect)

            # Estado y rareza en la misma línea
            status = "DESBLOQUEADA" if unlocked else "BLOQUEADA"
            rarity = card.rarity.upper() if hasattr(card, 'rarity') else ""
            
            # Estado a la izquierda
            status_text = small_font.render(status, True, text_color)
            status_rect = status_text.get_rect(x=card_x + 10, centery=card_y + 45)
            self.screen.blit(status_text, status_rect)
            
            # Rareza a la derecha
            rarity_text = small_font.render(rarity, True, color)
            rarity_rect = rarity_text.get_rect(right=card_x + card_width - 10, centery=card_y + 45)
            self.screen.blit(rarity_text, rarity_rect)

    def draw_debug_menu(self):
        font = pygame.font.Font(None, 28)
        debug_lines = [
            f"DEBUG MENU",
            f"FPS: {self.clock.get_fps():.1f}",
            f"State: {self.state.name}",
            f"Player: {self.current_player['name'] if self.current_player else 'None'}",
            f"Score: {getattr(self.tetris_game, 'score', 0) if self.tetris_game else 0}",
            f"Cards: {len(self.settings.unlocked_cards)}"
        ]
        for i, line in enumerate(debug_lines):
            surf = font.render(line, True, (255, 255, 0))
            self.screen.blit(surf, (20, 40 + i * 28))

    def create_double_click_effect(self, position):
        """
        Crea un efecto visual en la posición del doble click.
        """
        effect_duration = 500  # Duración del efecto en ms
        effect_start_time = pygame.time.get_ticks()
        effect_surface = pygame.Surface((100, 100), pygame.SRCALPHA)
        effect_surface.fill((255, 255, 255, 0))  # Transparente inicial

        while pygame.time.get_ticks() - effect_start_time < effect_duration:
            elapsed = pygame.time.get_ticks() - effect_start_time
            alpha = max(0, 255 - int((elapsed / effect_duration) * 255))
            size = max(10, 100 - int((elapsed / effect_duration) * 90))
            effect_surface.fill((255, 255, 255, alpha))
            pygame.draw.circle(effect_surface, (255, 255, 255, alpha), (50, 50), size)
            rect = effect_surface.get_rect(center=position)
            self.screen.blit(effect_surface, rect)
            pygame.display.flip()

    def show_card_demo(self, card_idx):
        """Muestra una demostración visual de la carta"""
        from src.cards import CardManager
        card_manager = CardManager()
        card = card_manager.all_cards[card_idx]

        # Crear overlay semitransparente
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))  # Fondo semitransparente

        # Dibujar título
        font_title = pygame.font.Font(None, 72)
        font_desc = pygame.font.Font(None, 36)
        
        title = font_title.render(card.name, True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 200))
        
        # Dibujar descripción
        desc = font_desc.render(card.demo_description, True, (200, 200, 200))
        desc_rect = desc.get_rect(center=(self.screen.get_width()//2, 300))
        
        # Dibujar instrucciones
        inst = font_desc.render("Click para cerrar", True, (150, 150, 150))
        inst_rect = inst.get_rect(center=(self.screen.get_width()//2, self.screen.get_height() - 100))
        
        # Dibujar borde decorativo según rareza
        color = {
            "common": (150, 255, 150),
            "epic": (255, 150, 255),
            "legendary": (255, 215, 0)
        }[card.rarity]
        
        demo_rect = pygame.Rect(self.screen.get_width()//2 - 300, 150, 600, 300)
        pygame.draw.rect(overlay, color, demo_rect, 3, border_radius=15)
        
        # Agregar todos los elementos al overlay
        overlay.blit(title, title_rect)
        overlay.blit(desc, desc_rect)
        overlay.blit(inst, inst_rect)
        
        # Mostrar el overlay y esperar click
        self.screen.blit(overlay, (0, 0))
        pygame.display.flip()
        
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                    waiting = False
                elif event.type == pygame.QUIT:
                    return

    def show_error_message(self, message):
        """
        Muestra un mensaje de error temporal en pantalla.
        """
        error_duration = 1500  # 1.5 segundos
        error_overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        error_overlay.fill((0, 0, 0, 180))
        font = pygame.font.Font(None, 64)
        error_text = font.render(message, True, (255, 50, 50))
        text_rect = error_text.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
        error_overlay.blit(error_text, text_rect)
        self.screen.blit(error_overlay, (0, 0))
        pygame.display.flip()
        pygame.time.delay(error_duration)

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()