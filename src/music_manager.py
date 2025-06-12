import pygame
import os
import random
import tkinter as tk
from tkinter import filedialog

class MusicManager:
    def __init__(self):
        pygame.mixer.init()
        self.music_folder = None
        self.music_files = []
        self.current_song_index = 0
        self.is_playing = False
        self.volume = 0.7
        
        # Crear carpeta de música si no existe
        if not os.path.exists("music"):
            os.makedirs("music")
        
        # Cargar música de la carpeta por defecto
        self.load_music_from_folder("music")
        
        pygame.mixer.music.set_volume(self.volume)
    
    def load_music_from_folder(self, folder_path):
        """Carga archivos de música desde una carpeta"""
        if not os.path.exists(folder_path):
            return
        
        self.music_folder = folder_path
        self.music_files = []
        
        # Extensiones de audio soportadas
        supported_formats = ['.mp3', '.wav', '.ogg']
        
        for file in os.listdir(folder_path):
            if any(file.lower().endswith(ext) for ext in supported_formats):
                self.music_files.append(os.path.join(folder_path, file))
        
        if self.music_files:
            self.current_song_index = 0
            self.play_current_song()
    
    def select_music_folder(self):
        """Abre un diálogo para seleccionar carpeta de música"""
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal
        
        folder_path = filedialog.askdirectory(
            title="Seleccionar carpeta de música",
            initialdir=os.getcwd()
        )
        
        root.destroy()
        
        if folder_path:
            self.load_music_from_folder(folder_path)
    
    def play_current_song(self):
        """Reproduce la canción actual"""
        if self.music_files and 0 <= self.current_song_index < len(self.music_files):
            try:
                pygame.mixer.music.load(self.music_files[self.current_song_index])
                pygame.mixer.music.play(-1)  # -1 para loop infinito
                self.is_playing = True
                print(f"Reproduciendo: {os.path.basename(self.music_files[self.current_song_index])}")
            except pygame.error as e:
                print(f"Error al reproducir música: {e}")
                self.next_song()

    def next_song(self):
        """Cambia a la siguiente canción"""
        if self.music_files:
            self.current_song_index = (self.current_song_index + 1) % len(self.music_files)
            self.play_current_song()
    
    def previous_song(self):
        """Cambia a la canción anterior"""
        if self.music_files:
            self.current_song_index = (self.current_song_index - 1) % len(self.music_files)
            self.play_current_song()
    
    def toggle_pause(self):
        """Pausa o reanuda la música"""
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
    
    def set_volume(self, volume):
        """Establece el volumen (0.0 a 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
    
    def get_current_song(self):
        """Obtiene el nombre de la canción actual"""
        if self.music_files and 0 <= self.current_song_index < len(self.music_files):
            return os.path.basename(self.music_files[self.current_song_index])
        return None
    
    def get_current_bpm(self, default=120):
        """Devuelve el BPM de la canción actual si está definida, si no el default."""
        # Puedes definir un diccionario aquí para asociar archivos a BPMs
        bpm_map = {
            "menu.mp3": 120,
            "menu.ogg": 120,
            "menu1.mp3": 128,
            "menu2.mp3": 140,
            # Agrega más si tienes más canciones de menú
        }
        song = self.get_current_song()
        if song and song in bpm_map:
            return bpm_map[song]
        return default

    def get_menu_songs(self):
        """Devuelve la lista de archivos de música de menú (nombre empieza con 'menu')"""
        return [f for f in self.music_files if os.path.basename(f).lower().startswith("menu")]

    def get_current_menu_song_name(self):
        """Devuelve el nombre de la canción de menú actual, o None si no es de menú"""
        menu_songs = self.get_menu_songs()
        if menu_songs:
            idx = self.get_menu_song_index()
            if 0 <= idx < len(menu_songs):
                return os.path.basename(menu_songs[idx])
        return None

    def get_menu_song_index(self):
        """Devuelve el índice de la canción de menú actual en la lista de canciones de menú"""
        menu_songs = self.get_menu_songs()
        if not menu_songs:
            return -1
        current = self.get_current_song()
        for i, f in enumerate(menu_songs):
            if os.path.basename(f) == current:
                return i
        return 0

    def play_menu_song_by_index(self, idx):
        """Reproduce la canción de menú en la posición idx"""
        menu_songs = self.get_menu_songs()
        if menu_songs and 0 <= idx < len(menu_songs):
            self.current_song_index = self.music_files.index(menu_songs[idx])
            self.play_current_song()

    def play_menu_music(self):
        """Reproduce la música de menú (primer archivo que empiece con 'menu')"""
        menu_songs = self.get_menu_songs()
        if menu_songs:
            self.current_song_index = self.music_files.index(menu_songs[0])
            self.play_current_song()
        else:
            pygame.mixer.music.stop()
            self.is_playing = False

    def play_ingame_music(self):
        """Reproduce la música de juego (primer archivo que NO empiece con 'menu')"""
        ingame_songs = [f for f in self.music_files if not os.path.basename(f).lower().startswith("menu")]
        if ingame_songs:
            self.current_song_index = self.music_files.index(ingame_songs[0])
            self.play_current_song()
        else:
            pygame.mixer.music.stop()
            self.is_playing = False

    def play_premenu_music(self):
        """Reproduce la música de pre-menú (primer archivo que empiece con 'premenu')"""
        premenu_songs = [f for f in self.music_files if os.path.basename(f).lower().startswith("premenu")]
        if premenu_songs:
            self.current_song_index = self.music_files.index(premenu_songs[0])
            self.play_current_song()
        else:
            # Si no hay canciones de pre-menú, intentar con música de menú
            self.play_menu_music()

    def update(self):
        """Actualiza el estado de la música (llamar en el loop principal)"""
        # Ya no es necesario controlar el loop manualmente, porque play(-1) hace loop automático
        pass