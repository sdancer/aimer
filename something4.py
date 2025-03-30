import pygame
import random
import time
import math

# Initialize Pygame
pygame.init()

# --- Screen Setup ---
try:
    display_info = pygame.display.Info()
    WIDTH, HEIGHT = display_info.current_w, display_info.current_h
except pygame.error:
    print("Could not get display info, using default 800x600.")
    WIDTH, HEIGHT = 1920, 1280

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Aim Trainer - Delayed Spawn & Sliding Histogram")

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)       # Cursor
YELLOW = (255, 255, 0)    # Sensitivity Info
CYAN = (0, 255, 255)      # Instructions
GREEN = (0, 255, 0)       # FPS
ORANGE = (255, 165, 0)    # Histogram bars
GREY = (150, 150, 150)    # Histogram labels

# --- Circle Properties ---
CIRCLE_RADIUS = 10       # Fixed radius

# --- Spawn Area Configuration ---
SPAWN_AREA_SIZE = 200    # The side length of the square spawn area
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
start_time = 0           # Time when the current circle spawned
hit_times_ms = []        # List to store successful hit times in milliseconds (will be capped)
last_hit_info = None     # Store (x, y, time_ms) of the last hit for text display

# --- Delay Configuration ---
DELAY_MIN_S = 0.5       # Minimum delay after hit (seconds)
DELAY_MAX_S = 1.0       # Maximum delay after hit (seconds)
is_delaying = False     # Flag indicating if we are in the post-hit delay phase
delay_start_time = 0.0  # When the current delay started
current_delay_duration = 0.0 # The duration of the current delay

font_large = pygame.font.Font(None, 30)
font_medium = pygame.font.Font(None, 24) # For histogram labels/counts
font_small = pygame.font.Font(None, 22)

# --- Histogram Configuration ---
HISTO_HEIGHT = 100       # Max height of histogram bars
HISTO_Y_POS = HEIGHT - HISTO_HEIGHT - 30 # Position histogram near the bottom
HISTO_BINS_MS = [100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 750, 1000] # Adjusted bins
HISTO_OVERFLOW_LABEL = ">1000"
HISTOGRAM_WINDOW_SIZE = 20 # Keep track of the last N hits

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
    """Spawns a new circle within the configured central area."""
    global circle_x, circle_y, circle_active, start_time
    valid_x_range = MAX_SPAWN_X >= MIN_SPAWN_X
    valid_y_range = MAX_SPAWN_Y >= MIN_SPAWN_Y
    if valid_x_range: circle_x = random.randint(MIN_SPAWN_X, MAX_SPAWN_X)
    else: circle_x = CENTER_X
    if valid_y_range: circle_y = random.randint(MIN_SPAWN_Y, MAX_SPAWN_Y)
    else: circle_y = CENTER_Y
    circle_active = True
    start_time = time.time() # Record spawn time for reaction calculation


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
        f"Hits (Last {HISTOGRAM_WINDOW_SIZE}): {len(hit_times_ms)}", # Show hits in window
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
        text_rect = text_surface.get_rect(topleft=(10, y_offset))
        screen.blit(text_surface, text_rect)
        y_offset += text_rect.height + 3

def draw_last_hit_time_ms():
    """Displays the time of the *last* successful hit near its location."""
    if last_hit_info:
        x, y, time_ms = last_hit_info
        timer_text = f"{time_ms:.0f} ms"
        color = GREEN if time_ms < 300 else CYAN
        text_surface = font_small.render(timer_text, True, color)
        text_rect = text_surface.get_rect(center=(x, y - CIRCLE_RADIUS - 15))
        screen.blit(text_surface, text_rect)

def draw_histogram():
    """Draws a histogram of the last N hit times at the bottom."""
    if not hit_times_ms: # Don't draw if no hits yet
        return

    num_bins = len(HISTO_BINS_MS) + 1 # +1 for the overflow bin
    bin_counts = [0] * num_bins
    max_count_in_window = 0 # Max count within the current window for scaling

    # --- Binning the data (only last N hits) ---
    # hit_times_ms already contains only the last N hits
    for hit_time in hit_times_ms:
        binned = False
        for i, bin_upper_limit in enumerate(HISTO_BINS_MS):
            if hit_time <= bin_upper_limit:
                bin_counts[i] += 1
                max_count_in_window = max(max_count_in_window, bin_counts[i])
                binned = True
                break
        if not binned: # Falls into the overflow bin
            bin_counts[-1] += 1
            max_count_in_window = max(max_count_in_window, bin_counts[-1])

    if max_count_in_window == 0: # Avoid division by zero
        return

    # --- Drawing the bars ---
    total_histo_width = WIDTH * 0.8
    histo_start_x = (WIDTH - total_histo_width) / 2
    bar_width = total_histo_width / num_bins
    bar_spacing = bar_width * 0.1
    actual_bar_width = bar_width - bar_spacing

    for i, count in enumerate(bin_counts):
        # Scale bar height based on the max count *within the current window*
        bar_height = int((count / max_count_in_window) * HISTO_HEIGHT)
        bar_x = histo_start_x + i * bar_width
        bar_y = HISTO_Y_POS + (HISTO_HEIGHT - bar_height)

        pygame.draw.rect(screen, ORANGE, (bar_x, bar_y, actual_bar_width, bar_height))

        if i < len(HISTO_BINS_MS):
            lower_limit = HISTO_BINS_MS[i-1] + 1 if i > 0 else 0
            label_text = f"{lower_limit}-{HISTO_BINS_MS[i]}"
        else:
            label_text = HISTO_OVERFLOW_LABEL

        label_surface = font_small.render(label_text, True, GREY)
        label_rect = label_surface.get_rect(center=(bar_x + actual_bar_width / 2, HISTO_Y_POS + HISTO_HEIGHT + 15))
        screen.blit(label_surface, label_rect)

        if count > 0:
            count_surface = font_medium.render(str(count), True, WHITE)
            count_rect = count_surface.get_rect(center=(bar_x + actual_bar_width / 2, bar_y - 10))
            screen.blit(count_surface, count_rect)


def draw_cursor():
    pygame.draw.circle(screen, BLUE, (int(cursor_x), int(cursor_y)), 5)
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
            if event.button == 1 and circle_active: # Left click and circle is present
                distance = math.hypot(cursor_x - circle_x, cursor_y - circle_y)
                if distance <= CIRCLE_RADIUS:
                    # --- HIT! ---
                    time_taken_sec = current_frame_time - start_time
                    time_taken_ms = time_taken_sec * 1000

                    # Add hit time and manage sliding window
                    hit_times_ms.append(time_taken_ms)
                    hit_times_ms = hit_times_ms[-HISTOGRAM_WINDOW_SIZE:] # Keep only the last N hits

                    last_hit_info = (circle_x, circle_y, time_taken_ms) # Store info for text display
                    circle_active = False # Deactivate circle

                    # Start the delay
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
    # Check if delay period is over
    if is_delaying:
        if current_frame_time - delay_start_time >= current_delay_duration:
            is_delaying = False
            # Delay is over, NOW spawn the next circle
            spawn_circle()
    # Spawn initial circle or if no delay is active and no circle exists
    elif not circle_active and not is_delaying:
         spawn_circle()


    # --- Drawing ---
    screen.fill(BLACK)

    # UI Elements
    current_fps = clock.get_fps()
    draw_instructions_and_fps(current_fps)
    draw_sensitivity_info()
    # Only draw last hit time if we are NOT currently drawing an active circle
    if not circle_active:
        draw_last_hit_time_ms()
    draw_histogram()

    # Game Elements - Only draw if not delaying
    if circle_active:
        pygame.draw.circle(screen, RED, (circle_x, circle_y), CIRCLE_RADIUS)

    draw_cursor()
    pygame.display.flip()
    clock.tick(144)

# --- Cleanup ---
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
