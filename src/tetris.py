import pygame
import random
from enum import Enum

class PieceType(Enum):
    I = 1
    O = 2
    T = 3
    S = 4
    Z = 5
    J = 6
    L = 7

class TetrisPiece:
    SHAPES = {
        PieceType.I: [
            ['....', 'IIII', '....', '....'],
            ['..I.', '..I.', '..I.', '..I.'],
            ['....', 'IIII', '....', '....'],
            ['..I.', '..I.', '..I.', '..I.']
        ],
        PieceType.O: [
            ['OO', 'OO'],
            ['OO', 'OO'],
            ['OO', 'OO'],
            ['OO', 'OO']
        ],
        PieceType.T: [
            ['...', 'TTT', '.T.'],
            ['..T', '.TT', '..T'],
            ['.T.', 'TTT', '...'],
            ['T..', 'TT.', 'T..']
        ],
        PieceType.S: [
            ['...', '.SS', 'SS.'],
            ['S..', 'SS.', '.S.'],
            ['...', '.SS', 'SS.'],
            ['S..', 'SS.', '.S.']
        ],
        PieceType.Z: [
            ['...', 'ZZ.', '.ZZ'],
            ['..Z', '.ZZ', '.Z.'],
            ['...', 'ZZ.', '.ZZ'],
            ['..Z', '.ZZ', '.Z.']
        ],
        PieceType.J: [
            ['...', 'JJJ', '..J'],
            ['..J', '..J', '.JJ'],
            ['J..', 'JJJ', '...'],
            ['JJ.', 'J..', 'J..']
        ],
        PieceType.L: [
            ['...', 'LLL', 'L..'],
            ['.L.', '.L.', '.LL'],
            ['..L', 'LLL', '...'],
            ['LL.', '..L', '..L']
        ]
    }
    
    COLORS = {
        PieceType.I: (0, 255, 255),    # Cyan brillante
        PieceType.O: (255, 255, 0),    # Amarillo brillante
        PieceType.T: (160, 32, 240),   # Púrpura vibrante
        PieceType.S: (50, 255, 50),    # Verde brillante
        PieceType.Z: (255, 50, 50),    # Rojo brillante
        PieceType.J: (50, 100, 255),   # Azul brillante
        PieceType.L: (255, 165, 0)     # Naranja brillante
    }
    
    def __init__(self, piece_type, x=0, y=0):
        self.type = piece_type
        self.x = x
        self.y = y
        self.rotation = 0
        self.shape = self.SHAPES[piece_type][0]
        self.color = self.COLORS[piece_type]
        self.lock_timer = 0
    
    def rotate_clockwise(self):
        """Rota la pieza en sentido horario"""
        shapes = self.SHAPES[self.type]
        self.rotation = (self.rotation + 1) % len(shapes)
        self.shape = shapes[self.rotation]
    
    def rotate_counterclockwise(self):
        """Rota la pieza en sentido antihorario"""
        shapes = self.SHAPES[self.type]
        self.rotation = (self.rotation - 1) % len(shapes)
        self.shape = shapes[self.rotation]
    
    def get_cells(self):
        cells = []
        for row_idx, row in enumerate(self.shape):
            for col_idx, cell in enumerate(row):
                if cell != '.' and cell != ' ':
                    cells.append((self.x + col_idx, self.y + row_idx))
        return cells
    
    def get_ghost_position(self, board):
        """Calcula la posición donde caería la pieza"""
        ghost_y = self.y
        while board.is_valid_position_for_piece(self, 0, ghost_y + 1 - self.y):
            ghost_y += 1
        return ghost_y

class TetrisBoard:
    def __init__(self, width=10, height=20):
        self.width = width
        self.height = height
        self.grid = [[None for _ in range(width)] for _ in range(height)]
        self.current_piece = None
        self.next_piece = None
        self.ghost_y = 0
        self.generate_new_piece()

    def generate_new_piece(self):
        if self.next_piece is None:
            self.next_piece = TetrisPiece(random.choice(list(PieceType)), self.width // 2 - 1, 0)
        self.current_piece = self.next_piece
        self.next_piece = TetrisPiece(random.choice(list(PieceType)), self.width // 2 - 1, 0)
        if self.current_piece:
            self.ghost_y = self.current_piece.get_ghost_position(self)

    def is_valid_position_for_piece(self, piece, dx=0, dy=0, rotation=None):
        if rotation is not None:
            temp_piece = TetrisPiece(piece.type, piece.x + dx, piece.y + dy)
            temp_piece.rotation = rotation
            temp_piece.shape = temp_piece.SHAPES[piece.type][rotation % len(temp_piece.SHAPES[piece.type])]
            cells = temp_piece.get_cells()
        else:
            cells = [(x + dx, y + dy) for x, y in piece.get_cells()]

        for x, y in cells:
            # NO PERMITIR POSICIONES FUERA DEL TABLERO
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                return False
            if self.grid[y][x] is not None:
                return False
        return True

    def move_piece(self, dx, dy):
        # SOLO PERMITIR MOVIMIENTO SI TODAS LAS CELDAS SON VÁLIDAS
        if self.current_piece and self.is_valid_position_for_piece(self.current_piece, dx, dy):
            self.current_piece.x += dx
            self.current_piece.y += dy
            self.ghost_y = self.current_piece.get_ghost_position(self)
            return True
        return False

    def place_piece(self, piece=None):
        if piece is None:
            piece = self.current_piece
        if piece:
            # Check if any part of the piece is above the board (game over condition)
            for x, y in piece.get_cells():
                if y < 0:
                    return False  # Piece extends above board, should trigger game over

            # Place the piece only if it's completely within bounds
            for x, y in piece.get_cells():
                # SOLO COLOCAR BLOQUES DENTRO DEL TABLERO
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.grid[y][x] = piece.color
        return True

    def clear_lines(self):
        lines_cleared = 0
        y = self.height - 1
        
        while y >= 0:
            if all(cell is not None for cell in self.grid[y]):
                # Línea completa, eliminarla
                del self.grid[y]
                self.grid.insert(0, [None for _ in range(self.width)])
                lines_cleared += 1
            else:
                y -= 1
        
        return lines_cleared
    
    def rotate_piece_clockwise(self):
        if self.current_piece:
            new_rotation = (self.current_piece.rotation + 1) % len(self.current_piece.SHAPES[self.current_piece.type])
            if self.is_valid_position_for_piece(self.current_piece, rotation=new_rotation):
                self.current_piece.rotate_clockwise()
                # Actualizar posición fantasma
                self.ghost_y = self.current_piece.get_ghost_position(self)
                return True
            else:
                # Intentar wall kick (empujar la pieza si está cerca de la pared)
                for dx in [-1, 1, -2, 2]:
                    if self.is_valid_position_for_piece(self.current_piece, dx, 0, new_rotation):
                        self.current_piece.x += dx
                        self.current_piece.rotate_clockwise()
                        self.ghost_y = self.current_piece.get_ghost_position(self)
                        return True
        return False
    
    def rotate_piece_counterclockwise(self):
        if self.current_piece:
            new_rotation = (self.current_piece.rotation - 1) % len(self.current_piece.SHAPES[self.current_piece.type])
            if self.is_valid_position_for_piece(self.current_piece, rotation=new_rotation):
                self.current_piece.rotate_counterclockwise()
                self.ghost_y = self.current_piece.get_ghost_position(self)
                return True
            else:
                # Intentar wall kick para rotación antihoraria
                for dx in [-1, 1, -2, 2]:
                    if self.is_valid_position_for_piece(self.current_piece, dx, 0, new_rotation):
                        self.current_piece.x += dx
                        self.current_piece.rotate_counterclockwise()
                        self.ghost_y = self.current_piece.get_ghost_position(self)
                        return True
        return False
    
    def drop_piece(self):
        """Baja la pieza actual hasta el fondo (hard drop)"""
        if self.current_piece:
            while self.move_piece(0, 1):
                pass
    
    def hard_drop_piece(self):
        """Implementación de hard drop que devuelve las líneas caídas"""
        if not self.current_piece:
            return 0
            
        lines_dropped = 0
        while self.move_piece(0, 1):
            lines_dropped += 1
            
        return lines_dropped
    
    def get_ghost_piece(self):
        """Devuelve una copia de la pieza actual en su posición fantasma"""
        if not self.current_piece:
            return None
            
        ghost = TetrisPiece(self.current_piece.type, self.current_piece.x, self.ghost_y)
        ghost.rotation = self.current_piece.rotation
        ghost.shape = self.current_piece.shape
        return ghost
    
    def check_game_over(self):
        """Verifica si el juego ha terminado"""
        if self.current_piece:
            # Check if the current piece can be placed at its spawn position
            if not self.is_valid_position_for_piece(self.current_piece):
                return True
            # Also check if any part of the piece is above the board
            for x, y in self.current_piece.get_cells():
                if y < 0:
                    return True
        return False
    
    def update(self):
        """Actualiza el estado del tablero, devuelve True si se colocó una pieza"""
        if self.current_piece:
            if not self.move_piece(0, 1):
                self.current_piece.lock_timer += 16
                if self.current_piece.lock_timer >= 500:  # 500ms de delay
                    self.place_piece(self.current_piece)
                    lines_cleared = self.clear_lines()
                    self.generate_new_piece()
                    if not self.is_valid_position_for_piece(self.current_piece):
                        return "game_over"
                    return lines_cleared
            else:
                self.current_piece.lock_timer = 0
        return 0
