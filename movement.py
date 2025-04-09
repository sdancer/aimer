import pygame
import sys
import random
import math
import time
from collections import deque

# Initialize pygame
pygame.init()

# Get display info and create fullscreen surface
display_info = pygame.display.Info()
WIDTH, HEIGHT = display_info.current_w, display_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Aim Reaction Trainer")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 100, 255)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)

# Configuration
CENTER = (WIDTH // 2, HEIGHT // 2)
TARGET_RADIUS = 30
SPAWN_DISTANCE = min(WIDTH, HEIGHT) * 0.4  # 40% of the smaller screen dimension
CROSSHAIR_SIZE = 15
VECTOR_LENGTH = 50
TRAIL_LENGTH = 100
TRAIL_FADE_START = 50  # When trail starts fading (older points)
MOVEMENT_WINDOW = 25  # ms to aggregate movement for direction vector
MIN_DIRECTION_CHANGE = math.radians(20)  # Minimum change to be considered a new movement
IDLE_PERIOD = 1.0  # seconds between targets

# Game state
class GameState:
    def __init__(self):
        self.target_active = False
        self.target_pos = None
        self.target_appear_time = 0
        self.idle_timer = 0
        self.mouse_movements = deque(maxlen=10)  # Store recent mouse movements
        self.current_vector = (0, 0)
        self.vector_magnitude = 0
        self.previous_angle = None
        self.current_angle = None
        self.movement_detected = False
        self.trail = deque(maxlen=TRAIL_LENGTH)
        self.reaction_times = []
        self.target_count = 0
        self.last_reaction_time = None
        self.absolute_mouse_pos = CENTER  # Track absolute mouse position
        
        # Initialize with a target
        self.spawn_new_target()
        
    def spawn_new_target(self):
        # Generate a random angle
        angle = random.uniform(0, 2 * math.pi)
        
        # Calculate position based on angle and spawn distance
        x = CENTER[0] + SPAWN_DISTANCE * math.cos(angle)
        y = CENTER[1] + SPAWN_DISTANCE * math.sin(angle)
        
        self.target_pos = (x, y)
        self.target_active = True
        self.target_appear_time = time.time()
        self.movement_detected = False
        self.previous_angle = self.current_angle
        self.trail.clear()  # Clear trail with each new target
        self.mouse_movements.clear()  # Reset movement queue
        self.absolute_mouse_pos = CENTER  # Reset absolute position
        
    def update_vector(self, dx, dy):
        # Add new movement to the queue
        self.mouse_movements.append((dx, dy))
        
        # Update absolute mouse position (hypothetical, since we reset it to center)
        new_x = self.absolute_mouse_pos[0] + dx
        new_y = self.absolute_mouse_pos[1] + dy
        self.absolute_mouse_pos = (new_x, new_y)
        
        # Aggregate recent movements for vector direction
        total_dx = sum(move[0] for move in self.mouse_movements)
        total_dy = sum(move[1] for move in self.mouse_movements)
        
        # Calculate magnitude
        self.vector_magnitude = math.sqrt(total_dx**2 + total_dy**2)
        
        # Normalize and scale the vector
        if self.vector_magnitude > 0:
            norm_dx = total_dx / self.vector_magnitude
            norm_dy = total_dy / self.vector_magnitude
            self.current_vector = (norm_dx * VECTOR_LENGTH, norm_dy * VECTOR_LENGTH)
            
            # Calculate current angle
            self.current_angle = math.atan2(norm_dy, norm_dx)
        else:
            self.current_vector = (0, 0)
            
        # Add current position to trail if there's movement
        # We only add actual mouse movement, not the reset back to center
        if dx != 0 or dy != 0:
            self.trail.append(self.absolute_mouse_pos)
    
    def check_movement_direction(self):
        # If no vector, can't check
        if self.current_vector == (0, 0):
            return False
            
        # Calculate target direction
        target_dx = self.target_pos[0] - CENTER[0]
        target_dy = self.target_pos[1] - CENTER[1]
        target_angle = math.atan2(target_dy, target_dx)
        
        # Calculate angle difference to target
        angle_diff = abs(angle_difference(self.current_angle, target_angle))
        
        # Check if we're within 30 degrees of the target with minimal movement
        return angle_diff < math.radians(30) and self.vector_magnitude > 0.1
                
    def update(self):
        # If we're in idle period and it's time for a new target
        if not self.target_active and time.time() - self.idle_timer >= IDLE_PERIOD:
            self.spawn_new_target()
            
    def get_avg_reaction_time(self):
        if not self.reaction_times:
            return None
        return sum(self.reaction_times) / len(self.reaction_times)

# Helper functions
def angle_difference(angle1, angle2):
    """Calculate the smallest angle difference between two angles."""
    diff = (angle1 - angle2) % (2 * math.pi)
    if diff > math.pi:
        diff = diff - 2 * math.pi
    return diff

def draw_crosshair(surface, pos, size, color):
    """Draw a simple crosshair at the specified position."""
    x, y = pos
    pygame.draw.line(surface, color, (x - size, y), (x + size, y), 2)
    pygame.draw.line(surface, color, (x, y - size), (x, y + size), 2)
    pygame.draw.circle(surface, color, pos, size // 3, 1)

def draw_direction_vector(surface, pos, vector, color):
    """Draw an arrow representing the movement direction."""
    if vector[0] == 0 and vector[1] == 0:
        return
        
    end_x = pos[0] + vector[0]
    end_y = pos[1] + vector[1]
    
    # Draw the line
    pygame.draw.line(surface, color, pos, (end_x, end_y), 3)
    
    # Draw arrowhead
    arrow_size = 10
    angle = math.atan2(vector[1], vector[0])
    
    arrow1_x = end_x - arrow_size * math.cos(angle - math.pi/6)
    arrow1_y = end_y - arrow_size * math.sin(angle - math.pi/6)
    
    arrow2_x = end_x - arrow_size * math.cos(angle + math.pi/6)
    arrow2_y = end_y - arrow_size * math.sin(angle + math.pi/6)
    
    pygame.draw.line(surface, color, (end_x, end_y), (arrow1_x, arrow1_y), 3)
    pygame.draw.line(surface, color, (end_x, end_y), (arrow2_x, arrow2_y), 3)

def draw_trail(surface, trail):
    """Draw the movement trail with fading effect."""
    if len(trail) < 2:
        return
    
    # Create a temporary trail that starts from CENTER
    display_trail = [CENTER]  # Always start from center
    
    # Add all other points from the actual trail
    for point in trail:
        display_trail.append(point)
        
    # Draw the trail segments
    for i in range(1, len(display_trail)):
        # Calculate opacity based on position in trail
        # Newer points are more opaque
        position_ratio = i / len(display_trail)
        alpha = 255 * (1 - position_ratio)
            
        # White color with fading
        color = (255, 255, 255)
        pygame.draw.line(surface, color, display_trail[i-1], display_trail[i], 2)

def draw_stats(surface, game_state):
    """Draw statistics on screen."""
    font = pygame.font.SysFont(None, 24)
    
    # Background for stats
    stats_rect = pygame.Rect(10, 10, 300, 100)
    pygame.draw.rect(surface, BLACK, stats_rect)
    pygame.draw.rect(surface, WHITE, stats_rect, 1)
    
    # Render text
    text_y = 20
    
    # Target count
    count_text = f"Targets: {game_state.target_count}"
    text_surface = font.render(count_text, True, WHITE)
    surface.blit(text_surface, (20, text_y))
    text_y += 25
    
    # Last reaction time
    if game_state.last_reaction_time is not None:
        reaction_text = f"Last reaction: {game_state.last_reaction_time*1000:.0f} ms"
        text_surface = font.render(reaction_text, True, WHITE)
        surface.blit(text_surface, (20, text_y))
        text_y += 25
    
    # Average reaction time
    avg_time = game_state.get_avg_reaction_time()
    if avg_time is not None:
        avg_text = f"Average reaction: {avg_time*1000:.0f} ms"
        text_surface = font.render(avg_text, True, WHITE)
        surface.blit(text_surface, (20, text_y))
        
    # Draw reaction time in center if just completed a target
    if game_state.last_reaction_time is not None and time.time() - game_state.idle_timer < 1.0:
        center_font = pygame.font.SysFont(None, 48)
        reaction_ms = game_state.last_reaction_time * 1000
        center_text = f"{reaction_ms:.0f} ms"
        
        # Color code based on reaction time
        if reaction_ms < 100:
            text_color = GREEN  # Great reaction time
        elif reaction_ms < 250:
            text_color = (255, 255, 0)  # Yellow - good reaction time
        else:
            text_color = (255, 105, 180)  # Pink - slow reaction time
            
        text_surface = center_font.render(center_text, True, text_color)
        text_rect = text_surface.get_rect(center=(WIDTH//2, HEIGHT//2 + 50))
        surface.blit(text_surface, text_rect)

def main():
    clock = pygame.time.Clock()
    game_state = GameState()
    
    # Hide the mouse cursor
    pygame.mouse.set_visible(False)
    
    # Position the mouse at the center
    pygame.mouse.set_pos(CENTER)
    pygame.mouse.get_rel()  # Clear any initial movement
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    
        # Get relative mouse movement
        dx, dy = pygame.mouse.get_rel()
        
        # Only process real movement, not the reset to center
        if dx != 0 or dy != 0:
            game_state.update_vector(dx, dy)
            
            # Check for target acquisition immediately after movement
            if game_state.target_active and game_state.check_movement_direction():
                game_state.movement_detected = True
                reaction_time = time.time() - game_state.target_appear_time
                game_state.reaction_times.append(reaction_time)
                game_state.last_reaction_time = reaction_time
                game_state.target_count += 1
                game_state.target_active = False
                game_state.idle_timer = time.time()
        
        # Reset mouse position to center
        pygame.mouse.set_pos(CENTER)
        
        # Update game state
        game_state.update()
        
        # Drawing
        screen.fill(BLACK)
        
        # Draw trail
        draw_trail(screen, game_state.trail)
        
        # Draw target if active
        if game_state.target_active:
            pygame.draw.circle(screen, RED, (int(game_state.target_pos[0]), int(game_state.target_pos[1])), TARGET_RADIUS)
        
        # Draw direction vector
        draw_direction_vector(screen, CENTER, game_state.current_vector, BLUE)
        
        # Draw crosshair at center
        draw_crosshair(screen, CENTER, CROSSHAIR_SIZE, WHITE)
        
        # Draw stats
        draw_stats(screen, game_state)
        
        # Update display
        pygame.display.flip()
        clock.tick(100)  # 100 FPS max
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
