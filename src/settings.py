import pygame

class Settings:
    def __init__(self):
        # Resolución adaptativa con margen extra para el piso
        info = pygame.display.Info()
        # Calcula el alto mínimo necesario para el tablero y controles
        min_width = 900  # suficiente para tablero y panel lateral
        min_height = 800  # suficiente para tablero y que no se corte el piso
        self.resolution = (
            max(min_width, min(1400, info.current_w - 100)),
            max(min_height, min(950, info.current_h - 50))
        )
        
        # Controles mejorados
        self.controls = {
            'left': pygame.K_LEFT,
            'right': pygame.K_RIGHT,
            'rotate': pygame.K_UP,
            'rotate_alt': pygame.K_r,  # Rotación alternativa
            'down': pygame.K_DOWN,
            'drop': pygame.K_SPACE,
            'hold': pygame.K_c,  # Para futuras funciones
            'pause': pygame.K_p
        }
        
        # Datos del jugador actual
        self.current_player = None
        self.total_score = 0
        self.unlocked_cards = []
        
        # Configuración del juego
        self.fall_speed = 800  # milisegundos (más lento para mejor jugabilidad)
        self.fast_fall_speed = 80
        self.lock_delay = 500  # Tiempo antes de que la pieza se bloquee
        
        # Configuración visual
        self.show_ghost_piece = True
        self.show_grid = True
        self.particle_effects = True
        
        # Audio
        self.music_volume = 0.7
        self.sfx_volume = 0.8
    
    def load_player_data(self, player):
        """Carga los datos de un jugador específico"""
        if player:
            self.current_player = player
            self.total_score = player.get('total_score', 0)
            self.unlocked_cards = player.get('unlocked_cards', [])
            
            # Cargar configuraciones personales
            player_settings = player.get('settings', {})
            self.music_volume = player_settings.get('music_volume', 0.7)
            self.sfx_volume = player_settings.get('sfx_volume', 0.8)