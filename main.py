import arcade
import random
from typing import List, Tuple, Optional, Dict
from enum import Enum
import math
import time
import copy

# SMALLER SCREEN SIZE FOR LAPTOPS
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Q Game - Dark Edition"

TILE_SIZE = 35  # Smaller tiles
BOARD_OFFSET_X = 500
BOARD_OFFSET_Y = 350
HAND_Y = 80

# Dark Elegant Color Scheme
BG_COLOR = (25, 25, 35)  # Dark blue-gray
PANEL_COLOR = (40, 40, 55)  # Dark panel
TEXT_COLOR = (240, 240, 245)  # Light gray
PLAYER_COLOR = (100, 200, 255)  # Bright blue
AI_COLOR = (255, 100, 120)  # Coral red
ACCENT_COLOR = (180, 120, 255)  # Purple
VALID_COLOR = (100, 220, 150)  # Mint green
HIGHLIGHT_COLOR = (255, 220, 100)  # Gold
BUTTON_COLOR = (80, 100, 200)  # Blue
BUTTON_HOVER_COLOR = (100, 130, 230)  # Light blue
BUTTON_DISABLED_COLOR = (60, 60, 80)
SCORE_PANEL_COLOR = (35, 35, 50)
HAND_PANEL_COLOR = (35, 35, 50)
GRID_COLOR = (50, 50, 70)
GRID_HIGHLIGHT = (65, 65, 85)

class Shape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    STAR = "star"
    DIAMOND = "diamond"
    CLOVER = "clover"
    CROSS = "cross"

class Color(Enum):
    RED = (255, 100, 100)  # Bright red
    BLUE = (100, 180, 255)  # Bright blue
    GREEN = (100, 220, 100)  # Bright green
    YELLOW = (255, 220, 100)  # Gold
    PURPLE = (180, 120, 220)  # Purple
    ORANGE = (255, 160, 80)  # Orange

class GameState(Enum):
    PLAYER_TURN = 0
    AI_TURN = 1
    GAME_OVER = 2

# ============================================================================
# TILE CLASS (UNCHANGED)
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
# GAME ENGINE WITH MINIMAX AI (UNCHANGED)
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
        self.consecutive_passes = 0
        self.debug_info = ""
        
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
        if not self.tile_bag:
            return None
        return self.tile_bag.pop()

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
        
        # Check player has all the tiles
        hand_copy = player["hand"].copy()
        try:
            for _, _, tile in placements:
                hand_copy.remove(tile)
        except ValueError:
            return False, "Don't have these tiles"
        
        # Check positions are empty
        for row, col, _ in placements:
            if (row, col) in self.board:
                return False, "Position occupied"
        
        # Check all placements are in same row OR same column
        rows = {pos[0] for pos in placements}
        cols = {pos[1] for pos in placements}
        
        if len(rows) > 1 and len(cols) > 1:
            return False, "Must be in same row or column"
        
        # Check contiguous placement
        if len(placements) > 1:
            if len(rows) == 1:  # Horizontal line
                sorted_cols = sorted([pos[1] for pos in placements])
                for i in range(len(sorted_cols) - 1):
                    if sorted_cols[i + 1] - sorted_cols[i] != 1:
                        return False, "Tiles must be adjacent horizontally"
            else:  # Vertical line
                sorted_rows = sorted([pos[0] for pos in placements])
                for i in range(len(sorted_rows) - 1):
                    if sorted_rows[i + 1] - sorted_rows[i] != 1:
                        return False, "Tiles must be adjacent vertically"
        
        # Check connection to existing board
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
        
        # Validate all affected lines after placement
        temp_board = self.board.copy()
        for row, col, tile in placements:
            temp_board[(row, col)] = tile
        
        # Check each row and column that contains new placements
        for row, col, _ in placements:
            # Check the entire row containing this placement
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
            
            # Check the entire column containing this placement
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
        if len(tiles) < 2:
            return True, ""
        
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
        
        # Single tile gets 1 point if no lines scored
        if score == 0 and placements:
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
        
        # Reset consecutive passes
        self.consecutive_passes = 0
        
        # Switch turns
        self.current_player = 1 - self.current_player
        self.game_state = GameState.AI_TURN if self.players[self.current_player]["is_ai"] else GameState.PLAYER_TURN
        
        return True, score, "Success"

    def pass_turn(self):
        """Pass the current player's turn"""
        self.consecutive_passes += 1
        self.current_player = 1 - self.current_player
        self.game_state = GameState.AI_TURN if self.players[self.current_player]["is_ai"] else GameState.PLAYER_TURN
        
        # Check if game should end
        if self.consecutive_passes >= 2:
            self.game_state = GameState.GAME_OVER

    # ============================================================================
    # MINIMAX AI IMPLEMENTATION (UNCHANGED)
    # ============================================================================
    def evaluate_game_state(self) -> float:
        """Evaluate the current game state from AI's perspective"""
        ai_score = self.players[1]["score"]
        player_score = self.players[0]["score"]
        
        # Base score difference
        score_diff = ai_score - player_score
        
        # Strategic advantages
        ai_advantage = 0
        
        # Advantage for having more tiles
        ai_tile_count = len(self.players[1]["hand"])
        player_tile_count = len(self.players[0]["hand"])
        tile_advantage = (ai_tile_count - player_tile_count) * 0.5
        
        # Advantage for board control (more placement options)
        valid_positions = self.get_valid_positions()
        placement_advantage = len(valid_positions) * 0.1
        
        return score_diff + tile_advantage + placement_advantage + ai_advantage

    def get_all_possible_moves(self) -> List[List[Tuple[int, int, Tile]]]:
        """Get all possible moves for current player"""
        player = self.get_current_player()
        valid_positions = self.get_valid_positions()
        possible_moves = []
        
        # Consider single tile placements (most common)
        for tile in player["hand"]:
            for pos in valid_positions:
                move = [(pos[0], pos[1], tile)]
                if self.is_valid_placement(move)[0]:
                    possible_moves.append(move)
        
        # Limit to reasonable number of moves for performance
        return possible_moves[:20]  # Consider first 20 valid moves

    def minimax(self, depth: int, alpha: float, beta: float, is_maximizing: bool) -> float:
        """MiniMax algorithm with alpha-beta pruning"""
        # Terminal conditions
        if depth == 0 or self.game_state == GameState.GAME_OVER:
            return self.evaluate_game_state()
        
        if is_maximizing:
            max_eval = -float('inf')
            possible_moves = self.get_all_possible_moves()
            
            if not possible_moves:  # No moves available, must pass
                # Simulate pass
                self.consecutive_passes += 1
                self.current_player = 1 - self.current_player
                
                eval = self.minimax(depth - 1, alpha, beta, False)
                
                # Undo pass
                self.current_player = 1 - self.current_player
                self.consecutive_passes -= 1
                
                max_eval = max(max_eval, eval)
            else:
                for move in possible_moves:
                    # Save current state
                    old_board = self.board.copy()
                    old_hands = [player["hand"].copy() for player in self.players]
                    old_scores = [player["score"] for player in self.players]
                    old_player = self.current_player
                    
                    # Make move
                    self.make_move(move)
                    eval = self.minimax(depth - 1, alpha, beta, False)
                    
                    # Undo move
                    self.board = old_board
                    for i, player in enumerate(self.players):
                        player["hand"] = old_hands[i]
                        player["score"] = old_scores[i]
                    self.current_player = old_player
                    self.game_state = GameState.AI_TURN if self.players[self.current_player]["is_ai"] else GameState.PLAYER_TURN
                    
                    max_eval = max(max_eval, eval)
                    alpha = max(alpha, eval)
                    if beta <= alpha:
                        break
            
            return max_eval
        else:
            min_eval = float('inf')
            possible_moves = self.get_all_possible_moves()
            
            if not possible_moves:  # No moves available, must pass
                # Simulate pass
                self.consecutive_passes += 1
                self.current_player = 1 - self.current_player
                
                eval = self.minimax(depth - 1, alpha, beta, True)
                
                # Undo pass
                self.current_player = 1 - self.current_player
                self.consecutive_passes -= 1
                
                min_eval = min(min_eval, eval)
            else:
                for move in possible_moves:
                    # Save current state
                    old_board = self.board.copy()
                    old_hands = [player["hand"].copy() for player in self.players]
                    old_scores = [player["score"] for player in self.players]
                    old_player = self.current_player
                    
                    # Make move
                    self.make_move(move)
                    eval = self.minimax(depth - 1, alpha, beta, True)
                    
                    # Undo move
                    self.board = old_board
                    for i, player in enumerate(self.players):
                        player["hand"] = old_hands[i]
                        player["score"] = old_scores[i]
                    self.current_player = old_player
                    self.game_state = GameState.AI_TURN if self.players[self.current_player]["is_ai"] else GameState.PLAYER_TURN
                    
                    min_eval = min(min_eval, eval)
                    beta = min(beta, eval)
                    if beta <= alpha:
                        break
            
            return min_eval

    def ai_make_move(self) -> Tuple[bool, int, str]:
        """AI makes a move using MiniMax algorithm"""
        player = self.players[1]  # AI player
        
        # Get all possible moves
        possible_moves = self.get_all_possible_moves()
        
        if not possible_moves:
            self.pass_turn()
            return False, 0, "AI passed (no valid moves)"
        
        best_score = -float('inf')
        best_move = None
        
        # Use MiniMax to find best move (limited depth for performance)
        for move in possible_moves:
            # Save current state
            old_board = self.board.copy()
            old_hands = [p["hand"].copy() for p in self.players]
            old_scores = [p["score"] for p in self.players]
            old_player = self.current_player
            
            # Make move temporarily
            self.make_move(move)
            move_score = self.minimax(depth=2, alpha=-float('inf'), beta=float('inf'), is_maximizing=False)
            
            # Restore state
            self.board = old_board
            for i, p in enumerate(self.players):
                p["hand"] = old_hands[i]
                p["score"] = old_scores[i]
            self.current_player = old_player
            self.game_state = GameState.AI_TURN
            
            if move_score > best_score:
                best_score = move_score
                best_move = move
        
        if best_move:
            success, score, msg = self.make_move(best_move)
            if success:
                return True, score, f"AI placed tile(s) scoring {score} points"
        
        # Fallback: use first valid move if MiniMax fails
        for move in possible_moves:
            success, score, msg = self.make_move(move)
            if success:
                return True, score, f"AI placed tile(s) scoring {score} points"
        
        self.pass_turn()
        return False, 0, "AI passed"

# ============================================================================
# GAME VIEW - BUTTONS ON LEFT SIDE
# ============================================================================
class QGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
        arcade.set_background_color(BG_COLOR)
        
        self.game = QGameEngine()
        self.selected_tile = None
        self.placement_positions = []
        self.message = "Welcome to Q Game! Select a tile and place it on the board."
        self.message_timer = 5.0
        
        # UI state
        self.hover_pos = None
        self.hover_button = None
        self.ai_thinking = False
        self.animation_time = 0
        self.debug_display = False
        self.show_welcome = True
        
        # Dark theme background elements
        self.particles = []
        for _ in range(30):  # Fewer particles for performance
            self.particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'size': random.uniform(1, 2),
                'speed': random.uniform(0.1, 0.3),
                'brightness': random.uniform(0.3, 0.8)
            })

    def on_draw(self):
        self.clear()
        
        # Draw dark background with particles
        self.draw_dark_background()
        
        if self.show_welcome:
            self.draw_welcome_screen()
        else:
            self.draw_game_board()
            self.draw_ui()
            self.draw_message()
            
            if self.debug_display:
                self.draw_debug_info()
            
            if self.game.game_state == GameState.GAME_OVER:
                self.draw_game_over()

    def draw_dark_background(self):
        # Draw subtle particles
        for particle in self.particles:
            alpha = int(particle['brightness'] * 255)
            arcade.draw_circle_filled(
                particle['x'], particle['y'], particle['size'], 
                (100, 100, 150, alpha)
            )

    def draw_welcome_screen(self):
        # Dark overlay for readability
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 
                                   SCREEN_WIDTH, SCREEN_HEIGHT, (30, 30, 45, 230))
        
        # Compact title
        title_y = SCREEN_HEIGHT - 150
        pulse = abs(math.sin(self.animation_time * 2)) * 0.3 + 0.7
        
        # Main title with glow effect
        title_color = (
            int(ACCENT_COLOR[0] * pulse),
            int(ACCENT_COLOR[1] * pulse),
            int(ACCENT_COLOR[2] * pulse)
        )
        
        # Title
        arcade.draw_text("Q GAME", SCREEN_WIDTH // 2, title_y, title_color, 48, 
                        bold=True, anchor_x="center", font_name="Arial")
        
        # Subtitle
        arcade.draw_text("Strategic Tile Placement", SCREEN_WIDTH // 2, title_y - 50, TEXT_COLOR, 20, 
                        bold=True, anchor_x="center")
        
        # Compact game description
        desc_panel_y = SCREEN_HEIGHT // 2
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, desc_panel_y, 550, 250, (40, 40, 55, 240))
        arcade.draw_rectangle_outline(SCREEN_WIDTH // 2, desc_panel_y, 550, 250, ACCENT_COLOR, 2)
        
        # Compact rules
        rules = [
            "CREATE LINES WHERE:",
            "• Same COLOR, different SHAPES",
            "• Same SHAPE, different COLORS",
            "",
            "SCORE points for each tile in lines",
            "Longer lines = more points!",
            "",
            "Place tiles, connect to board,",
            "and challenge the AI!"
        ]
        
        for i, line in enumerate(rules):
            color = TEXT_COLOR
            size = 14
            if "CREATE" in line or "SCORE" in line:
                color = ACCENT_COLOR
                size = 15
                
            arcade.draw_text(line, SCREEN_WIDTH // 2, desc_panel_y + 90 - i * 22, color, size, 
                           anchor_x="center", anchor_y="center", font_name="Arial")
        
        # Start button
        button_y = SCREEN_HEIGHT // 2 - 180
        pulse = abs(math.sin(self.animation_time * 2)) * 0.2 + 0.8
        
        # Button with gradient effect
        if self.hover_button == "START":
            button_color = BUTTON_HOVER_COLOR
        else:
            button_color = (
                int(BUTTON_COLOR[0] * pulse),
                int(BUTTON_COLOR[1] * pulse),
                int(BUTTON_COLOR[2] * pulse)
            )
        
        # Main button
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, button_y, 180, 45, button_color)
        arcade.draw_rectangle_outline(SCREEN_WIDTH // 2, button_y, 180, 45, ACCENT_COLOR, 2)
        
        # Button text
        arcade.draw_text("START GAME", SCREEN_WIDTH // 2, button_y, (255, 255, 255), 18, 
                        bold=True, anchor_x="center", anchor_y="center", font_name="Arial")
        
        # Footer with instructions
        blink = int(self.animation_time * 2) % 2 == 0
        if blink:
            arcade.draw_text("Press SPACE or ENTER to start", SCREEN_WIDTH // 2, 50, TEXT_COLOR, 14, 
                            anchor_x="center", font_name="Arial")

    def draw_game_board(self):
        # Smaller board for compact layout
        board_size = 350
        
        # Shadow
        shadow_offset = 3
        arcade.draw_rectangle_filled(BOARD_OFFSET_X + shadow_offset, BOARD_OFFSET_Y - shadow_offset, 
                                   board_size, board_size, (20, 20, 30))
        
        # Main board
        arcade.draw_rectangle_filled(BOARD_OFFSET_X, BOARD_OFFSET_Y, board_size, board_size, PANEL_COLOR)
        
        # Border with glow
        border_pulse = abs(math.sin(self.animation_time * 1.5)) * 0.3 + 0.7
        border_color = (
            int(ACCENT_COLOR[0] * border_pulse),
            int(ACCENT_COLOR[1] * border_pulse),
            int(ACCENT_COLOR[2] * border_pulse)
        )
        arcade.draw_rectangle_outline(BOARD_OFFSET_X, BOARD_OFFSET_Y, board_size, board_size, border_color, 2)
        
        # Smaller grid
        grid_half = 4  # Reduced from 5 to fit better
        for row in range(-grid_half, grid_half + 1):
            for col in range(-grid_half, grid_half + 1):
                x = BOARD_OFFSET_X + col * TILE_SIZE
                y = BOARD_OFFSET_Y + row * TILE_SIZE
                
                # Grid cell
                cell_color = GRID_HIGHLIGHT if (row + col) % 2 == 0 else GRID_COLOR
                arcade.draw_rectangle_filled(x, y, TILE_SIZE - 2, TILE_SIZE - 2, cell_color)
                arcade.draw_rectangle_outline(x, y, TILE_SIZE - 2, TILE_SIZE - 2, (60, 60, 80), 1)
                
                # Draw existing tiles
                if (row, col) in self.game.board:
                    tile = self.game.board[(row, col)]
                    self.draw_tile(x, y, tile)
                
                # Highlight valid positions
                valid_positions = self.game.get_valid_positions()
                if (self.game.game_state == GameState.PLAYER_TURN and 
                    (row, col) in valid_positions):
                    highlight_pulse = abs(math.sin(self.animation_time * 3)) * 0.5 + 0.5
                    highlight_color = (
                        int(VALID_COLOR[0] * highlight_pulse),
                        int(VALID_COLOR[1] * highlight_pulse),
                        int(VALID_COLOR[2] * highlight_pulse)
                    )
                    arcade.draw_rectangle_filled(x, y, TILE_SIZE - 6, TILE_SIZE - 6, highlight_color)
                
                # Highlight hover position
                if self.hover_pos == (row, col) and self.selected_tile:
                    arcade.draw_rectangle_outline(x, y, TILE_SIZE - 2, TILE_SIZE - 2, ACCENT_COLOR, 2)
        
        # Draw placement preview
        for row, col, tile in self.placement_positions:
            x = BOARD_OFFSET_X + col * TILE_SIZE
            y = BOARD_OFFSET_Y + row * TILE_SIZE
            arcade.draw_rectangle_filled(x, y, TILE_SIZE - 4, TILE_SIZE - 4, HIGHLIGHT_COLOR)
            self.draw_tile(x, y, tile)

    def draw_tile(self, x, y, tile, size_ratio=0.7):
        """Tile drawing for dark theme"""
        color = tile.color.value
        size = (TILE_SIZE - 8) * size_ratio  # Adjusted for smaller tiles
        
        # Tile background
        arcade.draw_rectangle_filled(x, y, TILE_SIZE - 4, TILE_SIZE - 4, (50, 50, 60))
        arcade.draw_rectangle_outline(x, y, TILE_SIZE - 4, TILE_SIZE - 4, (80, 80, 100), 1)
        
        # Inner background
        arcade.draw_rectangle_filled(x, y, TILE_SIZE - 6, TILE_SIZE - 6, (30, 30, 40))
        
        # Draw shape
        if tile.shape == Shape.CIRCLE:
            arcade.draw_circle_filled(x, y, size / 2, color)
            arcade.draw_circle_outline(x, y, size / 2, (255, 255, 255), 1)
        elif tile.shape == Shape.SQUARE:
            arcade.draw_rectangle_filled(x, y, size, size, color)
            arcade.draw_rectangle_outline(x, y, size, size, (255, 255, 255), 1)
        elif tile.shape == Shape.STAR:
            self.draw_star(x, y, size / 2, color)
        elif tile.shape == Shape.DIAMOND:
            points = [(x, y + size/2), (x + size/2, y), (x, y - size/2), (x - size/2, y)]
            arcade.draw_polygon_filled(points, color)
            arcade.draw_polygon_outline(points, (255, 255, 255), 1)
        elif tile.shape == Shape.CLOVER:
            self.draw_clover(x, y, size / 3, color)
        elif tile.shape == Shape.CROSS:
            arcade.draw_rectangle_filled(x, y, size * 0.7, size * 0.2, color)
            arcade.draw_rectangle_filled(x, y, size * 0.2, size * 0.7, color)
        
        # Border
        arcade.draw_rectangle_outline(x, y, TILE_SIZE - 4, TILE_SIZE - 4, (200, 200, 220), 1)

    def draw_star(self, x, y, size, color):
        points = []
        for i in range(10):
            angle = math.pi / 2 + i * 2 * math.pi / 10
            r = size if i % 2 == 0 else size / 2
            points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
        arcade.draw_polygon_filled(points, color)
        arcade.draw_polygon_outline(points, (255, 255, 255), 1)

    def draw_clover(self, x, y, size, color):
        arcade.draw_circle_filled(x, y + size, size, color)
        arcade.draw_circle_filled(x - size, y, size, color)
        arcade.draw_circle_filled(x + size, y, size, color)
        arcade.draw_circle_filled(x, y - size, size, color)

    def draw_ui(self):
        # SCORE DISPLAY IN TOP RIGHT CORNER - COMPACT
        self.draw_score_panel()
        
        # DRAW BUTTONS ON LEFT SIDE
        self.draw_buttons()
        
        # Draw hand area
        if self.game.game_state == GameState.PLAYER_TURN:
            self.draw_hand()
        
        # AI thinking indicator
        if self.ai_thinking:
            dots = "." * (int(self.animation_time * 3) % 4)
            arcade.draw_text(f"AI Thinking{dots}", SCREEN_WIDTH // 2, 150, AI_COLOR, 18, 
                           anchor_x="center", bold=True, font_name="Arial")

    def draw_score_panel(self):
        """Larger score information in top right corner"""
        player = self.game.players[0]
        ai = self.game.players[1]
        
        # Position in top right corner - MAKE PANEL LARGER
        panel_x = SCREEN_WIDTH - 140
        panel_y = SCREEN_HEIGHT - 140
        
        # LARGER Background panel
        arcade.draw_rectangle_filled(panel_x, panel_y, 260, 155, (35, 35, 50, 230))
        arcade.draw_rectangle_outline(panel_x, panel_y, 260, 155, ACCENT_COLOR, 2)
        
        # Title - make larger
        arcade.draw_text("GAME INFO", panel_x, panel_y + 50, (255, 255, 255), 18,
                        bold=True, anchor_x="center", font_name="Arial")
        
        # Player Score - LARGER TEXT
        arcade.draw_text(f"Player: {player['score']}", panel_x - 110, panel_y + 15,
                        (255, 255, 255), 16, font_name="Arial")
        
        # AI Score - LARGER TEXT  
        arcade.draw_text(f"AI: {ai['score']}", panel_x - 110, panel_y - 10,
                        (255, 255, 255), 16, font_name="Arial")
        
        # Tiles in bag - LARGER TEXT
        arcade.draw_text(f"Tiles: {len(self.game.tile_bag)}", panel_x - 110, panel_y - 30,
                        (255, 255, 255), 14, font_name="Arial")
        
        # Passes - LARGER TEXT
        arcade.draw_text(f"Passes: {self.game.consecutive_passes}/2", panel_x - 110, panel_y - 50,
                        (255, 255, 255), 14, font_name="Arial")
        
        # Turn indicator - LARGER TEXT
        turn_text = "Your Turn" if self.game.game_state == GameState.PLAYER_TURN else "AI's Turn"
        turn_color = PLAYER_COLOR if self.game.game_state == GameState.PLAYER_TURN else AI_COLOR
        
        # Pulse effect for current turn
        pulse = abs(math.sin(self.animation_time * 3)) * 0.3 + 0.7
        pulse_color = (
            int(turn_color[0] * pulse),
            int(turn_color[1] * pulse), 
            int(turn_color[2] * pulse)
        )
        
        arcade.draw_text(turn_text, panel_x, panel_y - 75, pulse_color, 18,
                        bold=True, anchor_x="center", font_name="Arial")

    def draw_buttons(self):
        """Draw buttons vertically on the left side"""
        if self.game.game_state != GameState.PLAYER_TURN:
            return
            
        # Position on left side
        button_x = 100
        start_y = 400  # Start position for first button
        
        buttons = [
            ("PLACE", button_x, start_y, len(self.placement_positions) > 0),
            ("CLEAR", button_x, start_y - 60, len(self.placement_positions) > 0),
            ("PASS", button_x, start_y - 120, True)
        ]
        
        for text, x, y, enabled in buttons:
            if enabled:
                color = BUTTON_HOVER_COLOR if self.hover_button == text else BUTTON_COLOR
                text_color = (255, 255, 255)
                border_color = ACCENT_COLOR
            else:
                color = BUTTON_DISABLED_COLOR
                text_color = (150, 150, 150)
                border_color = (80, 80, 100)
            
            # Draw buttons
            arcade.draw_rectangle_filled(x, y, 100, 40, color)
            arcade.draw_rectangle_outline(x, y, 100, 40, border_color, 2)
            
            # Button text
            arcade.draw_text(text, x, y, text_color, 16, 
                           anchor_x="center", anchor_y="center", bold=True, font_name="Arial")

    def draw_hand(self):
        player = self.game.players[0]
        
        # Compact hand panel
        hand_panel_y = 80
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, hand_panel_y, SCREEN_WIDTH, 120, (30, 30, 45))
        arcade.draw_rectangle_outline(SCREEN_WIDTH // 2, hand_panel_y, SCREEN_WIDTH, 120, ACCENT_COLOR, 2)
        
        arcade.draw_text("YOUR HAND", SCREEN_WIDTH // 2, hand_panel_y + 40, (255, 255, 255), 18, 
                        bold=True, anchor_x="center", font_name="Arial")
        
        if not player["hand"]:
            arcade.draw_text("No tiles left!", SCREEN_WIDTH // 2, hand_panel_y, (255, 255, 255), 16, 
                           anchor_x="center", anchor_y="center", font_name="Arial")
            return
        
        # Draw tiles in hand
        start_x = SCREEN_WIDTH // 2 - (len(player["hand"]) * (TILE_SIZE + 8)) // 2
        for i, tile in enumerate(player["hand"]):
            x = start_x + i * (TILE_SIZE + 8)
            y = hand_panel_y
            
            # Highlight selected tile
            if tile == self.selected_tile:
                arcade.draw_rectangle_filled(x, y, TILE_SIZE + 8, TILE_SIZE + 8, HIGHLIGHT_COLOR)
                arcade.draw_rectangle_outline(x, y, TILE_SIZE + 8, TILE_SIZE + 8, ACCENT_COLOR, 2)
            
            self.draw_tile(x, y, tile, 0.75)
            
            # Number indicator
            arcade.draw_rectangle_filled(x - TILE_SIZE//2 + 5, y + TILE_SIZE//2 - 5, 16, 16, (20, 20, 35))
            arcade.draw_rectangle_outline(x - TILE_SIZE//2 + 5, y + TILE_SIZE//2 - 5, 16, 16, ACCENT_COLOR, 1)
            arcade.draw_text(str(i + 1), x - TILE_SIZE//2 + 5, y + TILE_SIZE//2 - 5, 
                           (255, 255, 255), 10, bold=True, anchor_x="center", anchor_y="center", font_name="Arial")

    def draw_message(self):
        if self.message and self.message_timer > 0:
            # Compact message box
            box_width = min(len(self.message) * 8 + 30, SCREEN_WIDTH - 50)
            arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25, 
                                       box_width, 30, (40, 40, 55))
            arcade.draw_rectangle_outline(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25, 
                                        box_width, 30, ACCENT_COLOR, 2)
            arcade.draw_text(self.message, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25, 
                           (255, 255, 255), 14, anchor_x="center", anchor_y="center", bold=True, font_name="Arial")

    def draw_debug_info(self):
        debug_text = f"Game State: {self.game.game_state.name}"
        debug_text += f" | Selected: {self.selected_tile is not None}"
        debug_text += f" | Placements: {len(self.placement_positions)}"
        
        arcade.draw_text(debug_text, 10, 30, (255, 255, 0), 10, font_name="Arial")

    def draw_game_over(self):
        # Compact game over screen
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 
                                  SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 200))
        
        # Main panel
        panel_width, panel_height = 400, 280
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, panel_width, panel_height, PANEL_COLOR)
        arcade.draw_rectangle_outline(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, panel_width, panel_height, ACCENT_COLOR, 3)
        
        # Results
        player_score = self.game.players[0]["score"]
        ai_score = self.game.players[1]["score"]
        
        if player_score > ai_score:
            winner_text = "VICTORY!"
            winner_color = PLAYER_COLOR
            sub_text = "You outsmarted the AI!"
        elif ai_score > player_score:
            winner_text = "DEFEAT"
            winner_color = AI_COLOR
            sub_text = "The AI was too clever!"
        else:
            winner_text = "DRAW"
            winner_color = ACCENT_COLOR
            sub_text = "An evenly matched game!"
        
        # Title
        arcade.draw_text("GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 90, 
                       ACCENT_COLOR, 32, bold=True, anchor_x="center", font_name="Arial")
        arcade.draw_text(winner_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
                       winner_color, 28, bold=True, anchor_x="center", font_name="Arial")
        arcade.draw_text(sub_text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20,
                       (255, 255, 255), 16, bold=True, anchor_x="center", font_name="Arial")
        
        # Scores
        y = SCREEN_HEIGHT // 2 - 20
        arcade.draw_text(f"Player: {player_score}", SCREEN_WIDTH // 2 - 80, y, 
                        (255, 255, 255), 20, anchor_x="center", anchor_y="center", bold=True, font_name="Arial")
        arcade.draw_text(f"AI: {ai_score}", SCREEN_WIDTH // 2 + 80, y, 
                        (255, 255, 255), 20, anchor_x="center", anchor_y="center", bold=True, font_name="Arial")
        
        # Restart instruction
        blink = int(self.animation_time * 2) % 2 == 0
        if blink:
            arcade.draw_text("Click anywhere to play again", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
                           (255, 255, 255), 14, anchor_x="center", font_name="Arial")

    def show_message(self, text):
        self.message = text
        self.message_timer = 3.0

    def on_mouse_motion(self, x, y, dx, dy):
        if self.show_welcome:
            # Check if hovering over start button
            button_y = SCREEN_HEIGHT // 2 - 180
            if (SCREEN_WIDTH // 2 - 90 <= x <= SCREEN_WIDTH // 2 + 90 and 
                button_y - 22 <= y <= button_y + 22):
                self.hover_button = "START"
            else:
                self.hover_button = None
            return
        
        # In-game hover detection
        if self.game.game_state == GameState.PLAYER_TURN:
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
        
        # Button hover detection - UPDATED FOR LEFT SIDE
        self.hover_button = None
        if self.game.game_state == GameState.PLAYER_TURN:
            button_x = 100
            start_y = 400
            
            buttons = [
                ("PLACE", button_x, start_y),
                ("CLEAR", button_x, start_y - 60),
                ("PASS", button_x, start_y - 120)
            ]
            
            for text, btn_x, btn_y in buttons:
                if (btn_x - 50 <= x <= btn_x + 50 and 
                    btn_y - 20 <= y <= btn_y + 20):
                    self.hover_button = text
                    return

    def on_mouse_press(self, x, y, button, modifiers):
        if self.show_welcome:
            # Check if start button clicked
            button_y = SCREEN_HEIGHT // 2 - 180
            if (SCREEN_WIDTH // 2 - 90 <= x <= SCREEN_WIDTH // 2 + 90 and 
                button_y - 22 <= y <= button_y + 22):
                self.show_welcome = False
                self.message = "Game started! Select a tile from your hand."
                self.message_timer = 3.0
            return
        
        if self.game.game_state == GameState.GAME_OVER:
            self.__init__()  # Restart game
            self.show_welcome = False
            return
        
        if self.game.game_state == GameState.AI_TURN and not self.ai_thinking:
            self.ai_thinking = True
            return
        
        # Player's turn interactions
        if self.check_hand_click(x, y):
            return
        
        if self.check_button_click(x, y):
            return
        
        if self.selected_tile and self.hover_pos:
            row, col = self.hover_pos
            valid_positions = self.game.get_valid_positions()
            
            if (row, col) in valid_positions:
                self.placement_positions.append((row, col, self.selected_tile))
                self.selected_tile = None
                self.show_message(f"Tile placed at ({row}, {col})")

    def check_hand_click(self, x, y) -> bool:
        if not (30 <= y <= 170):  # Hand area
            return False
        
        player = self.game.players[0]
        start_x = SCREEN_WIDTH // 2 - (len(player["hand"]) * (TILE_SIZE + 8)) // 2
        
        for i, tile in enumerate(player["hand"]):
            tile_x = start_x + i * (TILE_SIZE + 8)
            tile_y = 80  # Hand panel center
            
            if abs(x - tile_x) < TILE_SIZE // 2 and abs(y - tile_y) < TILE_SIZE // 2:
                if tile == self.selected_tile:
                    self.selected_tile = None
                    self.show_message("Tile deselected")
                else:
                    self.selected_tile = tile
                    self.show_message(f"Selected tile {i + 1}")
                return True
        return False

    def check_button_click(self, x, y) -> bool:
        """Check if left side buttons are clicked"""
        if self.game.game_state != GameState.PLAYER_TURN:
            return False
            
        button_x = 100
        start_y = 400
        
        buttons = [
            (SCREEN_WIDTH // 2 - 120, button_x, start_y, self.place_tiles, len(self.placement_positions) > 0),
            (SCREEN_WIDTH // 2, button_x, start_y - 60, self.clear_selection, len(self.placement_positions) > 0),
            (SCREEN_WIDTH // 2 + 120, button_x, start_y - 120, self.pass_turn, True)
        ]
        
        for _, btn_x, btn_y, callback, enabled in buttons:
            if enabled and (btn_x - 50 <= x <= btn_x + 50 and btn_y - 20 <= y <= btn_y + 20):
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
            self.selected_tile = self.placement_positions[0][2]
            self.placement_positions.clear()
            self.show_message("Placement cleared")

    def pass_turn(self):
        self.game.pass_turn()
        self.selected_tile = None
        self.placement_positions.clear()
        self.show_message("Turn passed to AI")

    def on_key_press(self, key, modifiers):
        if self.show_welcome:
            if key == arcade.key.SPACE or key == arcade.key.ENTER:
                self.show_welcome = False
                self.message = "Game started! Select a tile from your hand."
                self.message_timer = 3.0
            return
        
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
        
        # Toggle debug display
        if key == arcade.key.F3:
            self.debug_display = not self.debug_display

    def on_update(self, delta_time):
        self.animation_time += delta_time
        
        # Animate background particles
        for particle in self.particles:
            particle['x'] += particle['speed']
            if particle['x'] > SCREEN_WIDTH + 10:
                particle['x'] = -10
                particle['y'] = random.randint(0, SCREEN_HEIGHT)
        
        if self.message_timer > 0:
            self.message_timer -= delta_time
        
        if self.game.game_state == GameState.AI_TURN and self.ai_thinking:
            time.sleep(0.5)  # Small delay for visual effect
            success, score, msg = self.game.ai_make_move()
            if success:
                self.show_message(f"AI placed tiles! Score: +{score}")
            else:
                self.show_message("AI passed turn")
            self.ai_thinking = False

def main():
    game = QGame()
    arcade.run()

if __name__ == "__main__":
    main()