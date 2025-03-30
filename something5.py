import pygame
import random
import math
import sys
import time # For brief pauses or effects if needed

# --- Constants ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
TARGET_BASE_RADIUS = 25
TARGET_SPAWN_RATE = 60 # Lower number = faster spawns (frames per spawn)
TARGET_LIFETIME = 120 # How many frames a target lasts if not hit
CROSSHAIR_SIZE = 15
CROSSHAIR_THICKNESS = 2
MAX_TARGETS_ON_SCREEN = 5 # Limit concurrent targets

# Colors (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (50, 50, 200) # Background color (Valorant-ish)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
CROSSHAIR_COLOR = WHITE

# --- Game Variables ---
score = 0
hits = 0
misses = 0
targets = [] # List to store active targets
spawn_timer = 0
game_running = True

# --- Target Class (Optional but good practice) ---
class Target:
    def __init__(self):
        # Ensure targets don't spawn too close to edges
        edge_margin = TARGET_BASE_RADIUS * 2
        self.x = random.randint(edge_margin, SCREEN_WIDTH - edge_margin)
        self.y = random.randint(edge_margin, SCREEN_HEIGHT - edge_margin)
        # Simulate distance slightly with size variation
        self.radius = int(TARGET_BASE_RADIUS * random.uniform(0.8, 1.5))
        self.creation_time = pygame.time.get_ticks() # For lifetime tracking (in milliseconds)
        self.lifetime_ms = TARGET_LIFETIME * (1000 / 60) # Approx lifetime in ms (assuming 60 FPS)
        self.color = RED

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius)
        # Optional: Add a border for better visibility
        pygame.draw.circle(surface, BLACK, (self.x, self.y), self.radius, 2)

    def is_hit(self, pos):
        distance = math.sqrt((self.x - pos[0])**2 + (self.y - pos[1])**2)
        return distance <= self.radius

    def is_expired(self):
        return pygame.time.get_ticks() - self.creation_time > self.lifetime_ms

# --- Pygame Initialization ---
pygame.init()
pygame.font.init() # Initialize font module
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Simple Aim Trainer")
clock = pygame.time.Clock()
pygame.mouse.set_visible(False) # Hide default mouse cursor

# Font for UI
ui_font = pygame.font.SysFont('Consolas', 30) # Use a common monospace font

# --- Helper Functions ---
def draw_crosshair(surface, pos):
    x, y = pos
    # Horizontal line
    pygame.draw.line(surface, CROSSHAIR_COLOR, (x - CROSSHAIR_SIZE, y), (x + CROSSHAIR_SIZE, y), CROSSHAIR_THICKNESS)
    # Vertical line
    pygame.draw.line(surface, CROSSHAIR_COLOR, (x, y - CROSSHAIR_SIZE), (x, y + CROSSHAIR_SIZE), CROSSHAIR_THICKNESS)
    # Optional center dot
    # pygame.draw.circle(surface, CROSSHAIR_COLOR, pos, CROSSHAIR_THICKNESS)

def draw_ui(surface):
    accuracy = 0
    if (hits + misses) > 0:
        accuracy = (hits / (hits + misses)) * 100

    score_text = ui_font.render(f"Score: {score}", True, WHITE)
    hits_text = ui_font.render(f"Hits: {hits}", True, GREEN)
    misses_text = ui_font.render(f"Misses: {misses}", True, RED)
    accuracy_text = ui_font.render(f"Accuracy: {accuracy:.1f}%", True, YELLOW)

    surface.blit(score_text, (10, 10))
    surface.blit(hits_text, (10, 40))
    surface.blit(misses_text, (10, 70))
    surface.blit(accuracy_text, (10, 100))

def spawn_target():
    global spawn_timer
    spawn_timer += 1
    if spawn_timer >= TARGET_SPAWN_RATE and len(targets) < MAX_TARGETS_ON_SCREEN:
        targets.append(Target())
        spawn_timer = 0 # Reset timer

# --- Game Loop ---
while game_running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left mouse button
                mouse_pos = pygame.mouse.get_pos()
                target_hit = False
                # Iterate backwards to safely remove items while iterating
                for i in range(len(targets) - 1, -1, -1):
                    target = targets[i]
                    if target.is_hit(mouse_pos):
                        score += 10 # Give points for hit
                        hits += 1
                        targets.pop(i) # Remove hit target
                        target_hit = True
                        # Optional: Add a hit sound effect here
                        break # Assume only one target hit per click
                if not target_hit:
                    misses += 1
                    score -= 2 # Penalty for missing
                    # Optional: Add a miss sound effect here

    # --- Game Logic ---
    # Spawn new targets
    spawn_target()

    # Update targets (check for expiration)
    current_time = pygame.time.get_ticks()
    targets_to_remove = []
    for i in range(len(targets) - 1, -1, -1):
         target = targets[i]
         if target.is_expired():
             targets.pop(i)
             misses += 1 # Count expired target as a miss
             # No score penalty for expired ones, usually

    # --- Drawing ---
    # Background
    screen.fill(BLUE)

    # Draw targets
    for target in targets:
        target.draw(screen)

    # Draw UI
    draw_ui(screen)

    # Draw Crosshair (draw last so it's on top)
    mouse_pos = pygame.mouse.get_pos()
    draw_crosshair(screen, mouse_pos)

    # --- Update Display ---
    pygame.display.flip() # Show the new frame

    # --- Frame Rate Control ---
    clock.tick(60) # Limit FPS to 60

# --- Cleanup ---
pygame.quit()
sys.exit()
