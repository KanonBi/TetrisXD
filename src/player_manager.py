import json
import os
from datetime import datetime

class PlayerManager:
    def __init__(self):
        self.players_file = "players.json"
        self.players_data = self.load_all_players()
        self.achievements_def = [
            # (nombre, descripción, rareza, condición lambda player)
            ("Primeras líneas", "Haz tu primera línea", "común", lambda p: p.get("lines_cleared", 0) >= 1),
            ("TetraMaster", "Haz 8 líneas de una vez", "legendaria", lambda p: p.get("max_lines", 0) >= 8),
            ("Puntaje 10k", "Llega a 10,000 puntos", "épica", lambda p: p.get("best_score", 0) >= 10000),
            ("Coleccionista", "Desbloquea todas las cartas", "épica", lambda p: len(p.get("unlocked_cards", [])) >= 18),
            ("Jugador Persistente", "Juega 100 partidas", "rara", lambda p: p.get("games_played", 0) >= 100),
            # ...agrega más logros aquí...
        ]
        self.xp_per_achievement = {"común": 50, "rara": 120, "épica": 300, "legendaria": 1000}
        self.coins_per_achievement = {"común": 10, "rara": 30, "épica": 100, "legendaria": 500}

    def load_all_players(self):
        """Carga todos los datos de jugadores"""
        try:
            with open(self.players_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_all_players(self):
        """Guarda todos los datos de jugadores"""
        with open(self.players_file, 'w', encoding='utf-8') as f:
            json.dump(self.players_data, f, indent=2, ensure_ascii=False)
    
    def get_or_create_player(self, name):
        """Obtiene un jugador existente o crea uno nuevo"""
        if name in self.players_data:
            player = self.players_data[name]
            player['last_played'] = datetime.now().isoformat()
            return player
        else:
            # Crear nuevo jugador
            new_player = {
                'name': name,
                'total_score': 0,
                'best_score': 0,
                'games_played': 0,
                'unlocked_cards': [],
                'created_date': datetime.now().isoformat(),
                'last_played': datetime.now().isoformat(),
                'achievements': [],
                'settings': {
                    'music_volume': 0.7,
                    'sfx_volume': 0.8
                }
            }
            self.players_data[name] = new_player
            self.save_all_players()
            return new_player
    
    def save_player_data(self, player):
        """Guarda los datos de un jugador específico"""
        if player and 'name' in player:
            player['last_played'] = datetime.now().isoformat()
            self.players_data[player['name']] = player
            self.save_all_players()
    
    def get_leaderboard(self, limit=10):
        """Obtiene la tabla de líderes"""
        players = list(self.players_data.values())
        players.sort(key=lambda x: x.get('best_score', 0), reverse=True)
        return players[:limit]
    
    def delete_player(self, name):
        """Elimina un jugador"""
        if name in self.players_data:
            del self.players_data[name]
            self.save_all_players()
            return True
        return False
    
    def check_achievements(self, player):
        if "achievements" not in player:
            player["achievements"] = []
        if "xp" not in player:
            player["xp"] = 0
        if "coins" not in player:
            player["coins"] = 0
        if "level" not in player:
            player["level"] = 1
        unlocked = []
        for name, desc, rarity, cond in self.achievements_def:
            if name not in player["achievements"] and cond(player):
                player["achievements"].append(name)
                player["xp"] += self.xp_per_achievement[rarity]
                player["coins"] += self.coins_per_achievement[rarity]
                unlocked.append((name, rarity))
        # Subida de nivel simple: cada 500xp sube 1 nivel
        new_level = player["xp"] // 500 + 1
        if new_level > player["level"]:
            player["level"] = new_level
        return unlocked

    def get_achievements_info(self, player):
        info = []
        for name, desc, rarity, _ in self.achievements_def:
            unlocked = name in player.get("achievements", [])
            info.append({"name": name, "desc": desc, "rarity": rarity, "unlocked": unlocked})
        return info