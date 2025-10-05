import arcade
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
import math

# Constants
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
SCREEN_TITLE = "Qwirkle Game"
TILE_SIZE = 50
TILE_MARGIN = 5
HAND_Y = 50
BOARD_OFFSET_X = 200
BOARD_OFFSET_Y = 200

class Shape(Enum):
    STAR = "star"
    STAR8 = "8star"
    SQUARE = "square"
    CIRCLE = "circle"
    CLOVER = "clover"
    DIAMOND = "diamond"

class Color(Enum):
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 165, 0)
    PURPLE = (160, 32, 240)

@dataclass(frozen=True)
class Tile:
    shape: Shape
    color: Color
    
    def matches(self, other: 'Tile', by_shape: bool) -> bool:
        if by_shape:
            return self.shape == other.shape
        return self.color == other.color

class TileCollection:
    def __init__(self):
        self.tiles = []
        for shape in Shape:
            for color in Color:
                self.tiles.extend([Tile(shape, color)] * 30)
        random.shuffle(self.tiles)
    
    def draw(self, count: int) -> List[Tile]:
        drawn = self.tiles[:count]
        self.tiles = self.tiles[count:]
        return drawn
    
    def return_tiles(self, tiles: List[Tile]):
        self.tiles.extend(tiles)
    
    def remaining(self) -> int:
        return len(self.tiles)

class Board:
    def __init__(self):
        self.tiles = {}  # {(row, col): Tile}
        self.min_row = 0
        self.max_row = 0
        self.min_col = 0
        self.max_col = 0
    
    def place_tile(self, row: int, col: int, tile: Tile):
        self.tiles[(row, col)] = tile
        if not self.tiles or len(self.tiles) == 1:
            self.min_row = self.max_row = row
            self.min_col = self.max_col = col
        else:
            self.min_row = min(self.min_row, row)
            self.max_row = max(self.max_row, row)
            self.min_col = min(self.min_col, col)
            self.max_col = max(self.max_col, col)
    
    def get_tile(self, row: int, col: int) -> Optional[Tile]:
        return self.tiles.get((row, col))
    
    def is_empty(self) -> bool:
        return len(self.tiles) == 0
    
    def has_neighbor(self, row: int, col: int) -> bool:
        neighbors = [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]
        return any(pos in self.tiles for pos in neighbors)
    
    def get_line(self, row: int, col: int, horizontal: bool) -> List[Tuple[int, int, Tile]]:
        line = []
        if horizontal:
            c = col
            while (row, c-1) in self.tiles:
                c -= 1
            while (row, c) in self.tiles:
                line.append((row, c, self.tiles[(row, c)]))
                c += 1
        else:
            r = row
            while (r-1, col) in self.tiles:
                r -= 1
            while (r, col) in self.tiles:
                line.append((r, col, self.tiles[(r, col)]))
                r += 1
        return line

class Player:
    def __init__(self, name: str, is_bot: bool = False):
        self.name = name
        self.hand = []
        self.score = 0
        self.is_bot = is_bot
        self.passed = False

class Bot:
    @staticmethod
    def choose_action(player: Player, board: Board, tile_collection: TileCollection):
        # Simple bot strategy: try to place tiles, otherwise pass
        if not player.hand:
            return "pass", []
        
        # Try to find valid placements
        if board.is_empty():
            return "place", [(0, 0, player.hand[0])]
        
        # Try placing each tile adjacent to existing tiles
        for tile in player.hand:
            for (row, col) in list(board.tiles.keys()):
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_row, new_col = row + dr, col + dc
                    if (new_row, new_col) not in board.tiles:
                        # Check if placement would be valid
                        placement = [(new_row, new_col, tile)]
                        if Game.validate_placement(board, placement):
                            return "place", placement
        
        # If can't place, exchange if possible
        if tile_collection.remaining() >= len(player.hand):
            return "exchange", []
        
        return "pass", []

class Game:
    def __init__(self, num_players: int, bot_players: List[int]):
        self.tile_collection = TileCollection()
        self.board = Board()
        self.players = []
        
        for i in range(num_players):
            is_bot = i in bot_players
            name = f"Bot {i+1}" if is_bot else f"Player {i+1}"
            player = Player(name, is_bot)
            player.hand = self.tile_collection.draw(6)
            self.players.append(player)
        
        # Place first tile
        first_tile = self.tile_collection.draw(1)[0]
        self.board.place_tile(0, 0, first_tile)
        
        self.current_player_idx = 0
        self.game_over = False
        self.winner = None
        self.message = f"{self.players[0].name}'s turn"
    
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]
    
    def next_player(self):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        player = self.current_player()
        self.message = f"{player.name}'s turn"
    
    @staticmethod
    def validate_placement(board: Board, placements: List[Tuple[int, int, Tile]]) -> bool:
        if not placements:
            return False
        
        # Check all placements are in same row or column
        rows = [p[0] for p in placements]
        cols = [p[1] for p in placements]
        same_row = len(set(rows)) == 1
        same_col = len(set(cols)) == 1
        
        if not (same_row or same_col):
            return False
        
        # For each placement
        for row, col, tile in placements:
            if (row, col) in board.tiles:
                return False
            
            # Must have neighbor (or board is empty)
            if not board.is_empty() and not board.has_neighbor(row, col):
                # Check if any other placement is adjacent
                adjacent = False
                for r2, c2, _ in placements:
                    if (r2, c2) != (row, col):
                        if abs(r2-row) + abs(c2-col) == 1:
                            adjacent = True
                            break
                if not adjacent:
                    return False
        
        # Validate matches in lines
        temp_board = {pos: tile for pos, tile in board.tiles.items()}
        for row, col, tile in placements:
            temp_board[(row, col)] = tile
        
        for row, col, tile in placements:
            # Check horizontal line
            h_line = []
            c = col
            while (row, c-1) in temp_board:
                c -= 1
            while (row, c) in temp_board:
                h_line.append(temp_board[(row, c)])
                c += 1
            
            if len(h_line) > 1:
                if not Game.validate_line(h_line):
                    return False
            
            # Check vertical line
            v_line = []
            r = row
            while (r-1, col) in temp_board:
                r -= 1
            while (r, col) in temp_board:
                v_line.append(temp_board[(r, col)])
                r += 1
            
            if len(v_line) > 1:
                if not Game.validate_line(v_line):
                    return False
        
        return True
    
    @staticmethod
    def validate_line(tiles: List[Tile]) -> bool:
        if len(tiles) <= 1:
            return True
        
        if len(tiles) > 6:
            return False
        
        # Check if all same shape or all same color
        shapes = set(t.shape for t in tiles)
        colors = set(t.color for t in tiles)
        
        if len(shapes) == 1 and len(colors) == len(tiles):
            return True
        if len(colors) == 1 and len(shapes) == len(tiles):
            return True
        
        return False
    
    def calculate_score(self, placements: List[Tuple[int, int, Tile]]) -> int:
        score = len(placements)
        qwirkle_bonus = 0
        
        for row, col, tile in placements:
            # Horizontal line
            h_line = self.board.get_line(row, col, True)
            if len(h_line) > 1:
                score += len(h_line)
                if len(h_line) == 6:
                    qwirkle_bonus += 6
            
            # Vertical line
            v_line = self.board.get_line(row, col, False)
            if len(v_line) > 1:
                score += len(v_line)
                if len(v_line) == 6:
                    qwirkle_bonus += 6
        
        # Bonus for using all tiles
        if len(self.current_player().hand) == len(placements):
            score += 6
        
        return score + qwirkle_bonus
    
    def execute_placement(self, placements: List[Tuple[int, int, Tile]]):
        player = self.current_player()
        
        for row, col, tile in placements:
            self.board.place_tile(row, col, tile)
            player.hand.remove(tile)
        
        score = self.calculate_score(placements)
        player.score += score
        
        # Draw new tiles
        draw_count = min(len(placements), self.tile_collection.remaining())
        player.hand.extend(self.tile_collection.draw(draw_count))
        
        self.message = f"{player.name} scored {score} points!"
        
        # Check end conditions
        if len(player.hand) == 0 or self.tile_collection.remaining() == 0:
            self.end_game()
        else:
            self.next_player()
    
    def execute_pass(self):
        player = self.current_player()
        player.passed = True
        self.message = f"{player.name} passed"
        
        # Check if all passed
        if all(p.passed for p in self.players):
            self.end_game()
        else:
            self.next_player()
    
    def execute_exchange(self):
        player = self.current_player()
        if self.tile_collection.remaining() < len(player.hand):
            self.message = "Not enough tiles to exchange!"
            return
        
        old_tiles = player.hand.copy()
        player.hand = self.tile_collection.draw(len(old_tiles))
        self.tile_collection.return_tiles(old_tiles)
        player.passed = False
        
        self.message = f"{player.name} exchanged tiles"
        self.next_player()
    
    def end_game(self):
        self.game_over = True
        winner = max(self.players, key=lambda p: p.score)
        self.winner = winner
        self.message = f"Game Over! {winner.name} wins with {winner.score} points!"

class QwirkleGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)
        
        self.game = None
        self.selected_tiles = []
        self.placements = []
        self.camera_x = 0
        self.camera_y = 0
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Create Text objects for better performance
        self.text_objects = {}
        
        self.setup_menu()
    
    def setup_menu(self):
        self.in_menu = True
        self.num_players = 2
        self.bot_players = []
    
    def start_game(self):
        self.in_menu = False
        self.game = Game(self.num_players, self.bot_players)
        
        # Process bot turns if starting player is bot
        if self.game.current_player().is_bot:
            self.process_bot_turn()
    
    def process_bot_turn(self):
        if self.game.game_over:
            return
        
        player = self.game.current_player()
        if not player.is_bot:
            return
        
        action, data = Bot.choose_action(player, self.game.board, self.game.tile_collection)
        
        if action == "place":
            self.game.execute_placement(data)
        elif action == "exchange":
            self.game.execute_exchange()
        else:
            self.game.execute_pass()
        
        # Continue if next player is also bot
        arcade.schedule(lambda dt: self.process_bot_turn(), 1.0)
    
    def draw_rectangle_filled(self, x, y, width, height, color):
        """Draw filled rectangle using polygon"""
        arcade.draw_polygon_filled([
            (x - width/2, y - height/2),
            (x + width/2, y - height/2),
            (x + width/2, y + height/2),
            (x - width/2, y + height/2)
        ], color)
    
    def draw_rectangle_outline(self, x, y, width, height, color, border_width):
        """Draw rectangle outline using lines"""
        half_w = width / 2
        half_h = height / 2
        arcade.draw_line(x - half_w, y - half_h, x + half_w, y - half_h, color, border_width)
        arcade.draw_line(x + half_w, y - half_h, x + half_w, y + half_h, color, border_width)
        arcade.draw_line(x + half_w, y + half_h, x - half_w, y + half_h, color, border_width)
        arcade.draw_line(x - half_w, y + half_h, x - half_w, y - half_h, color, border_width)
    
    def draw_tile(self, x, y, tile: Tile, selected=False):
        # Draw tile background
        color = tile.color.value
        if selected:
            self.draw_rectangle_filled(x, y, TILE_SIZE+4, TILE_SIZE+4, arcade.color.WHITE)
        self.draw_rectangle_filled(x, y, TILE_SIZE, TILE_SIZE, color)
        self.draw_rectangle_outline(x, y, TILE_SIZE, TILE_SIZE, arcade.color.BLACK, 2)
        
        # Draw shape
        shape_color = arcade.color.BLACK if sum(color) > 400 else arcade.color.WHITE
        size = TILE_SIZE * 0.35
        
        if tile.shape == Shape.CIRCLE:
            arcade.draw_circle_filled(x, y, size, shape_color)
        elif tile.shape == Shape.SQUARE:
            self.draw_rectangle_filled(x, y, size*2, size*2, shape_color)
        elif tile.shape == Shape.DIAMOND:
            arcade.draw_polygon_filled([
                (x, y+size), (x+size, y), (x, y-size), (x-size, y)
            ], shape_color)
        elif tile.shape == Shape.STAR:
            self.draw_star(x, y, size, 4, shape_color)
        elif tile.shape == Shape.STAR8:
            self.draw_star(x, y, size, 8, shape_color)
        elif tile.shape == Shape.CLOVER:
            self.draw_clover(x, y, size*0.5, shape_color)
    
    def draw_star(self, x, y, radius, points, color):
        outer_radius = radius
        inner_radius = radius * 0.4
        angle_step = math.pi / points
        
        vertices = []
        for i in range(points * 2):
            angle = i * angle_step - math.pi / 2
            r = outer_radius if i % 2 == 0 else inner_radius
            vertices.append((x + r * math.cos(angle), y + r * math.sin(angle)))
        
        arcade.draw_polygon_filled(vertices, color)
    
    def draw_clover(self, x, y, radius, color):
        # Four circles arranged in clover pattern
        for dx, dy in [(0, radius), (radius, 0), (0, -radius), (-radius, 0)]:
            arcade.draw_circle_filled(x+dx, y+dy, radius, color)
    
    def on_draw(self):
        self.clear()
        
        if self.in_menu:
            self.draw_menu()
        else:
            self.draw_game()
    
    def draw_menu(self):
        arcade.draw_text("QWIRKLE", SCREEN_WIDTH//2, SCREEN_HEIGHT-100,
                        arcade.color.WHITE, 60, anchor_x="center", bold=True)
        
        arcade.draw_text(f"Number of Players: {self.num_players}", SCREEN_WIDTH//2, 500,
                        arcade.color.WHITE, 24, anchor_x="center")
        arcade.draw_text("Use UP/DOWN arrows to change", SCREEN_WIDTH//2, 470,
                        arcade.color.LIGHT_GRAY, 14, anchor_x="center")
        
        y = 400
        for i in range(self.num_players):
            is_bot = i in self.bot_players
            player_type = "BOT" if is_bot else "HUMAN"
            arcade.draw_text(f"Player {i+1}: {player_type}", SCREEN_WIDTH//2, y,
                           arcade.color.WHITE, 20, anchor_x="center")
            arcade.draw_text(f"Press {i+1} to toggle", SCREEN_WIDTH//2, y-25,
                           arcade.color.LIGHT_GRAY, 12, anchor_x="center")
            y -= 60
        
        arcade.draw_text("Press SPACE to start", SCREEN_WIDTH//2, 150,
                        arcade.color.GREEN, 28, anchor_x="center", bold=True)
    
    def draw_game(self):
        # Draw board
        if not self.game.board.is_empty():
            for (row, col), tile in self.game.board.tiles.items():
                x = SCREEN_WIDTH//2 + col * (TILE_SIZE + TILE_MARGIN) - self.camera_x
                y = SCREEN_HEIGHT//2 + row * (TILE_SIZE + TILE_MARGIN) - self.camera_y
                self.draw_tile(x, y, tile)
        
        # Draw placement preview
        for row, col, tile in self.placements:
            x = SCREEN_WIDTH//2 + col * (TILE_SIZE + TILE_MARGIN) - self.camera_x
            y = SCREEN_HEIGHT//2 + row * (TILE_SIZE + TILE_MARGIN) - self.camera_y
            self.draw_rectangle_outline(x, y, TILE_SIZE+8, TILE_SIZE+8, arcade.color.YELLOW, 4)
            self.draw_tile(x, y, tile)
        
        # Draw player hand
        player = self.game.current_player()
        x_start = SCREEN_WIDTH//2 - (len(player.hand) * (TILE_SIZE + TILE_MARGIN))//2
        for i, tile in enumerate(player.hand):
            x = x_start + i * (TILE_SIZE + TILE_MARGIN)
            self.draw_tile(x, HAND_Y, tile, tile in self.selected_tiles)
        
        # Draw UI
        arcade.draw_text(self.game.message, 10, SCREEN_HEIGHT-30,
                        arcade.color.WHITE, 16, bold=True)
        
        # Draw scores
        y = SCREEN_HEIGHT - 60
        for p in self.game.players:
            is_current = p == player
            color = arcade.color.YELLOW if is_current else arcade.color.WHITE
            arcade.draw_text(f"{p.name}: {p.score}", 10, y, color, 14, bold=is_current)
            y -= 25
        
        arcade.draw_text(f"Tiles left: {self.game.tile_collection.remaining()}", 
                        SCREEN_WIDTH-150, SCREEN_HEIGHT-30, arcade.color.WHITE, 14)
        
        # Draw controls
        controls = [
            "Click tile to select/deselect",
            "Click board to place",
            "P: Pass | E: Exchange | C: Clear",
            "ENTER: Confirm placement",
            "Arrow keys: Pan camera"
        ]
        y = 150
        for text in controls:
            arcade.draw_text(text, 10, y, arcade.color.LIGHT_GRAY, 12)
            y -= 20
    
    def on_key_press(self, key, modifiers):
        if self.in_menu:
            if key == arcade.key.SPACE:
                self.start_game()
            elif key == arcade.key.UP:
                self.num_players = min(4, self.num_players + 1)
            elif key == arcade.key.DOWN:
                self.num_players = max(2, self.num_players - 1)
            elif arcade.key.KEY_1 <= key <= arcade.key.KEY_4:
                player_idx = key - arcade.key.KEY_1
                if player_idx < self.num_players:
                    if player_idx in self.bot_players:
                        self.bot_players.remove(player_idx)
                    else:
                        self.bot_players.append(player_idx)
        else:
            if self.game.game_over:
                return
            
            if self.game.current_player().is_bot:
                return
            
            if key == arcade.key.P:
                self.game.execute_pass()
                if self.game.current_player().is_bot:
                    self.process_bot_turn()
            elif key == arcade.key.E:
                self.game.execute_exchange()
                if self.game.current_player().is_bot:
                    self.process_bot_turn()
            elif key == arcade.key.C:
                self.placements.clear()
                self.selected_tiles.clear()
            elif key == arcade.key.ENTER:
                if self.placements and Game.validate_placement(self.game.board, self.placements):
                    self.game.execute_placement(self.placements)
                    self.placements.clear()
                    self.selected_tiles.clear()
                    if self.game.current_player().is_bot:
                        self.process_bot_turn()
                else:
                    self.game.message = "Invalid placement!"
            elif key == arcade.key.LEFT:
                self.camera_x -= 50
            elif key == arcade.key.RIGHT:
                self.camera_x += 50
            elif key == arcade.key.UP:
                self.camera_y += 50
            elif key == arcade.key.DOWN:
                self.camera_y -= 50
    
    def on_mouse_press(self, x, y, button, modifiers):
        if self.in_menu or self.game.game_over:
            return
        
        if self.game.current_player().is_bot:
            return
        
        # Check hand selection
        player = self.game.current_player()
        x_start = SCREEN_WIDTH//2 - (len(player.hand) * (TILE_SIZE + TILE_MARGIN))//2
        
        for i, tile in enumerate(player.hand):
            tile_x = x_start + i * (TILE_SIZE + TILE_MARGIN)
            if abs(x - tile_x) < TILE_SIZE//2 and abs(y - HAND_Y) < TILE_SIZE//2:
                if tile in self.selected_tiles:
                    self.selected_tiles.remove(tile)
                else:
                    self.selected_tiles.append(tile)
                return
        
        # Check board placement
        if self.selected_tiles:
            col = round((x - SCREEN_WIDTH//2 + self.camera_x) / (TILE_SIZE + TILE_MARGIN))
            row = round((y - SCREEN_HEIGHT//2 + self.camera_y) / (TILE_SIZE + TILE_MARGIN))
            
            if (row, col) not in self.game.board.tiles:
                tile = self.selected_tiles[0]
                self.placements.append((row, col, tile))
                self.selected_tiles.remove(tile)

def main():
    game = QwirkleGame()
    arcade.run()

if __name__ == "__main__":
    main()