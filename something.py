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
pygame.display.set_caption("Aim Trainer - Valorant Sensitivity Sim")

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)

# --- Circle Properties ---
CIRCLE_MIN_RADIUS = 15
CIRCLE_MAX_RADIUS = 50
CIRCLE_GROWTH_RATE = 1.2
CIRCLE_SHRINK_RATE = 1.2

# --- Game Variables ---
circle_x = 0
circle_y = 0
circle_radius = 0
circle_growing = True
circle_active = False
start_time = 0
last_hit_info = None
font_large = pygame.font.Font(None, 30) # For main info
font_small = pygame.font.Font(None, 22) # For instructions

# --- Sensitivity Simulation Settings ---
# User-configurable target settings
target_dpi = 1600
target_valorant_sens = 0.4

# Sensitivity adjustment controls
# Let's allow fine-tuning the Valorant sens value directly
VALORANT_SENS_INCREMENT_FINE = 0.005
VALORANT_SENS_INCREMENT_COARSE = 0.05
DPI_INCREMENT = 50

# Reference eDPI for scaling (Valorant default is often used as a baseline)
# We'll scale cursor movement relative to this. Adjust if needed.
# Using 1600 * 0.4 = 640 as the reference where our internal scale might be ~1.0
REFERENCE_eDPI = 640.0 # 1600 DPI * 0.4 Sens

# Calculate the actual multiplier based on target settings
# This multiplier scales the raw mouse input (event.rel)
def calculate_sensitivity_multiplier(dpi, sens):
    current_eDPI = dpi * sens
    # Scale linearly relative to the reference eDPI
    # If current eDPI is higher, multiplier > 1, if lower, multiplier < 1
    return current_eDPI / REFERENCE_eDPI

sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)

# --- Custom Cursor ---
cursor_x, cursor_y = WIDTH // 2, HEIGHT // 2
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)


def spawn_circle():
    global circle_x, circle_y, circle_radius, circle_growing, circle_active, start_time
    circle_x = random.randint(CIRCLE_MAX_RADIUS, WIDTH - CIRCLE_MAX_RADIUS)
    circle_y = random.randint(CIRCLE_MAX_RADIUS, HEIGHT - CIRCLE_MAX_RADIUS)
    circle_radius = CIRCLE_MIN_RADIUS
    circle_growing = True
    circle_active = True
    start_time = time.time()


def draw_last_hit_time():
    if last_hit_info:
        x, y, time_taken = last_hit_info
        text_surface = font_large.render(f"{time_taken:.2f}s", True, WHITE)
        text_rect = text_surface.get_rect(center=(x, y - CIRCLE_MAX_RADIUS - 15))
        screen.blit(text_surface, text_rect)

def draw_sensitivity_info():
    """Draws the target DPI and Valorant sensitivity."""
    dpi_text = f"Target DPI: {target_dpi}"
    sens_text = f"Target Val Sens: {target_valorant_sens:.3f}" # Show more precision

    dpi_surf = font_large.render(dpi_text, True, YELLOW)
    sens_surf = font_large.render(sens_text, True, YELLOW)

    # Position in top right
    dpi_rect = dpi_surf.get_rect(topright=(WIDTH - 20, 10))
    sens_rect = sens_surf.get_rect(topright=(WIDTH - 20, 10 + dpi_rect.height + 5))

    screen.blit(dpi_surf, dpi_rect)
    screen.blit(sens_surf, sens_rect)

def draw_instructions():
    """Draws control instructions."""
    instructions = [
        "Controls:",
        "UP/DOWN: Adjust Val Sens (Fine)",
        "SHIFT+UP/DOWN: Adjust Val Sens (Coarse)",
        "LEFT/RIGHT: Adjust DPI",
        "ESC: Quit"
    ]
    y_offset = 10
    for line in instructions:
        text_surface = font_small.render(line, True, CYAN)
        text_rect = text_surface.get_rect(topleft=(10, y_offset))
        screen.blit(text_surface, text_rect)
        y_offset += text_rect.height + 3


def draw_cursor():
    pygame.draw.circle(screen, BLUE, (int(cursor_x), int(cursor_y)), 5)
    pygame.draw.line(screen, WHITE, (int(cursor_x) - 8, int(cursor_y)), (int(cursor_x) + 8, int(cursor_y)), 1)
    pygame.draw.line(screen, WHITE, (int(cursor_x), int(cursor_y) - 8), (int(cursor_x), int(cursor_y) + 8), 1)


# --- Game Loop ---
running = True
clock = pygame.time.Clock()

while running:
    # --- Event Handling ---
    keys_pressed = pygame.key.get_pressed() # Get state of all keys
    shift_pressed = keys_pressed[pygame.K_LSHIFT] or keys_pressed[pygame.K_RSHIFT]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            # --- Sensitivity Adjustments ---
            current_sens_increment = VALORANT_SENS_INCREMENT_COARSE if shift_pressed else VALORANT_SENS_INCREMENT_FINE

            if event.key == pygame.K_UP:
                target_valorant_sens += current_sens_increment
                target_valorant_sens = round(target_valorant_sens, 5) # Prevent floating point issues
            elif event.key == pygame.K_DOWN:
                target_valorant_sens -= current_sens_increment
                target_valorant_sens = max(0.001, round(target_valorant_sens, 5)) # Prevent going <= 0

            elif event.key == pygame.K_RIGHT:
                target_dpi += DPI_INCREMENT
            elif event.key == pygame.K_LEFT:
                target_dpi = max(50, target_dpi - DPI_INCREMENT) # Prevent going too low

            # Recalculate multiplier whenever target settings change
            if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                 sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)


        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if circle_active:
                    distance = ((cursor_x - circle_x) ** 2 + (cursor_y - circle_y) ** 2) ** 0.5
                    if distance <= circle_radius:
                        end_time = time.time()
                        time_taken = end_time - start_time
                        last_hit_info = (circle_x, circle_y, time_taken)
                        circle_active = False

        if event.type == pygame.MOUSEMOTION:
            dx, dy = event.rel
            # Apply the calculated sensitivity multiplier to raw mouse input
            cursor_x += dx * sensitivity_multiplier
            cursor_y += dy * sensitivity_multiplier

            # Clamp cursor
            cursor_x = max(0, min(WIDTH - 1, cursor_x))
            cursor_y = max(0, min(HEIGHT - 1, cursor_y))


    # --- Game Logic ---
    if not circle_active:
        spawn_circle()

    if circle_active:
        if circle_growing:
            circle_radius += CIRCLE_GROWTH_RATE
            if circle_radius >= CIRCLE_MAX_RADIUS:
                circle_growing = False
        else:
            circle_radius -= CIRCLE_SHRINK_RATE
            if circle_radius <= CIRCLE_MIN_RADIUS:
                circle_growing = True

    # --- Drawing ---
    screen.fill(BLACK)
    draw_last_hit_time()
    draw_sensitivity_info()
    draw_instructions() # Draw instructions on the left

    if circle_active:
        pygame.draw.circle(screen, RED, (circle_x, circle_y), int(circle_radius))

    draw_cursor()
    pygame.display.flip()
    clock.tick(120) # Aim for higher tick rate for smoother input reading

# --- Cleanup ---
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()