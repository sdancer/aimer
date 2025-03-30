import pygame
import random
import time
import math # Needed for clamping cursor position

# Initialize Pygame
pygame.init()

# --- Screen Setup ---
try:
    display_info = pygame.display.Info()
    WIDTH, HEIGHT = display_info.current_w, display_info.current_h
except pygame.error:
    print("Could not get display info, using default 800x600.")
    WIDTH, HEIGHT = 800, 600

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Aim Trainer - Timed Targets")

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
GREEN = (0, 255, 0) # For FPS display

# --- Circle Properties ---
CIRCLE_RADIUS = 20       # Fixed radius
CIRCLE_LIFETIME_MS = 300 # Time before circle respawns (in milliseconds)

# --- Game Variables ---
circle_x = 0
circle_y = 0
circle_active = False    # Starts inactive to trigger initial spawn
start_time = 0           # Time when the current circle spawned
font_large = pygame.font.Font(None, 30) # For main info
font_small = pygame.font.Font(None, 22) # For instructions & FPS

# --- Sensitivity Simulation Settings ---
target_dpi = 1600
target_valorant_sens = 0.4
VALORANT_SENS_INCREMENT_FINE = 0.005
VALORANT_SENS_INCREMENT_COARSE = 0.05
DPI_INCREMENT = 50
REFERENCE_eDPI = 640.0 # 1600 DPI * 0.4 Sens

def calculate_sensitivity_multiplier(dpi, sens):
    current_eDPI = dpi * sens
    return current_eDPI / REFERENCE_eDPI

sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)

# --- Custom Cursor ---
cursor_x, cursor_y = WIDTH // 2, HEIGHT // 2
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)


def spawn_circle():
    """Spawns a new circle at a random location and resets its timer."""
    global circle_x, circle_y, circle_active, start_time
    # Ensure circle spawns fully within bounds
    circle_x = random.randint(CIRCLE_RADIUS, WIDTH - CIRCLE_RADIUS)
    circle_y = random.randint(CIRCLE_RADIUS, HEIGHT - CIRCLE_RADIUS)
    circle_active = True
    start_time = time.time() # Record the exact spawn time


def draw_sensitivity_info():
    """Draws the target DPI and Valorant sensitivity."""
    dpi_text = f"Target DPI: {target_dpi}"
    sens_text = f"Target Val Sens: {target_valorant_sens:.3f}"
    dpi_surf = font_large.render(dpi_text, True, YELLOW)
    sens_surf = font_large.render(sens_text, True, YELLOW)
    dpi_rect = dpi_surf.get_rect(topright=(WIDTH - 20, 10))
    sens_rect = sens_surf.get_rect(topright=(WIDTH - 20, 10 + dpi_rect.height + 5))
    screen.blit(dpi_surf, dpi_rect)
    screen.blit(sens_surf, sens_rect)

def draw_instructions_and_fps(current_fps):
    """Draws control instructions and FPS in the top left."""
    instructions = [
        f"FPS: {current_fps:.0f}", # Display FPS first
        "-----------",
        "Controls:",
        "UP/DOWN: Adjust Val Sens (Fine)",
        "SHIFT+UP/DOWN: Adjust Val Sens (Coarse)",
        "LEFT/RIGHT: Adjust DPI",
        "ESC: Quit"
    ]
    y_offset = 10
    for i, line in enumerate(instructions):
        color = GREEN if i == 0 else CYAN # Use Green for FPS, Cyan for rest
        text_surface = font_small.render(line, True, color)
        text_rect = text_surface.get_rect(topleft=(10, y_offset))
        screen.blit(text_surface, text_rect)
        y_offset += text_rect.height + 3


def draw_circle_timer(elapsed_ms):
    """Displays the time the current circle has been alive."""
    if circle_active:
        timer_text = f"{elapsed_ms:.0f} ms"
        text_surface = font_small.render(timer_text, True, WHITE)
        # Position it slightly above the current circle
        text_rect = text_surface.get_rect(center=(circle_x, circle_y - CIRCLE_RADIUS - 15))
        screen.blit(text_surface, text_rect)


def draw_cursor():
    pygame.draw.circle(screen, BLUE, (int(cursor_x), int(cursor_y)), 5)
    pygame.draw.line(screen, WHITE, (int(cursor_x) - 8, int(cursor_y)), (int(cursor_x) + 8, int(cursor_y)), 1)
    pygame.draw.line(screen, WHITE, (int(cursor_x), int(cursor_y) - 8), (int(cursor_x), int(cursor_y) + 8), 1)


# --- Game Loop ---
running = True
clock = pygame.time.Clock()

while running:
    # Get current time at the start of the frame for consistent calculations
    current_frame_time = time.time()

    # --- Event Handling ---
    keys_pressed = pygame.key.get_pressed()
    shift_pressed = keys_pressed[pygame.K_LSHIFT] or keys_pressed[pygame.K_RSHIFT]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            # Sensitivity Adjustments
            current_sens_increment = VALORANT_SENS_INCREMENT_COARSE if shift_pressed else VALORANT_SENS_INCREMENT_FINE
            sens_changed = False
            if event.key == pygame.K_UP:
                target_valorant_sens += current_sens_increment
                target_valorant_sens = round(target_valorant_sens, 5)
                sens_changed = True
            elif event.key == pygame.K_DOWN:
                target_valorant_sens -= current_sens_increment
                target_valorant_sens = max(0.001, round(target_valorant_sens, 5))
                sens_changed = True
            elif event.key == pygame.K_RIGHT:
                target_dpi += DPI_INCREMENT
                sens_changed = True
            elif event.key == pygame.K_LEFT:
                target_dpi = max(50, target_dpi - DPI_INCREMENT)
                sens_changed = True

            if sens_changed:
                 sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)

        # Mouse button click doesn't destroy the circle anymore, but we can
        # still register it if needed for future features (like hit sounds/effects)
        # if event.type == pygame.MOUSEBUTTONDOWN:
        #     if event.button == 1:
        #         if circle_active:
        #             distance = ((cursor_x - circle_x)**2 + (cursor_y - circle_y)**2)**0.5
        #             if distance <= CIRCLE_RADIUS:
        #                 # Optional: Add hit feedback here (e.g., sound, brief color change)
        #                 pass # Circle is NOT destroyed by click

        if event.type == pygame.MOUSEMOTION:
            dx, dy = event.rel
            cursor_x += dx * sensitivity_multiplier
            cursor_y += dy * sensitivity_multiplier
            cursor_x = max(0, min(WIDTH - 1, cursor_x))
            cursor_y = max(0, min(HEIGHT - 1, cursor_y))


    # --- Game Logic ---
    elapsed_milliseconds = 0
    if not circle_active:
        spawn_circle() # Initial spawn
        elapsed_milliseconds = 0 # Reset timer display for the new circle
    else:
        # Calculate how long the current circle has been alive
        elapsed_seconds = current_frame_time - start_time
        elapsed_milliseconds = elapsed_seconds * 1000

        # Check if the circle's lifetime is up
        if elapsed_milliseconds >= CIRCLE_LIFETIME_MS:
            spawn_circle() # Respawn in a new location
            # No need to reset elapsed_milliseconds here, spawn_circle resets start_time


    # --- Drawing ---
    screen.fill(BLACK)

    # UI Elements
    current_fps = clock.get_fps()
    draw_instructions_and_fps(current_fps)
    draw_sensitivity_info()
    draw_circle_timer(elapsed_milliseconds if circle_active else 0) # Show timer for active circle

    # Game Elements
    if circle_active:
        pygame.draw.circle(screen, RED, (circle_x, circle_y), CIRCLE_RADIUS)

    draw_cursor() # Draw cursor last

    # --- Update Display ---
    pygame.display.flip()

    # --- Control Frame Rate ---
    clock.tick(144) # Aim for a higher tick rate for potentially smoother input/timing

# --- Cleanup ---
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()