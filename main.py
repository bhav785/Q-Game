import arcade
import random
from typing import List, Tuple, Optional, Dict
from enum import Enum
import math


SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Q Game"

TILE_SIZE = 50
BOARD_OFFSET_X = 400
BOARD_OFFSET_Y = 300
HAND_Y = 80

# Colors
BG_COLOR = (20, 25, 35)
PANEL_COLOR = (40, 45, 60)
TEXT_COLOR = (220, 220, 220)
PLAYER_COLOR = (100, 200, 100)
AI_COLOR = (200, 100, 100)
ACCENT_COLOR = (0, 150, 255)
VALID_COLOR = (100, 255, 150, 100)


class Shape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    STAR = "star"
    DIAMOND = "diamond"
    CLOVER = "clover"
    CROSS = "cross"

class Color(Enum):
    RED = (255, 50, 50)
    BLUE = (50, 150, 255)
    GREEN = (50, 200, 50)
    YELLOW = (255, 220, 50)
    PURPLE = (180, 70, 220)
    ORANGE = (255, 150, 50)

class GameState(Enum):
    PLAYER_TURN = 0
    AI_TURN = 1
    GAME_OVER = 2

# ============================================================================
# TILE CLASS
# ============================================================================
class Tile:
    def __init__(self, shape: Shape, color: Color):
        self.shape = shape
        self.color = color
    
    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return self.shape == other.shape and self.color == other.color
    
    def __hash__(self):
        return hash((self.shape, self.color))
    
    def __repr__(self):
        return f"Tile({self.shape.name}, {self.color.name})"

# ============================================================================
# GAME ENGINE - SIMPLIFIED AND PROPER
# ============================================================================
class QGameEngine:
    def __init__(self):
        self.board = {}  # Dict of (row, col) -> Tile
        self.players = [
            {"name": "Player", "hand": [], "score": 0, "is_ai": False},
            {"name": "AI", "hand": [], "score": 0, "is_ai": True}
        ]
        self.current_player = 0
        self.game_state = GameState.PLAYER_TURN
        self.tile_bag = self.create_tile_bag()
        
        # Deal initial hands
        for player in self.players:
            player["hand"] = [self.draw_tile() for _ in range(6)]
        
        # Place first tile in center
        if self.tile_bag:
            first_tile = self.tile_bag.pop()
            self.board[(0, 0)] = first_tile
    
    def create_tile_bag(self) -> List[Tile]:
        """Create 3 copies of each tile combination"""
        bag = []
        for shape in Shape:
            for color in Color:
                for _ in range(3):
                    bag.append(Tile(shape, color))
        random.shuffle(bag)
        return bag
    
    def draw_tile(self) -> Optional[Tile]:
        """Draw one tile from the bag"""
        return self.tile_bag.pop() if self.tile_bag else None
    
    def get_current_player(self):
        return self.players[self.current_player]
    
    def get_valid_positions(self) -> List[Tuple[int, int]]:
        """Get all empty positions adjacent to existing tiles"""
        if not self.board:
            return [(0, 0)]
        
        positions = set()
        for (row, col) in self.board.keys():
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                new_pos = (row + dr, col + dc)
                if new_pos not in self.board:
                    positions.add(new_pos)
        return list(positions)
    
    def is_valid_placement(self, placements: List[Tuple[int, int, Tile]]) -> Tuple[bool, str]:
        """Check if placement is valid according to Q game rules"""
        if not placements:
            return False, "No placements"
        
        player = self.get_current_player()
        
        # Check player has the tiles
        hand_copy = player["hand"].copy()
        for _, _, tile in placements:
            if tile in hand_copy:
                hand_copy.remove(tile)
            else:
                return False, "Don't have these tiles"
        
        # Check positions are empty
        for row, col, _ in placements:
            if (row, col) in self.board:
                return False, "Position occupied"
        
        # Check all in same row or column
        rows = {pos[0] for pos in placements}
        cols = {pos[1] for pos in placements}
        
        if len(rows) > 1 and len(cols) > 1:
            return False, "Must be in same row or column"
        
        # Check contiguous
        if len(placements) > 1:
            if len(rows) == 1:  # Horizontal
                sorted_cols = sorted([pos[1] for pos in placements])
                for i in range(len(sorted_cols) - 1):
                    if sorted_cols[i + 1] - sorted_cols[i] != 1:
                        return False, "Tiles must be adjacent"
            else:  # Vertical
                sorted_rows = sorted([pos[0] for pos in placements])
                for i in range(len(sorted_rows) - 1):
                    if sorted_rows[i + 1] - sorted_rows[i] != 1:
                        return False, "Tiles must be adjacent"
        
        # Check connection to board (unless first move)
        if len(self.board) > 0:
            connected = False
            for row, col, _ in placements:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if (row + dr, col + dc) in self.board:
                        connected = True
                        break
                if connected:
                    break
            if not connected:
                return False, "Must connect to existing tiles"
        
        # Check line rules after placement
        temp_board = self.board.copy()
        for row, col, tile in placements:
            temp_board[(row, col)] = tile
        
        # Check each line created/modified by this placement
        for row, col, _ in placements:
            # Check row
            row_tiles = []
            c = col
            while (row, c) in temp_board:
                c -= 1
            c += 1
            while (row, c) in temp_board:
                row_tiles.append(temp_board[(row, c)])
                c += 1
            
            if len(row_tiles) > 1:
                valid, msg = self.validate_line(row_tiles)
                if not valid:
                    return False, f"Row invalid: {msg}"
            
            # Check column
            col_tiles = []
            r = row
            while (r, col) in temp_board:
                r -= 1
            r += 1
            while (r, col) in temp_board:
                col_tiles.append(temp_board[(r, col)])
                r += 1
            
            if len(col_tiles) > 1:
                valid, msg = self.validate_line(col_tiles)
                if not valid:
                    return False, f"Column invalid: {msg}"
        
        return True, "Valid"
    
    def validate_line(self, tiles: List[Tile]) -> Tuple[bool, str]:
        """Validate a line according to Q game rules"""
        colors = [tile.color for tile in tiles]
        shapes = [tile.shape for tile in tiles]
        
        # Option 1: All same color, all different shapes
        if len(set(colors)) == 1 and len(set(shapes)) == len(shapes):
            return True, ""
        
        # Option 2: All same shape, all different colors
        if len(set(shapes)) == 1 and len(set(colors)) == len(colors):
            return True, ""
        
        return False, "Must be all same color with unique shapes OR all same shape with unique colors"
    
    def calculate_score(self, placements: List[Tuple[int, int, Tile]]) -> int:
        """Calculate score for this placement"""
        temp_board = self.board.copy()
        for row, col, tile in placements:
            temp_board[(row, col)] = tile
        
        score = 0
        scored_lines = set()
        
        for row, col, _ in placements:
            # Score row
            row_tiles = []
            c = col
            while (row, c) in temp_board:
                c -= 1
            c += 1
            start_col = c
            while (row, c) in temp_board:
                row_tiles.append(temp_board[(row, c)])
                c += 1
            
            if len(row_tiles) > 1:
                line_key = ('row', row, start_col)
                if line_key not in scored_lines:
                    score += len(row_tiles)
                    scored_lines.add(line_key)
            
            # Score column
            col_tiles = []
            r = row
            while (r, col) in temp_board:
                r -= 1
            r += 1
            start_row = r
            while (r, col) in temp_board:
                col_tiles.append(temp_board[(r, col)])
                r += 1
            
            if len(col_tiles) > 1:
                line_key = ('col', col, start_row)
                if line_key not in scored_lines:
                    score += len(col_tiles)
                    scored_lines.add(line_key)
        
        # Single tile gets 1 point
        if len(placements) == 1 and score == 0:
            score = 1
        
        return score
    
    def make_move(self, placements: List[Tuple[int, int, Tile]]) -> Tuple[bool, int, str]:
        """Execute a move"""
        valid, msg = self.is_valid_placement(placements)
        if not valid:
            return False, 0, msg
        
        player = self.get_current_player()
        
        # Remove tiles from hand
        for _, _, tile in placements:
            player["hand"].remove(tile)
        
        # Place tiles on board
        for row, col, tile in placements:
            self.board[(row, col)] = tile
        
        # Calculate score
        score = self.calculate_score(placements)
        player["score"] += score
        
        # Draw new tiles
        for _ in range(len(placements)):
            new_tile = self.draw_tile()
            if new_tile:
                player["hand"].append(new_tile)
        
        # Switch turns
        self.current_player = 1 - self.current_player
        self.game_state = GameState.AI_TURN if self.players[self.current_player]["is_ai"] else GameState.PLAYER_TURN
        
        # Check game over
        if len(player["hand"]) == 0 and not self.tile_bag:
            self.game_state = GameState.GAME_OVER
        
        return True, score, "Success"
    
    def ai_make_move(self) -> Tuple[bool, int, str]:
        """AI makes a move"""
        player = self.players[1]  # AI player
        valid_positions = self.get_valid_positions()
        
        # Try to place single tiles first
        for tile in player["hand"]:
            for pos in valid_positions:
                placement = [(pos[0], pos[1], tile)]
                valid, _ = self.is_valid_placement(placement)
                if valid:
                    return self.make_move(placement)
        
        # If no single moves, pass
        self.current_player = 1 - self.current_player
        self.game_state = GameState.PLAYER_TURN
        return False, 0, "AI passed"

# ============================================================================
# GAME VIEW - CLEAN AND WORKING
# ============================================================================
class QGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(BG_COLOR)
        
        self.game = QGameEngine()
        self.selected_tile = None
        self.placement_positions = []
        self.message = ""
        self.message_timer = 0
        
        # UI state
        self.hover_pos = None
    
    def on_draw(self):
        self.clear()
        self.draw_game_board()
        self.draw_ui()
        self.draw_message()
        
        if self.game.game_state == GameState.GAME_OVER:
            self.draw_game_over()
    
    def draw_game_board(self):
        # Draw board background
        board_size = 400
        arcade.draw_rectangle_filled(BOARD_OFFSET_X, BOARD_OFFSET_Y, board_size, board_size, PANEL_COLOR)
        
        # Draw grid and tiles
        grid_half = 4  # Show 9x9 grid
        for row in range(-grid_half, grid_half + 1):
            for col in range(-grid_half, grid_half + 1):
                x = BOARD_OFFSET_X + col * TILE_SIZE
                y = BOARD_OFFSET_Y + row * TILE_SIZE
                
                # Draw grid cell
                arcade.draw_rectangle_outline(x, y, TILE_SIZE - 2, TILE_SIZE - 2, (80, 80, 100), 1)
                
                # Draw tile if exists
                if (row, col) in self.game.board:
                    tile = self.game.board[(row, col)]
                    self.draw_tile(x, y, tile)
                
                # Highlight valid positions
                if (self.game.game_state == GameState.PLAYER_TURN and 
                    self.selected_tile and 
                    (row, col) in self.game.get_valid_positions()):
                    arcade.draw_rectangle_filled(x, y, TILE_SIZE - 10, TILE_SIZE - 10, VALID_COLOR)
                
                # Highlight hover position
                if self.hover_pos == (row, col) and self.selected_tile:
                    arcade.draw_rectangle_outline(x, y, TILE_SIZE - 2, TILE_SIZE - 2, ACCENT_COLOR, 2)
        
        # Draw placement preview
        for row, col, tile in self.placement_positions:
            x = BOARD_OFFSET_X + col * TILE_SIZE
            y = BOARD_OFFSET_Y + row * TILE_SIZE
            arcade.draw_rectangle_filled(x, y, TILE_SIZE - 4, TILE_SIZE - 4, (255, 255, 0, 100))
            self.draw_tile(x, y, tile)
    
    def draw_tile(self, x, y, tile, size_ratio=0.7):
        """Draw a tile with its shape and color"""
        color = tile.color.value
        size = (TILE_SIZE - 10) * size_ratio
        
        # Tile background
        arcade.draw_rectangle_filled(x, y, TILE_SIZE - 4, TILE_SIZE - 4, (240, 240, 240))
        
        # Draw shape
        if tile.shape == Shape.CIRCLE:
            arcade.draw_circle_filled(x, y, size / 2, color)
        elif tile.shape == Shape.SQUARE:
            arcade.draw_rectangle_filled(x, y, size, size, color)
        elif tile.shape == Shape.STAR:
            self.draw_star(x, y, size / 2, color)
        elif tile.shape == Shape.DIAMOND:
            points = [(x, y + size/2), (x + size/2, y), (x, y - size/2), (x - size/2, y)]
            arcade.draw_polygon_filled(points, color)
        elif tile.shape == Shape.CLOVER:
            self.draw_clover(x, y, size / 3, color)
        elif tile.shape == Shape.CROSS:
            arcade.draw_rectangle_filled(x, y, size * 0.7, size * 0.2, color)
            arcade.draw_rectangle_filled(x, y, size * 0.2, size * 0.7, color)
        
        # Border
        arcade.draw_rectangle_outline(x, y, TILE_SIZE - 4, TILE_SIZE - 4, (0, 0, 0), 1)
    
    def draw_star(self, x, y, size, color):
        points = []
        for i in range(10):
            angle = math.pi / 2 + i * 2 * math.pi / 10
            r = size if i % 2 == 0 else size / 2
            points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
        arcade.draw_polygon_filled(points, color)
    
    def draw_clover(self, x, y, size, color):
        arcade.draw_circle_filled(x, y + size, size, color)
        arcade.draw_circle_filled(x - size, y, size, color)
        arcade.draw_circle_filled(x + size, y, size, color)
        arcade.draw_circle_filled(x, y - size, size, color)
    
    def draw_ui(self):
        # Draw scores
        arcade.draw_text("SCORES", 100, SCREEN_HEIGHT - 80, TEXT_COLOR, 20, bold=True)
        
        player = self.game.players[0]
        ai = self.game.players[1]
        
        arcade.draw_text(f"Player: {player['score']}", 100, SCREEN_HEIGHT - 120, PLAYER_COLOR, 16)
        arcade.draw_text(f"AI: {ai['score']}", 100, SCREEN_HEIGHT - 150, AI_COLOR, 16)
        
        # Draw turn indicator
        turn_text = "Your Turn" if self.game.game_state == GameState.PLAYER_TURN else "AI's Turn"
        turn_color = PLAYER_COLOR if self.game.game_state == GameState.PLAYER_TURN else AI_COLOR
        arcade.draw_text(turn_text, 100, SCREEN_HEIGHT - 200, turn_color, 18, bold=True)
        
        # Draw hand
        if self.game.game_state == GameState.PLAYER_TURN:
            self.draw_hand()
    
    def draw_hand(self):
        player = self.game.players[0]
        
        arcade.draw_text("YOUR HAND", SCREEN_WIDTH // 2, 150, TEXT_COLOR, 16, bold=True, anchor_x="center")
        
        if not player["hand"]:
            arcade.draw_text("No tiles!", SCREEN_WIDTH // 2, 120, TEXT_COLOR, 14, anchor_x="center")
            return
        
        start_x = SCREEN_WIDTH // 2 - (len(player["hand"]) * (TILE_SIZE + 10)) // 2
        for i, tile in enumerate(player["hand"]):
            x = start_x + i * (TILE_SIZE + 10)
            y = 100
            
            # Highlight selected tile
            if tile == self.selected_tile:
                arcade.draw_rectangle_filled(x, y, TILE_SIZE + 8, TILE_SIZE + 8, (255, 255, 0, 100))
                arcade.draw_rectangle_outline(x, y, TILE_SIZE + 8, TILE_SIZE + 8, ACCENT_COLOR, 2)
            
            self.draw_tile(x, y, tile, 0.8)
            
            # Number
            arcade.draw_text(str(i + 1), x - TILE_SIZE//2 + 8, y + TILE_SIZE//2 - 8, 
                           (0, 0, 0), 12, bold=True)
        
        # Draw buttons
        self.draw_buttons()
    
    def draw_buttons(self):
        buttons = [
            ("PLACE TILES", SCREEN_WIDTH // 2 - 150, 40, self.place_tiles),
            ("CLEAR", SCREEN_WIDTH // 2, 40, self.clear_selection),
            ("PASS", SCREEN_WIDTH // 2 + 150, 40, self.pass_turn)
        ]
        
        for text, x, y, _ in buttons:
            color = PLAYER_COLOR if text == "PLACE TILES" else ACCENT_COLOR
            arcade.draw_rectangle_filled(x, y, 120, 30, color)
            arcade.draw_rectangle_outline(x, y, 120, 30, TEXT_COLOR, 2)
            arcade.draw_text(text, x, y, (255, 255, 255), 12, anchor_x="center", anchor_y="center", bold=True)
    
    def draw_message(self):
        if self.message and self.message_timer > 0:
            alpha = min(255, int(self.message_timer * 255))
            arcade.draw_text(self.message, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, 
                           (255, 255, 255, alpha), 16, anchor_x="center", bold=True)
    
    def draw_game_over(self):
        # Overlay
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 
                                  SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 200))
        
        # Panel
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 400, 300, PANEL_COLOR)
        arcade.draw_rectangle_outline(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 400, 300, ACCENT_COLOR, 3)
        
        # Winner
        winner = max(self.game.players, key=lambda p: p["score"])
        arcade.draw_text("GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100, 
                       ACCENT_COLOR, 32, anchor_x="center", bold=True)
        arcade.draw_text(f"{winner['name']} Wins!", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
                       PLAYER_COLOR if winner["name"] == "Player" else AI_COLOR, 24, anchor_x="center")
        
        # Scores
        y = SCREEN_HEIGHT // 2
        for player in self.game.players:
            color = PLAYER_COLOR if player["name"] == "Player" else AI_COLOR
            arcade.draw_text(f"{player['name']}: {player['score']}", 
                           SCREEN_WIDTH // 2, y, color, 20, anchor_x="center")
            y -= 40
        
        arcade.draw_text("Click to play again", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80,
                       TEXT_COLOR, 16, anchor_x="center")
    
    def show_message(self, text):
        self.message = text
        self.message_timer = 3.0
    
    def on_mouse_motion(self, x, y, dx, dy):
        # Update hover position
        if self.game.game_state == GameState.PLAYER_TURN and self.selected_tile:
            grid_half = 4
            for row in range(-grid_half, grid_half + 1):
                for col in range(-grid_half, grid_half + 1):
                    tile_x = BOARD_OFFSET_X + col * TILE_SIZE
                    tile_y = BOARD_OFFSET_Y + row * TILE_SIZE
                    
                    if (abs(x - tile_x) < TILE_SIZE // 2 and 
                        abs(y - tile_y) < TILE_SIZE // 2):
                        self.hover_pos = (row, col)
                        return
            self.hover_pos = None
    
    def on_mouse_press(self, x, y, button, modifiers):
        if self.game.game_state == GameState.GAME_OVER:
            self.__init__()  # Restart game
            return
        
        if self.game.game_state == GameState.AI_TURN:
            # Let AI make move
            success, score, msg = self.game.ai_make_move()
            if success:
                self.show_message(f"AI placed tiles! Score: +{score}")
            else:
                self.show_message("AI passed turn")
            return
        
        # Player's turn
        if self.check_hand_click(x, y):
            return
        
        if self.check_button_click(x, y):
            return
        
        # Board click for placement
        if self.selected_tile and self.hover_pos:
            row, col = self.hover_pos
            if (row, col) in self.game.get_valid_positions():
                self.placement_positions.append((row, col, self.selected_tile))
                self.selected_tile = None
                self.show_message(f"Tile placed at ({row}, {col})")
    
    def check_hand_click(self, x, y) -> bool:
        if not (70 <= y <= 130):  # Hand area
            return False
        
        player = self.game.players[0]
        start_x = SCREEN_WIDTH // 2 - (len(player["hand"]) * (TILE_SIZE + 10)) // 2
        
        for i, tile in enumerate(player["hand"]):
            tile_x = start_x + i * (TILE_SIZE + 10)
            if abs(x - tile_x) < TILE_SIZE // 2:
                if tile == self.selected_tile:
                    self.selected_tile = None
                    self.show_message("Tile deselected")
                else:
                    self.selected_tile = tile
                    self.show_message(f"Selected tile {i + 1}")
                return True
        return False
    
    def check_button_click(self, x, y) -> bool:
        if not (25 <= y <= 55):  # Button area
            return False
        
        buttons = [
            (SCREEN_WIDTH // 2 - 150, 40, self.place_tiles),
            (SCREEN_WIDTH // 2, 40, self.clear_selection),
            (SCREEN_WIDTH // 2 + 150, 40, self.pass_turn)
        ]
        
        for btn_x, btn_y, callback in buttons:
            if abs(x - btn_x) < 60 and abs(y - btn_y) < 15:
                callback()
                return True
        return False
    
    def place_tiles(self):
        if not self.placement_positions:
            self.show_message("No tiles placed on board!")
            return
        
        success, score, msg = self.game.make_move(self.placement_positions)
        if success:
            self.show_message(f"Tiles placed! Score: +{score}")
            self.placement_positions.clear()
        else:
            self.show_message(f"Invalid: {msg}")
    
    def clear_selection(self):
        if self.placement_positions:
            # Return tiles to hand selection
            self.selected_tile = self.placement_positions[0][2]
            self.placement_positions.clear()
            self.show_message("Placement cleared")
    
    def pass_turn(self):
        self.game.current_player = 1 - self.game.current_player
        self.game.game_state = GameState.AI_TURN
        self.selected_tile = None
        self.placement_positions.clear()
        self.show_message("Turn passed to AI")
    
    def on_key_press(self, key, modifiers):
        if self.game.game_state != GameState.PLAYER_TURN:
            return
        
        # Number keys for tile selection
        if arcade.key.KEY_1 <= key <= arcade.key.KEY_6:
            index = key - arcade.key.KEY_1
            player = self.game.players[0]
            if index < len(player["hand"]):
                tile = player["hand"][index]
                if tile == self.selected_tile:
                    self.selected_tile = None
                else:
                    self.selected_tile = tile
    
    def on_update(self, delta_time):
        if self.message_timer > 0:
            self.message_timer -= delta_time

def main():
    game = QGame()
    arcade.run()

if __name__ == "__main__":
    main()