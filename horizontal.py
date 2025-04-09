import pygame
import random
import time
import math
import os # Import os module for path handling

# Initialize Pygame
pygame.init()
pygame.mixer.init()  # Initialize the sound mixer

# --- Screen Setup ---
try:
    display_info = pygame.display.Info()
    WIDTH, HEIGHT = display_info.current_w, display_info.current_h
except pygame.error:
    print("Could not get display info, using default 800x600.")
    WIDTH, HEIGHT = 800, 600

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Aim Trainer - Reaction Time Spectrogram")

# --- Load Background Image and Sound Effect ---
background_image = None # Initialize as None



# Load sound effect
explosion_sound = None
hit_sound = None
near_miss_sound = None

try:
    sound_path = os.path.join(os.path.dirname(__file__), "76097_578556_Swords_-_woosh_Celine_Woodburn_Swords_51_stereo_normal.ogg")
    print(f"Loading sound from: {sound_path}")
    near_miss_sound = pygame.mixer.Sound(sound_path)
    print("Sound effect loaded successfully.")
except (pygame.error, FileNotFoundError) as e:
    print(f"Error loading sound effect: {e}")
    print("Ensure the sound file is in the same directory as the script.")

try:
    sound_path = os.path.join(os.path.dirname(__file__), "metal-hit-94-200422.mp3")
    print(f"Loading sound from: {sound_path}")
    hit_sound = pygame.mixer.Sound(sound_path)
    print("Sound effect loaded successfully.")
except (pygame.error, FileNotFoundError) as e:
    print(f"Error loading sound effect: {e}")
    print("Ensure the sound file is in the same directory as the script.")

try:
    sound_path = os.path.join(os.path.dirname(__file__), "50669_423144_423143_Creatures_-_announcer_voice_classic_FPS_style_headshot_normal.ogg")
    print(f"Loading sound from: {sound_path}")
    explosion_sound = pygame.mixer.Sound(sound_path)
    print("Sound effect loaded successfully.")
except (pygame.error, FileNotFoundError) as e:
    print(f"Error loading sound effect: {e}")
    print("Ensure the sound file is in the same directory as the script.")

try:
    # Construct the full path to the image file relative to the script
    script_dir = os.path.dirname(__file__) # Get the directory the script is in
    image_path = os.path.join(script_dir, "choke4.png")
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

# Load the image
image = pygame.image.load("p1.png").convert()

# Set white (255, 255, 255) as the transparent color
image.set_colorkey((255, 255, 255))

# --- Colors ---
# Keep colors defined, they might be needed for elements drawn *over* the background
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)         # Circle and Missed targets
BLUE = (0, 0, 255)        # Cursor
YELLOW = (255, 255, 0)     # Sensitivity Info
CYAN = (0, 255, 255)       # Instructions
GREEN = (0, 255, 0)        # FPS & Good Times
ORANGE = (255, 165, 0)     # Medium Times
PINK = (255, 105, 180)     # Slower Times
GREY = (150, 150, 150)     # Spectrogram Axis/Labels
DARK_GREY = (50, 50, 50, 200) # Spectrogram Background (Add Alpha for slight transparency)
PURPLE = (128, 0, 128)     # New color for off-target hits

# --- Target Color Change Configuration ---
TARGET_COLOR_CHANGE_MS = 25  # Change color every 25ms
target_color = YELLOW  # Starting color
last_color_change_time = 0

# --- Circle Properties ---
CIRCLE_RADIUS = 35 - 15

# --- Spawn Area Configuration ---
SPAWN_AREA_SIZE = 100
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
HALF_SPAWN_SIZE = SPAWN_AREA_SIZE // 2
MIN_SPAWN_X = max(CIRCLE_RADIUS, CENTER_X - HALF_SPAWN_SIZE)
MAX_SPAWN_X = min(WIDTH - CIRCLE_RADIUS, CENTER_X + HALF_SPAWN_SIZE)
MIN_SPAWN_Y = max(CIRCLE_RADIUS, CENTER_Y - HALF_SPAWN_SIZE)
MAX_SPAWN_Y = min(HEIGHT - CIRCLE_RADIUS, CENTER_Y + HALF_SPAWN_SIZE)

# --- Game Variables ---
circle_x = 0
circle_y = 0

# --- Target Type Management ---
target_type = "random"  # Starts with random position targets, alternates with "center"

circle_active = False
start_time = 0
hit_times_ms = []
miss_flags = []  # New list to track whether each entry was a miss
last_hit_info = None

# --- Target Timeout Configuration ---
TARGET_TIMEOUT_MS = 350  # Target disappears after x ms
TARGET_CENTER_TIMEOUT_MS = 350  # Faster timeout for center targets
timeout_expired = False  # Track if the target timed out

# --- Delay Configuration ---
DELAY_MIN_S = 1.0
DELAY_MAX_S = 2.0
is_delaying = False
delay_start_time = 0.0
current_delay_duration = 0.0

font_large = pygame.font.Font(None, 36)  # Increased font size for top timing display
font_medium = pygame.font.Font(None, 24)
font_small = pygame.font.Font(None, 22)
font_tiny = pygame.font.Font(None, 18)

# --- Spectrogram Configuration ---
SPEC_HEIGHT = 120
SPEC_Y_POS = HEIGHT - SPEC_HEIGHT - 40
SPEC_MAX_TIME_MS = TARGET_TIMEOUT_MS
SPEC_WINDOW_SIZE = 20
SPEC_MARKER_HEIGHT = 8

# --- Timeline Configuration ---
TIMELINE_LENGTH_SECONDS = 20
TIMELINE_HEIGHT = 60
TIMELINE_Y_POS = SPEC_Y_POS - TIMELINE_HEIGHT - 20
TIMELINE_BG_COLOR = (30, 30, 30, 200)
TARGET_ACTIVE_COLOR = (150, 150, 255, 150)  # Semi-transparent blue
HIT_MARKER_COLOR = GREEN
MISS_MARKER_COLOR = RED
OFF_TARGET_HIT_COLOR = PURPLE  # New color for off-target hits
TIMELINE_AXIS_COLOR = GREY

# --- Timeline Visibility Toggle ---
show_timeline = True  # New variable to track timeline visibility

# --- Timeline Data Structure ---
# List of event tuples: (timestamp, event_type, duration)
# event_type: "target_active", "hit", "miss", "off_target_hit"
timeline_events = []

# --- Sensitivity Simulation Settings ---
target_dpi = 1600
target_valorant_sens = 0.2
VALORANT_SENS_INCREMENT_FINE = 0.005
VALORANT_SENS_INCREMENT_COARSE = 0.05
DPI_INCREMENT = 50

TIME_BAR = 250
DONT_CHANGE_TARGET_COLOR = True

def calculate_sensitivity_multiplier(dpi, sens):
    current_eDPI = dpi * sens
    return sens

sensitivity_multiplier = calculate_sensitivity_multiplier(target_dpi, target_valorant_sens)

# --- Custom Cursor ---
cursor_x, cursor_y = CENTER_X, CENTER_Y
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)


def spawn_circle():
    global circle_x, circle_y, circle_active, start_time, timeout_expired, last_color_change_time, target_color, target_type
    
    # Determine target position based on target_type
    if target_type != "random" and False:
        # Center target
        circle_x = CENTER_X
        circle_y = CENTER_Y
    else:
        # Modified random position to be either 25px left or right
        # Randomly choose -25 or +25 for the x-offset
        x_offset = random.choice([25, -25])
        circle_x = CENTER_X + x_offset
        circle_y = CENTER_Y  # Keep y position at center
        
    circle_active = True
    timeout_expired = False
    start_time = time.time()
    last_color_change_time = start_time
    target_color = YELLOW  # Reset target color when spawning
    
    # Add target activation event to timeline
    # Use appropriate timeout based on target type
    if target_type == "center":
        add_timeline_event("target_active", TARGET_CENTER_TIMEOUT_MS/1000)  # Convert ms to seconds
    else:
        add_timeline_event("target_active", TARGET_TIMEOUT_MS/1000)  # Convert ms to seconds

def update_target_color(current_time):
    global target_color, last_color_change_time
    if DONT_CHANGE_TARGET_COLOR:
        return
    
    time_since_last_change_ms = (current_time - last_color_change_time) * 1000
    
    if time_since_last_change_ms >= TARGET_COLOR_CHANGE_MS:
        # Calculate how many 25ms intervals have passed since the last change
        intervals_passed = int(time_since_last_change_ms / TARGET_COLOR_CHANGE_MS)
        last_color_change_time += (intervals_passed * TARGET_COLOR_CHANGE_MS) / 1000
        
        # Calculate time visible as a percentage of timeout
        time_visible_ms = (current_time - start_time) * 1000
        progress = min(time_visible_ms / TARGET_TIMEOUT_MS, 1.0)
        
        # Generate a color that shifts from red to yellow as time progresses
        r = 255
        g = int(255 * progress)
        b = 0
        
        target_color = (r, g, b)


def draw_sensitivity_info():
    dpi_text = f"Target DPI: {target_dpi}"
    sens_text = f"Target Val Sens: {target_valorant_sens:.3f}"
    mode_text = f"Target Mode: {target_type.capitalize()}"
    dpi_surf = font_large.render(dpi_text, True, YELLOW)
    sens_surf = font_large.render(sens_text, True, YELLOW)
    mode_surf = font_large.render(mode_text, True, YELLOW)
    dpi_rect = dpi_surf.get_rect(topright=(WIDTH - 20, 10))
    sens_rect = sens_surf.get_rect(topright=(WIDTH - 20, 10 + dpi_rect.height + 5))
    mode_rect = mode_surf.get_rect(topright=(WIDTH - 20, 10 + dpi_rect.height + sens_rect.height + 10))
    screen.blit(dpi_surf, dpi_rect)
    screen.blit(sens_surf, sens_rect)
    screen.blit(mode_surf, mode_rect)

def draw_instructions_and_fps(current_fps):
    instructions = [
        f"FPS: {current_fps:.0f}",
        f"Spawn Size: {SPAWN_AREA_SIZE}px",
        f"Hits (Last {SPEC_WINDOW_SIZE}): {len(hit_times_ms)}",
        f"Target Timeout: {TARGET_TIMEOUT_MS}ms / Center: {TARGET_CENTER_TIMEOUT_MS}ms",
        f"Target Color Change: {TARGET_COLOR_CHANGE_MS}ms",
        "Timeline: Last 20 seconds",
        "-----------",
        "Controls:",
        "Left Click / Left CTRL: Fire",
        "UP/DOWN: Adjust Val Sens (Fine)",
        "SHIFT+UP/DOWN: Adjust Val Sens (Coarse)",
        "LEFT/RIGHT: Adjust DPI",
        f"T: {'Hide' if show_timeline else 'Show'} Timeline",
        "ESC: Quit"
    ]
    y_offset = 10
    for i, line in enumerate(instructions):
        color = GREEN if i == 0 else CYAN
        text_surface = font_small.render(line, True, color)
        text_rect = text_surface.get_rect(topleft=(10, y_offset))
        screen.blit(text_surface, text_rect)
        y_offset += text_rect.height + 3

def get_time_color(time_ms, is_miss):
    if is_miss:
        return RED  # Return red for missed targets
    elif time_ms <= TIME_BAR:
        return GREEN
    elif time_ms <= TARGET_TIMEOUT_MS:
        return ORANGE
    else:
        return PINK

def draw_timing_display():
    if last_hit_info:
        _, _, time_ms, was_timeout = last_hit_info
        
        if was_timeout:
            timer_text = f"MISSED"
            color = RED  # Use red for missed targets
        else:
            timer_text = f"{time_ms:.0f} ms"
            color = get_time_color(time_ms, False)  # Use the same color as in the spectrogram
            
        # Create larger text centered in the middle of the screen, offset by 100px up
        text_surface = font_large.render(timer_text, True, color)
        
        # Add background for better readability
        bg_rect = text_surface.get_rect(center=(WIDTH // 2, CENTER_Y - 100))
        bg_rect_inflated = bg_rect.inflate(20, 10)  # Make the background slightly larger
        pygame.draw.rect(screen, BLACK, bg_rect_inflated)
        pygame.draw.rect(screen, DARK_GREY, bg_rect_inflated, 1)  # Border using spectrogram colors
        
        # Draw the text
        text_rect = text_surface.get_rect(center=(WIDTH // 2, CENTER_Y - 100))
        screen.blit(text_surface, text_rect)

def draw_spectrogram():
    global hit_times_ms, miss_flags
    if not hit_times_ms:
        return

    total_spec_width = WIDTH * 0.8
    spec_start_x = (WIDTH - total_spec_width) / 2
    slot_width = total_spec_width / SPEC_WINDOW_SIZE
    
    # Increase the bar width (make them "fattier")
    bar_width = slot_width * 0.7  # Use 70% of slot width for the bar, leaving 30% as spacing

    # Use a Surface for the spectrogram area for transparency control
    spec_surface = pygame.Surface((total_spec_width, SPEC_HEIGHT), pygame.SRCALPHA) # SRCALPHA enables per-pixel alpha
    spec_surface.fill(DARK_GREY) # Fill with semi-transparent dark grey

    axis_color = GREY
    axis_label_color = WHITE
    for ms_level in [0, TIME_BAR, SPEC_MAX_TIME_MS]:
        if ms_level > SPEC_MAX_TIME_MS:
            continue
        normalized_time = ms_level / SPEC_MAX_TIME_MS
        y_pos = SPEC_HEIGHT * (1.0 - normalized_time) # Y pos relative to surface

        # Draw axis line ON THE SURFACE
        pygame.draw.line(spec_surface, axis_color, (0, y_pos), (total_spec_width, y_pos), 1)

        # Draw label TO THE MAIN SCREEN (left of the surface)
        label_surf = font_tiny.render(f"{ms_level}ms", True, axis_label_color)
        label_rect = label_surf.get_rect(centery=SPEC_Y_POS + y_pos, right=spec_start_x - 5)
        screen.blit(label_surf, label_rect)

    for i, (hit_time, is_miss) in enumerate(zip(hit_times_ms, miss_flags)):
        normalized_hit_time = min(hit_time / SPEC_MAX_TIME_MS, 1.0)
        
        # Calculate the height of the bar based on hit time
        bar_height = SPEC_HEIGHT * normalized_hit_time
        
        # Position the bar at the bottom of the spectrogram
        bar_x = i * slot_width + (slot_width - bar_width) / 2  # Center the bar in its slot
        bar_y = SPEC_HEIGHT - bar_height  # Start from the bottom up
        
        # Get the appropriate color for this hit time
        bar_color = get_time_color(hit_time, is_miss)
        
        # Draw a filled rectangle from 0 to the hit time
        pygame.draw.rect(spec_surface, bar_color, (bar_x, bar_y, bar_width, bar_height))
        
        # Add a border to the bar for better visibility
        pygame.draw.rect(spec_surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    # Blit the entire spectrogram surface onto the main screen
    screen.blit(spec_surface, (spec_start_x, SPEC_Y_POS))

    # Draw border around the blitted area on the main screen
    pygame.draw.rect(screen, GREY, (spec_start_x, SPEC_Y_POS, total_spec_width, SPEC_HEIGHT), 1)

def add_timeline_event(event_type, duration=None):
    global timeline_events
    
    """Add an event to the timeline with current timestamp"""
    current_time = time.time()
    timeline_events.append((current_time, event_type, duration))
    
    # Clean up old events (older than TIMELINE_LENGTH_SECONDS)
    cutoff_time = current_time - TIMELINE_LENGTH_SECONDS
    timeline_events = [event for event in timeline_events if event[0] >= cutoff_time]

def draw_timeline():
    """Draw the timeline showing the last TIMELINE_LENGTH_SECONDS"""
    # Skip drawing if timeline is hidden
    if not show_timeline:
        return
        
    current_time = time.time()
    cutoff_time = current_time - TIMELINE_LENGTH_SECONDS
    
    # Timeline dimensions
    total_timeline_width = WIDTH * 0.8
    timeline_start_x = (WIDTH - total_timeline_width) / 2
    
    # Create a surface for the timeline with alpha channel
    timeline_surface = pygame.Surface((total_timeline_width, TIMELINE_HEIGHT), pygame.SRCALPHA)
    timeline_surface.fill(TIMELINE_BG_COLOR)
    
    # Draw time markers (every second)
    for i in range(TIMELINE_LENGTH_SECONDS + 1):
        sec_pos = total_timeline_width * (1.0 - i / TIMELINE_LENGTH_SECONDS)
        # Draw tick marks
        tick_height = 10 if i % 5 == 0 else 5  # Taller tick marks every 5 seconds
        pygame.draw.line(timeline_surface, TIMELINE_AXIS_COLOR, 
                        (sec_pos, TIMELINE_HEIGHT), 
                        (sec_pos, TIMELINE_HEIGHT - tick_height), 
                        1)
        
        # Add labels every 5 seconds
        if i % 5 == 0:
            label = font_tiny.render(f"-{i}s", True, WHITE)
            label_rect = label.get_rect(midtop=(sec_pos, TIMELINE_HEIGHT - 15))
            timeline_surface.blit(label, label_rect)
    
    # Draw horizontal axis line
    pygame.draw.line(timeline_surface, TIMELINE_AXIS_COLOR, 
                    (0, TIMELINE_HEIGHT - 1), 
                    (total_timeline_width, TIMELINE_HEIGHT - 1), 
                    1)
    
    # Draw events on the timeline
    for timestamp, event_type, duration in timeline_events:
        # Skip events outside our time window
        if timestamp < cutoff_time:
            continue
        
        # Calculate position on timeline (transform from time to x-position)
        relative_time = current_time - timestamp  # seconds ago
        event_x_pos = total_timeline_width * (1.0 - relative_time / TIMELINE_LENGTH_SECONDS)
        
        if event_type == "target_active" and duration is not None:
            # Draw a rectangle for the duration of target activity
            rect_width = (duration / TIMELINE_LENGTH_SECONDS) * total_timeline_width
            rect_height = TIMELINE_HEIGHT - 20  # Leave space for tick marks and time labels
            pygame.draw.rect(timeline_surface, TARGET_ACTIVE_COLOR, 
                          (event_x_pos, 0, rect_width, rect_height))
            pygame.draw.rect(timeline_surface, WHITE, 
                          (event_x_pos, 0, rect_width, rect_height), 1)
                          
        elif event_type == "hit":
            # Draw a green marker for a hit
            marker_height = 20
            pygame.draw.polygon(timeline_surface, HIT_MARKER_COLOR, 
                             [(event_x_pos, TIMELINE_HEIGHT - 20 - marker_height),
                              (event_x_pos - 5, TIMELINE_HEIGHT - 20),
                              (event_x_pos + 5, TIMELINE_HEIGHT - 20)], 
                             0)  # 0 means filled
                             
        elif event_type == "miss":
            # Draw a red dot for a miss instead of a cross
            marker_size = 5
            marker_y = TIMELINE_HEIGHT - 25
            pygame.draw.circle(timeline_surface, MISS_MARKER_COLOR,
                           (event_x_pos, marker_y),
                           marker_size, 0)  # 0 means filled
                          
        elif event_type == "off_target_hit":
            # Draw a purple circle for an off-target hit
            marker_size = 5
            marker_y = TIMELINE_HEIGHT - 25
            pygame.draw.circle(timeline_surface, OFF_TARGET_HIT_COLOR,
                           (event_x_pos, marker_y),
                           marker_size, 0)  # 0 means filled
    
    # Blit the timeline surface onto the main screen
    screen.blit(timeline_surface, (timeline_start_x, TIMELINE_Y_POS))
    
    # Draw border around the timeline area
    pygame.draw.rect(screen, GREY, (timeline_start_x, TIMELINE_Y_POS, total_timeline_width, TIMELINE_HEIGHT), 1)
    
    # Add timeline label and legend
    label = font_small.render("Timeline (last 20 seconds)", True, WHITE)
    label_rect = label.get_rect(bottomleft=(timeline_start_x, TIMELINE_Y_POS - 5))
    screen.blit(label, label_rect)
    
    # Add a small legend to explain the different markers
    legend_start_x = timeline_start_x + total_timeline_width - 240
    legend_y = TIMELINE_Y_POS - 25
    
    # Hit marker
    marker_width = 10
    pygame.draw.polygon(screen, HIT_MARKER_COLOR, 
                    [(legend_start_x, legend_y),
                     (legend_start_x - marker_width//2, legend_y + marker_width),
                     (legend_start_x + marker_width//2, legend_y + marker_width)], 
                    0)
    hit_text = font_tiny.render("Hit", True, WHITE)
    screen.blit(hit_text, (legend_start_x + 10, legend_y))
    
    # Off-target hit marker
    legend_start_x += 60
    pygame.draw.circle(screen, OFF_TARGET_HIT_COLOR,
                   (legend_start_x, legend_y + marker_width//2),
                   marker_width//2, 0)
    off_hit_text = font_tiny.render("Off-target", True, WHITE)
    screen.blit(off_hit_text, (legend_start_x + 10, legend_y))
    
    # Miss marker (now a dot instead of a cross)
    legend_start_x += 90
    pygame.draw.circle(screen, MISS_MARKER_COLOR,
                   (legend_start_x, legend_y + marker_width//2),
                   marker_width//2, 0)
    miss_text = font_tiny.render("Miss", True, WHITE)
    screen.blit(miss_text, (legend_start_x + 10, legend_y))

def draw_cursor():
    # Draw a small white rectangle with black border
    rect_width = 2
    rect_height = 2
    rect_x = int(cursor_x) - rect_width // 2
    rect_y = int(cursor_y) - rect_height // 2
    
    # Draw black border (by drawing a slightly larger black rectangle)
    pygame.draw.rect(screen, BLACK, (rect_x-1, rect_y-1, rect_width+2, rect_height+2))
    # Draw white inner rectangle
    pygame.draw.rect(screen, WHITE, (rect_x, rect_y, rect_width, rect_height))

# Function to process hit detection
def process_hit():
    global circle_active, is_delaying, delay_start_time, current_delay_duration, last_hit_info, hit_times_ms, miss_flags, target_type
    if not circle_active:
        distance = math.hypot(cursor_x - circle_x, cursor_y - circle_y)
        if distance <= CIRCLE_RADIUS:
            if near_miss_sound:
                near_miss_sound.play()
    
    if circle_active:
        distance = math.hypot(cursor_x - circle_x, cursor_y - circle_y)
        if distance <= CIRCLE_RADIUS:
            # --- HIT! ---
            time_taken_sec = time.time() - start_time
            time_taken_ms = time_taken_sec * 1000
            hit_times_ms.append(time_taken_ms)
            miss_flags.append(False)  # Not a miss
            # Keep only the latest SPEC_WINDOW_SIZE entries
            if len(hit_times_ms) > SPEC_WINDOW_SIZE:
                hit_times_ms = hit_times_ms[-SPEC_WINDOW_SIZE:]
                miss_flags = miss_flags[-SPEC_WINDOW_SIZE:]
            last_hit_info = (circle_x, circle_y, time_taken_ms, False)  # False means not a timeout
            
            # Add hit event to timeline
            add_timeline_event("hit")
            
            # Play explosion sound if reaction time is below 280ms
            if random.random() < 0.25:
                if explosion_sound: explosion_sound.play()
            else:
                if hit_sound: hit_sound.play()
                
            # Toggle target type for next spawn
            if random.random() > 0.25:
                target_type = "random"
            else:
                target_type = "center"
            
            circle_active = False
            is_delaying = True
            delay_start_time = time.time()
            current_delay_duration = random.uniform(DELAY_MIN_S, DELAY_MAX_S)
            return True
        else:
            # Click was made but missed the target
            add_timeline_event("off_target_hit")
            return False
    else:
        # No active target, but user clicked
        add_timeline_event("off_target_hit")
    return False

# --- Game Loop ---
running = True
clock = pygame.time.Clock()

while running:
    current_frame_time = time.time()

    # --- Event Handling ---
    keys_pressed = pygame.key.get_pressed()
    shift_pressed = keys_pressed[pygame.K_LSHIFT] or keys_pressed[pygame.K_RSHIFT]

    is_hitting = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            
            # Toggle timeline visibility with T key
            if event.key == pygame.K_t:
                show_timeline = not show_timeline
            
            # Fire with left CTRL key (single press)
            if event.key == pygame.K_LCTRL:
                process_hit()
                is_hitting = True

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

        # --- Hit Detection with Mouse ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                process_hit()
                is_hitting = True

        if event.type == pygame.MOUSEMOTION:
            dx, dy = event.rel
            cursor_x += dx * sensitivity_multiplier
            cursor_y += dy * sensitivity_multiplier
            cursor_x = max(0, min(WIDTH - 1, cursor_x))
            cursor_y = max(0, min(HEIGHT - 1, cursor_y))

    # --- Game Logic ---
    # Update target color if active
    if circle_active and not timeout_expired:
        update_target_color(current_frame_time)
        
    # Check for target timeout
    if circle_active and not timeout_expired:
        time_visible_ms = (current_frame_time - start_time) * 1000
        
        # Use the appropriate timeout based on target type
        current_timeout = TARGET_CENTER_TIMEOUT_MS if target_type == "center" else TARGET_TIMEOUT_MS
        
        if time_visible_ms >= current_timeout:
            # Target timed out - mark as missed
            
            # Toggle target type for next spawn
            if random.random() > 0.25:
                target_type = "random"
            else:
                target_type = "center"
            
            timeout_expired = True
            circle_active = False
            last_hit_info = (circle_x, circle_y, current_timeout, True)  # True means it was a timeout
            hit_times_ms.append(current_timeout)  # Add timeout value to hit times
            miss_flags.append(True)  # This was a miss
            # Keep only the latest SPEC_WINDOW_SIZE entries
            if len(hit_times_ms) > SPEC_WINDOW_SIZE:
                hit_times_ms = hit_times_ms[-SPEC_WINDOW_SIZE:]
                miss_flags = miss_flags[-SPEC_WINDOW_SIZE:]
                
            # Add miss event to timeline
            add_timeline_event("miss")
                
            is_delaying = True
            delay_start_time = current_frame_time
            current_delay_duration = random.uniform(DELAY_MIN_S, DELAY_MAX_S)

    if is_delaying and not is_hitting:
        if current_frame_time - delay_start_time >= current_delay_duration:
            is_delaying = False
            spawn_circle()
    elif not circle_active and not is_delaying and not is_hitting:
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
    draw_timing_display()  # Always draw timing display, regardless of circle state
    draw_spectrogram()
    draw_timeline()  # Draw the timeline if visible

    # Game Elements (drawn OVER background and some UI)
    if circle_active and not timeout_expired:
        pygame.draw.circle(screen, target_color, (circle_x, circle_y), CIRCLE_RADIUS)
        # Display different colors or indicators based on target type
        #if target_type == "center":
        #    pygame.draw.circle(screen, target_color, (circle_x, circle_y), CIRCLE_RADIUS + 2, 1)  # Cyan outline for center targets
        screen.blit(image, (circle_x-12, circle_y-6))

    draw_cursor() # Draw cursor last, on top of everything
    pygame.display.flip()
    clock.tick(144)

# --- Cleanup ---
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
