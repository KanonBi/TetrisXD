import pygame
import random
from src.tetris import TetrisBoard, TetrisPiece

class Card:
    def __init__(self, name, description, effect_type, rarity="common", power=1, duration=0):
        self.name = name
        self.description = description
        self.effect_type = effect_type
        self.rarity = rarity
        self.power = power
        self.duration = duration
        self.used = False
        # Agregar descripciones detalladas para demostraciones
        self.demo_description = {
            "clear_line": "Limpia una línea casi completa",
            "score_multiplier": f"Multiplica los puntos x{power} durante {duration//60} segundos",
            "slow_time": f"Ralentiza la caída durante {duration//60} segundos",
            "ghost_piece": f"Atraviesa bloques durante {duration//60} segundos",
            "perfect_line": "Completa automáticamente una línea",
            "line_bomb": f"Elimina {power} líneas instantáneamente",
            "piece_transform": "Transforma la pieza en una línea I",
            "gravity_reverse": f"Invierte la gravedad durante {duration//60} segundos",
            "time_freeze": f"Congela el tiempo durante {duration//60} segundos",
            "mega_clear": "Limpia líneas con 3 o menos bloques"
        }.get(effect_type, "Sin descripción disponible")
    
    def use(self, game_state):
        if self.used:
            return False
        
        self.used = True
        return self.apply_effect(game_state)
    
    def apply_effect(self, game_state):
        if self.effect_type == "clear_line":
            return self.clear_line_effect(game_state)
        elif self.effect_type == "score_multiplier":
            return self.score_multiplier_effect(game_state)
        elif self.effect_type == "slow_time":
            return self.slow_time_effect(game_state)
        elif self.effect_type == "ghost_piece":
            return self.ghost_piece_effect(game_state)
        elif self.effect_type == "perfect_line":
            return self.perfect_line_effect(game_state)
        elif self.effect_type == "line_bomb":
            return self.line_bomb_effect(game_state)
        elif self.effect_type == "piece_transform":
            return self.piece_transform_effect(game_state)
        elif self.effect_type == "gravity_reverse":
            return self.gravity_reverse_effect(game_state)
        elif self.effect_type == "time_freeze":
            return self.time_freeze_effect(game_state)
        elif self.effect_type == "mega_clear":
            return self.mega_clear_effect(game_state)
        elif self.effect_type == "golden_touch":
            return self.golden_touch_effect(game_state)
        elif self.effect_type == "reality_shift":
            return self.reality_shift_effect(game_state)
        
        return False
    
    def clear_line_effect(self, game_state):
        for y in range(game_state.board.height - 1, -1, -1):
            if sum(1 for cell in game_state.board.grid[y] if cell is not None) >= 7:
                game_state.board.grid[y] = [None for _ in range(game_state.board.width)]
                return True
        return False
    
    def score_multiplier_effect(self, game_state):
        game_state.score_multiplier = self.power
        game_state.multiplier_timer = self.duration
        return True
    
    def slow_time_effect(self, game_state):
        game_state.fall_timer_max *= 2
        game_state.slow_time_timer = self.duration
        return True
    
    def ghost_piece_effect(self, game_state):
        game_state.ghost_mode = True
        game_state.ghost_timer = self.duration
        return True
    
    def perfect_line_effect(self, game_state):
        for y in range(game_state.board.height - 1, -1, -1):
            if any(cell is not None for cell in game_state.board.grid[y]):
                for x in range(game_state.board.width):
                    if game_state.board.grid[y][x] is None:
                        game_state.board.grid[y][x] = (150, 150, 150)
                return True
        return False
    
    def line_bomb_effect(self, game_state):
        # Elimina múltiples líneas
        lines_cleared = 0
        for _ in range(self.power):
            for y in range(game_state.board.height - 1, -1, -1):
                if any(cell is not None for cell in game_state.board.grid[y]):
                    game_state.board.grid[y] = [None for _ in range(game_state.board.width)]
                    lines_cleared += 1
                    break
        return lines_cleared > 0
    
    def piece_transform_effect(self, game_state):
        # Transforma la pieza actual en una línea I
        if game_state.board.current_piece:
            from src.tetris import PieceType, TetrisPiece
            new_piece = TetrisPiece(PieceType.I, 
                                  game_state.board.current_piece.x, 
                                  game_state.board.current_piece.y)
            game_state.board.current_piece = new_piece
            return True
        return False
    
    def gravity_reverse_effect(self, game_state):
        game_state.gravity_reversed = True
        game_state.gravity_timer = self.duration
        return True
    
    def time_freeze_effect(self, game_state):
        game_state.time_frozen = True
        game_state.freeze_timer = self.duration
        return True
    
    def mega_clear_effect(self, game_state):
        # Limpia todas las líneas con menos de 3 bloques
        lines_cleared = 0
        for y in range(game_state.board.height - 1, -1, -1):
            block_count = sum(1 for cell in game_state.board.grid[y] if cell is not None)
            if 0 < block_count <= 3:
                game_state.board.grid[y] = [None for _ in range(game_state.board.width)]
                lines_cleared += 1
        return lines_cleared > 0
    
    def golden_touch_effect(self, game_state):
        game_state.golden_mode = True
        game_state.golden_timer = self.duration
        game_state.score_multiplier = self.power
        return True
    
    def reality_shift_effect(self, game_state):
        # Reorganiza aleatoriamente el tablero
        all_blocks = []
        for y in range(game_state.board.height):
            for x in range(game_state.board.width):
                if game_state.board.grid[y][x] is not None:
                    all_blocks.append(game_state.board.grid[y][x])
                game_state.board.grid[y][x] = None
        
        # Redistribuir bloques aleatoriamente en la parte inferior
        random.shuffle(all_blocks)
        block_index = 0
        
        for y in range(game_state.board.height - 1, -1, -1):
            for x in range(game_state.board.width):
                if block_index < len(all_blocks) and random.random() < 0.7:
                    game_state.board.grid[y][x] = all_blocks[block_index]
                    block_index += 1
                if block_index >= len(all_blocks):
                    break
            if block_index >= len(all_blocks):
                break
        
        return True

class CardManager:
    def __init__(self):
        self.all_cards = [
            # Cartas Comunes (0-5)
            Card("Línea Perfecta", "Completa la línea más baja", "perfect_line", "common"),
            Card("Multiplicador x2", "Duplica puntos por 5 seg", "score_multiplier", "common", 2, 300),
            Card("Tiempo Extra", "Ralentiza caída por 8 seg", "slow_time", "common", 1, 480),
            Card("Pieza Fantasma", "Atraviesa bloques por 4 seg", "ghost_piece", "common", 1, 240),
            Card("Limpieza Básica", "Limpia una línea casi llena", "clear_line", "common"),
            Card("Combo x2", "Duplica puntos por 3 seg", "score_multiplier", "common", 2, 180),
            
            # Cartas Épicas (6-11)
            Card("Bomba de Líneas", "Elimina 3 líneas inferiores", "line_bomb", "epic", 3),
            Card("Multiplicador x3", "Triplica puntos por 6 seg", "score_multiplier", "epic", 3, 360),
            Card("Transformación I", "Convierte pieza actual en línea I", "piece_transform", "epic"),
            Card("Tiempo Congelado", "Congela el tiempo por 5 seg", "time_freeze", "epic", 1, 300),
            Card("Gravedad Inversa", "Invierte gravedad por 8 seg", "gravity_reverse", "epic", 1, 480),
            Card("Mega Limpieza", "Elimina líneas con ≤3 bloques", "mega_clear", "epic"),
            
            # Cartas Legendarias (12-17)
            Card("Toque Dorado", "x5 puntos + efectos dorados 10s", "golden_touch", "legendary", 5, 600),
            Card("Cambio de Realidad", "Reorganiza todo el tablero", "reality_shift", "legendary"),
            Card("Multiplicador x10", "x10 puntos por 4 segundos", "score_multiplier", "legendary", 10, 240),
            Card("Bomba Nuclear", "Elimina 8 líneas inferiores", "line_bomb", "legendary", 8),
            Card("Maestro del Tiempo", "Congela tiempo por 15 seg", "time_freeze", "legendary", 1, 900),
            Card("Dios del Tetris", "Todos los efectos por 5 seg", "golden_touch", "legendary", 3, 300)
        ]
        
        self.hand = []
        self.max_hand_size = 3
    
    def draw_card(self, unlocked_cards):
        if len(self.hand) < self.max_hand_size and unlocked_cards:
            available_indices = [i for i in unlocked_cards if i < len(self.all_cards)]
            if available_indices:
                card_index = random.choice(available_indices)
                original_card = self.all_cards[card_index]
                new_card = Card(
                    original_card.name,
                    original_card.description,
                    original_card.effect_type,
                    original_card.rarity,
                    original_card.power,
                    original_card.duration
                )
                self.hand.append(new_card)
                return True
        return False
    
    def use_card(self, index, game_state):
        if 0 <= index < len(self.hand):
            card = self.hand[index]
            if card.use(game_state):
                self.hand.pop(index)
                return True
        return False
    
    def get_rarity_color(self, rarity):
        colors = {
            "common": (150, 255, 150),
            "epic": (255, 150, 255),
            "legendary": (255, 215, 0)
        }
        return colors.get(rarity, (255, 255, 255))
    
    def draw_hand(self, screen, x, y):
        font = pygame.font.Font(None, 20)
        title_font = pygame.font.Font(None, 28)
        
        # Título
        title = title_font.render("CARTAS ACTIVAS", True, (255, 255, 255))
        screen.blit(title, (x, y - 30))
        
        card_width = 140
        card_height = 90
        
        for i, card in enumerate(self.hand):
            card_x = x + i * (card_width + 15)
            card_y = y
            
            # Color según rareza
            rarity_color = self.get_rarity_color(card.rarity)
            bg_color = (40, 50, 70) if not card.used else (30, 30, 30)
            
            # Fondo de la carta con efecto de brillo
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
            
            # Sombra
            shadow_rect = card_rect.copy()
            shadow_rect.x += 2
            shadow_rect.y += 2
            pygame.draw.rect(screen, (10, 10, 10), shadow_rect, border_radius=8)
            
            # Fondo
            pygame.draw.rect(screen, bg_color, card_rect, border_radius=8)
            pygame.draw.rect(screen, rarity_color, card_rect, 3, border_radius=8)
            
            # Nombre de la carta
            name_lines = card.name.split(' ')
            for j, line in enumerate(name_lines[:2]):  # Máximo 2 líneas
                name_text = font.render(line, True, (255, 255, 255))
                name_rect = name_text.get_rect(center=(card_x + card_width//2, card_y + 15 + j * 15))
                screen.blit(name_text, name_rect)
            
            # Rareza
            rarity_text = font.render(card.rarity.upper(), True, rarity_color)
            rarity_rect = rarity_text.get_rect(center=(card_x + card_width//2, card_y + 50))
            screen.blit(rarity_text, rarity_rect)
            
            # Número de la carta
            num_text = title_font.render(f"{i+1}", True, (255, 255, 0))
            screen.blit(num_text, (card_x + 5, card_y + 5))
            
            # Indicador de poder si aplica
            if card.power > 1:
                power_text = font.render(f"x{card.power}", True, (255, 200, 0))
                screen.blit(power_text, (card_x + card_width - 25, card_y + 5))