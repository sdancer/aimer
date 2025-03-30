import pygame
import random
import time
import math
import os # Import os module for path handling

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
pygame.display.set_caption("Aim Trainer - Reaction Time Spectrogram")

# --- Load Background Image ---
background_image = None # Initialize as None
try:
    # Construct the full path to the image file relative to the script
    script_dir = os.path.dirname(__file__) # Get the directory the script is in
    image_path = os.path.join(script_dir, "choke2.png")
    print(f"Loading background image from: {image_path}") # Debug print

    # Load the image
    raw_background = pygame.image.load(image_path).convert() # Use convert for potential performance boost

    # Scale the image to fit the screen resolution
    background_image = pygame.transform.scale(raw_background, (WIDTH, HEIGHT))
    print("Background image loaded and scaled successfully.")

except pygame.error as e:
    print(f"Error loading background image 'bg1.png': {e}")
    print("Ensure 'bg1.png' is in the same directory as the script.")
    # background_image will remain None, game will run with black background

except FileNotFoundError:
    print(f"Error: 'bg1.png' not found.")
    print("Ensure 'bg1.png' is in the same directory as the script.")
    # background_image will remain None

# --- Colors ---
# Keep colors defined, they might be needed for elements drawn *over* the background
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)         # Circle
BLUE = (0, 0, 255)        # Cursor
YELLOW = (255, 255, 0)     # Sensitivity Info
CYAN = (0, 255, 255)       # Instructions
GREEN = (0, 255, 0)        # FPS & Good Times
ORANGE = (255, 165, 0)     # Medium Times
PINK = (255, 105, 180)     # Slower Times
GREY = (150, 150, 150)     # Spectrogram Axis/Labels
DARK_GREY = (50, 50, 50, 200) # Spectrogram Background (Add Alpha for slight transparency)

# --- Circle Properties ---
CIRCLE_RADIUS =10

# --- Spawn Area Configuration ---
SPAWN_AREA_SIZE = 200
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
HALF_SPAWN_SIZE = SPAWN_AREA_SIZE // 2
MIN_SPAWN_X = max(CIRCLE_RADIUS, CENTER_X - HALF_SPAWN_SIZE)
MAX_SPAWN_X = min(WIDTH - CIRCLE_RADIUS, CENTER_X + HALF_SPAWN_SIZE)
MIN_SPAWN_Y = max(CIRCLE_RADIUS, CENTER_Y - HALF_SPAWN_SIZE)
MAX_SPAWN_Y = min(HEIGHT - CIRCLE_RADIUS, CENTER_Y + HALF_SPAWN_SIZE)

# --- Game Variables ---
circle_x = 0
circle_y = 0
circle_active = False
start_time = 0
hit_times_ms = []
last_hit_info = None

# --- Delay Configuration ---
DELAY_MIN_S = 0.5
DELAY_MAX_S = 1.0
is_delaying = False
delay_start_time = 0.0
current_delay_duration = 0.0

font_large = pygame.font.Font(None, 30)
font_medium = pygame.font.Font(None, 24)
font_small = pygame.font.Font(None, 22)
font_tiny = pygame.font.Font(None, 18)

# --- Spectrogram Configuration ---
SPEC_HEIGHT = 120
SPEC_Y_POS = HEIGHT - SPEC_HEIGHT - 40
SPEC_MAX_TIME_MS = 1000.0
SPEC_WINDOW_SIZE = 100
SPEC_MARKER_HEIGHT = 8

# --- Sensitivity Simulation Settings ---
target_dpi = 1600
target_valorant_sens = 0.4
VALORANT_SENS_INCREMENT_FINE = 0.005
VALORANT_SENS_INCREMENT_COARSE = 0.05
DPI_INCREMENT = 50
REFERENCE_eDPI = 640.0

def calculate_sensitivity_multiplier(dpi, sens):
    current_eDPI = dpi * sens
    return current_eDPI / REFERENCE_eDPI

sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)

# --- Custom Cursor ---
cursor_x, cursor_y = CENTER_X, CENTER_Y
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)


def spawn_circle():
    global circle_x, circle_y, circle_active, start_time
    valid_x_range = MAX_SPAWN_X >= MIN_SPAWN_X
    valid_y_range = MAX_SPAWN_Y >= MIN_SPAWN_Y
    if valid_x_range: circle_x = random.randint(MIN_SPAWN_X, MAX_SPAWN_X)
    else: circle_x = CENTER_X
    if valid_y_range: circle_y = random.randint(MIN_SPAWN_Y, MAX_SPAWN_Y)
    else: circle_y = CENTER_Y
    circle_active = True
    start_time = time.time()


def draw_sensitivity_info():
    dpi_text = f"Target DPI: {target_dpi}"
    sens_text = f"Target Val Sens: {target_valorant_sens:.3f}"
    dpi_surf = font_large.render(dpi_text, True, YELLOW)
    sens_surf = font_large.render(sens_text, True, YELLOW)
    dpi_rect = dpi_surf.get_rect(topright=(WIDTH - 20, 10))
    sens_rect = sens_surf.get_rect(topright=(WIDTH - 20, 10 + dpi_rect.height + 5))
    screen.blit(dpi_surf, dpi_rect)
    screen.blit(sens_surf, sens_rect)

def draw_instructions_and_fps(current_fps):
    instructions = [
        f"FPS: {current_fps:.0f}",
        f"Spawn Size: {SPAWN_AREA_SIZE}px",
        f"Hits (Last {SPEC_WINDOW_SIZE}): {len(hit_times_ms)}",
        "-----------",
        "Controls:",
        "UP/DOWN: Adjust Val Sens (Fine)",
        "SHIFT+UP/DOWN: Adjust Val Sens (Coarse)",
        "LEFT/RIGHT: Adjust DPI",
        "ESC: Quit"
    ]
    y_offset = 10
    for i, line in enumerate(instructions):
        color = GREEN if i == 0 else CYAN
        text_surface = font_small.render(line, True, color)
        # Optional: Add background to text for better readability over image
        # text_surface.set_alpha(200) # Make text slightly transparent
        # bg_rect = text_surface.get_rect(topleft=(10, y_offset))
        # pygame.draw.rect(screen, (0,0,0, 150), bg_rect) # Semi-transparent black background
        text_rect = text_surface.get_rect(topleft=(10, y_offset))
        screen.blit(text_surface, text_rect)
        y_offset += text_rect.height + 3

def draw_last_hit_time_ms():
    if last_hit_info:
        x, y, time_ms = last_hit_info
        timer_text = f"{time_ms:.0f} ms"
        text_surface = font_small.render(timer_text, True, WHITE)
        # Add background for readability
        bg_rect = text_surface.get_rect(center=(x, y - CIRCLE_RADIUS - 15))
        pygame.draw.rect(screen, (0,0,0, 180), bg_rect.inflate(6,2)) # Slightly larger black bg
        text_rect = text_surface.get_rect(center=(x, y - CIRCLE_RADIUS - 15))
        screen.blit(text_surface, text_rect)

def get_time_color(time_ms):
    if time_ms <= 250: return GREEN
    elif time_ms <= 500: return ORANGE
    else: return PINK

def draw_spectrogram():
    if not hit_times_ms: return

    total_spec_width = WIDTH * 0.8
    spec_start_x = (WIDTH - total_spec_width) / 2
    slot_width = total_spec_width / SPEC_WINDOW_SIZE

    # Use a Surface for the spectrogram area for transparency control
    spec_surface = pygame.Surface((total_spec_width, SPEC_HEIGHT), pygame.SRCALPHA) # SRCALPHA enables per-pixel alpha
    spec_surface.fill(DARK_GREY) # Fill with semi-transparent dark grey

    axis_color = GREY
    axis_label_color = WHITE
    for ms_level in [0, 500, 1000]:
        if ms_level > SPEC_MAX_TIME_MS: continue
        normalized_time = ms_level / SPEC_MAX_TIME_MS
        y_pos = SPEC_HEIGHT * (1.0 - normalized_time) # Y pos relative to surface

        # Draw axis line ON THE SURFACE
        pygame.draw.line(spec_surface, axis_color, (0, y_pos), (total_spec_width, y_pos), 1)

        # Draw label TO THE MAIN SCREEN (left of the surface)
        label_surf = font_tiny.render(f"{ms_level}ms", True, axis_label_color)
        label_rect = label_surf.get_rect(centery=SPEC_Y_POS + y_pos, right=spec_start_x - 5)
        screen.blit(label_surf, label_rect)


    for i, hit_time in enumerate(hit_times_ms):
        normalized_hit_time = min(hit_time / SPEC_MAX_TIME_MS, 1.0)
        marker_center_y = SPEC_HEIGHT * (1.0 - normalized_hit_time) # Y relative to surface
        marker_center_x = (i + 0.5) * slot_width # X relative to surface
        marker_color = get_time_color(hit_time)
        marker_top_y = marker_center_y - SPEC_MARKER_HEIGHT / 2
        marker_bottom_y = marker_center_y + SPEC_MARKER_HEIGHT / 2

        # Draw marker ON THE SURFACE
        pygame.draw.line(spec_surface, marker_color, (marker_center_x, marker_top_y), (marker_center_x, marker_bottom_y), 2)

    # Blit the entire spectrogram surface onto the main screen
    screen.blit(spec_surface, (spec_start_x, SPEC_Y_POS))

    # Draw border around the blitted area on the main screen
    pygame.draw.rect(screen, GREY, (spec_start_x, SPEC_Y_POS, total_spec_width, SPEC_HEIGHT), 1)


def draw_cursor():
    #pygame.draw.circle(screen, BLUE, (int(cursor_x), int(cursor_y)), 5)
    pygame.draw.line(screen, WHITE, (int(cursor_x) - 8, int(cursor_y)), (int(cursor_x) + 8, int(cursor_y)), 1)
    pygame.draw.line(screen, WHITE, (int(cursor_x), int(cursor_y) - 8), (int(cursor_x), int(cursor_y) + 8), 1)


# --- Game Loop ---
running = True
clock = pygame.time.Clock()

while running:
    current_frame_time = time.time()

    # --- Event Handling ---
    keys_pressed = pygame.key.get_pressed()
    shift_pressed = keys_pressed[pygame.K_LSHIFT] or keys_pressed[pygame.K_RSHIFT]

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False

            # Sensitivity Adjustments
            current_sens_increment = VALORANT_SENS_INCREMENT_COARSE if shift_pressed else VALORANT_SENS_INCREMENT_FINE
            sens_changed = False
            if event.key == pygame.K_UP: target_valorant_sens += current_sens_increment; sens_changed = True
            elif event.key == pygame.K_DOWN: target_valorant_sens -= current_sens_increment; sens_changed = True
            elif event.key == pygame.K_RIGHT: target_dpi += DPI_INCREMENT; sens_changed = True
            elif event.key == pygame.K_LEFT: target_dpi -= DPI_INCREMENT; sens_changed = True

            target_valorant_sens = max(0.001, round(target_valorant_sens, 5))
            target_dpi = max(50, target_dpi)
            if sens_changed:
                 sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)

        # --- Hit Detection ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and circle_active:
                distance = math.hypot(cursor_x - circle_x, cursor_y - circle_y)
                if distance <= CIRCLE_RADIUS:
                    # --- HIT! ---
                    time_taken_sec = current_frame_time - start_time
                    time_taken_ms = time_taken_sec * 1000
                    hit_times_ms.append(time_taken_ms)
                    hit_times_ms = hit_times_ms[-SPEC_WINDOW_SIZE:]
                    last_hit_info = (circle_x, circle_y, time_taken_ms)
                    circle_active = False
                    is_delaying = True
                    delay_start_time = current_frame_time
                    current_delay_duration = random.uniform(DELAY_MIN_S, DELAY_MAX_S)

        if event.type == pygame.MOUSEMOTION:
            dx, dy = event.rel
            cursor_x += dx * sensitivity_multiplier
            cursor_y += dy * sensitivity_multiplier
            cursor_x = max(0, min(WIDTH - 1, cursor_x))
            cursor_y = max(0, min(HEIGHT - 1, cursor_y))

    # --- Game Logic ---
    if is_delaying:
        if current_frame_time - delay_start_time >= current_delay_duration:
            is_delaying = False
            spawn_circle()
    elif not circle_active and not is_delaying:
         spawn_circle()

    # --- Drawing ---
    # Draw Background FIRST
    if background_image:
        screen.blit(background_image, (0, 0))
    else:
        screen.fill(BLACK) # Fallback to black background if image failed to load

    # UI Elements (drawn OVER background)
    current_fps = clock.get_fps()
    draw_instructions_and_fps(current_fps)
    draw_sensitivity_info()
    if not circle_active:
        draw_last_hit_time_ms()
    draw_spectrogram()

    # Game Elements (drawn OVER background and some UI)
    if circle_active:
        pygame.draw.circle(screen, RED, (circle_x, circle_y), CIRCLE_RADIUS)

    draw_cursor() # Draw cursor last, on top of everything
    pygame.display.flip()
    clock.tick(144)

# --- Cleanup ---
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
