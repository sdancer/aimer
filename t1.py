#!/usr/bin/env python

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import (
    WindowProperties, CollisionTraverser, CollisionNode, 
    CollisionRay, CollisionHandlerQueue, CollisionSphere, Vec3, Vec4, 
    NodePath, BitMask32, LPoint3, TextNode, CardMaker
)
import random
import math
import time

# Constants
VALORANT_FOV = 103  # Valorant's default FOV
TARGET_SIZE = 0.5
TARGET_COUNT = 10
TARGET_SPAWN_RADIUS = 15
CROSSHAIR_SIZE = 0.02  # Increased crosshair size
MOUSE_SENSITIVITY = 0.2
TARGET_COLORS = {
    "normal": (1, 0, 0, 1),    # Bright red
    "hit": (0, 1, 0, 1)        # Green
}

class ValorantAimTrainer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # Set up window properties
        self.setup_window()
        
        # Set up the camera and FOV
        self.setup_camera()
        
        # Hide default mouse cursor and set up first-person mouse control
        self.setup_mouse_control()
        
        # Set up collision detection
        self.setup_collision()
        
        # Create crosshair
        self.create_crosshair()
        
        # Set up stats and UI
        self.stats = {
            "hits": 0,
            "shots": 0,
            "start_time": time.time(),
            "targets_spawned": 0
        }
        self.create_ui()
        
        # Create targets
        self.targets = []
        self.spawn_targets(TARGET_COUNT)
        
        # Set up key bindings
        self.accept("escape", self.quit_game)
        self.accept("mouse1", self.shoot)
        self.accept("r", self.reset_game)
        
        # Start the task to update stats
        self.taskMgr.add(self.update_stats_task, "UpdateStatsTask")

    def setup_window(self):
        """Set up window properties"""
        props = WindowProperties()
        props.setTitle("Valorant-Style Aim Trainer")
        props.setFullscreen(True)  # Set to fullscreen
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        
        # Set background color to black
        self.setBackgroundColor(0, 0, 0, 1)
        
        # Disable default camera controls
        self.disableMouse()

    def setup_camera(self):
        """Set up the camera with Valorant's FOV"""
        # Set the field of view
        self.camLens.setFov(VALORANT_FOV)
        
        # Position the camera
        self.camera.setPos(0, 0, 0)
        self.camera.setHpr(0, 0, 0)

    def setup_mouse_control(self):
        """Set up first-person mouse control"""
        self.heading = 0
        self.pitch = 0
        
        # Center mouse position
        self.center_x = 0
        self.center_y = 0
        
        # Set mouse to relative mode for better FPS controls
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)
        
        # Add task to handle mouse movement
        self.taskMgr.add(self.mouse_task, "MouseTask")

    def mouse_task(self, task):
        """Handle mouse movement for camera control"""
        if self.mouseWatcherNode.hasMouse():
            # Get mouse position delta in relative mode
            dx = self.mouseWatcherNode.getMouseX()
            dy = self.mouseWatcherNode.getMouseY()
            
            # Only update if there's significant movement to prevent jitter
            if abs(dx) > 0.001 or abs(dy) > 0.001:
                # Apply sensitivity to mouse movement
                self.heading -= dx * MOUSE_SENSITIVITY * 100
                self.pitch -= dy * MOUSE_SENSITIVITY * 100
                
                # Limit pitch to 90 degrees up and down
                self.pitch = max(-90, min(90, self.pitch))
                
                # Set the camera's orientation
                self.camera.setHpr(self.heading, self.pitch, 0)
                
        return Task.cont

    def setup_collision(self):
        """Set up collision detection for shooting targets"""
        self.cTrav = CollisionTraverser()
        self.shooterRay = CollisionRay()
        self.shooterNode = CollisionNode('shooterRay')
        self.shooterNode.addSolid(self.shooterRay)
        self.shooterNode.setFromCollideMask(BitMask32.bit(1))
        self.shooterNode.setIntoCollideMask(BitMask32.allOff())
        self.shooterNP = self.camera.attachNewNode(self.shooterNode)
        self.shooterRay.setOrigin(0, 0, 0)
        self.shooterRay.setDirection(0, 1, 0)
        
        self.shooterHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.shooterNP, self.shooterHandler)

    def create_crosshair(self):
        """Create a crosshair in the center of the screen"""
        # Crosshair consists of four lines - Valorant-style
        self.crosshair = {}
        
        # Create a center dot (small square in the center)
        cm = CardMaker("center_dot")
        dot_size = CROSSHAIR_SIZE * 1.5
        cm.setFrame(-dot_size, dot_size, -dot_size, dot_size)
        center_dot = self.render2d.attachNewNode(cm.generate())
        center_dot.setColor(0, 1, 0, 1)  # Green dot
        center_dot.setBin("fixed", 0)
        center_dot.setDepthTest(False)
        center_dot.setDepthWrite(False)
        self.crosshair["center"] = center_dot
        
        # Gap between center and lines
        gap = CROSSHAIR_SIZE * 2
        
        # Vertical line above center
        self.crosshair["top"] = self.create_crosshair_line(0, gap, 0, gap + CROSSHAIR_SIZE * 6)
        
        # Vertical line below center
        self.crosshair["bottom"] = self.create_crosshair_line(0, -gap, 0, -(gap + CROSSHAIR_SIZE * 6))
        
        # Horizontal line to the left
        self.crosshair["left"] = self.create_crosshair_line(-gap, 0, -(gap + CROSSHAIR_SIZE * 6), 0)
        
        # Horizontal line to the right
        self.crosshair["right"] = self.create_crosshair_line(gap, 0, gap + CROSSHAIR_SIZE * 6, 0)

    def create_crosshair_line(self, start_x, start_y, end_x, end_y):
        """Create a line for the crosshair"""
        line = self.render2d.attachNewNode("crosshair_line")
        
        cm = CardMaker("line")
        cm.setFrame(start_x, end_x, start_y, end_y)
        
        line_node = line.attachNewNode(cm.generate())
        # Bright green crosshair with full opacity for better visibility
        line_node.setColor(0, 1, 0, 1)
        # Make sure it renders on top of everything
        line_node.setBin("fixed", 0)
        line_node.setDepthTest(False)
        line_node.setDepthWrite(False)
        
        return line

    def create_ui(self):
        """Create UI elements for displaying stats"""
        self.ui_text = {}
        
        # Create accuracy text
        self.ui_text["accuracy"] = OnscreenText(
            text="Accuracy: 0%",
            pos=(-1.3, 0.9),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        # Create hits text
        self.ui_text["hits"] = OnscreenText(
            text="Hits: 0",
            pos=(-1.3, 0.8),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        # Create shots text
        self.ui_text["shots"] = OnscreenText(
            text="Shots: 0",
            pos=(-1.3, 0.7),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        # Create timer text
        self.ui_text["timer"] = OnscreenText(
            text="Time: 0.0s",
            pos=(-1.3, 0.6),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        # Instructions
        self.ui_text["instructions"] = OnscreenText(
            text="Left-click to shoot | R to reset | ESC to quit",
            pos=(0, -0.9),
            scale=0.04,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter
        )

    def spawn_targets(self, count):
        """Spawn multiple targets around the player"""
        for _ in range(count):
            self.spawn_target()

    def spawn_target(self):
        """Spawn a single target at a random position"""
        # Create a sphere for the target
        target = self.loader.loadModel("models/misc/sphere")
        target.setScale(TARGET_SIZE, TARGET_SIZE, TARGET_SIZE)
        target.setColor(*TARGET_COLORS["normal"])
        
        # Position the target at a random location within the spawn radius
        theta = random.uniform(0, 2 * math.pi)
        phi = random.uniform(0, math.pi)
        x = TARGET_SPAWN_RADIUS * math.sin(phi) * math.cos(theta)
        y = TARGET_SPAWN_RADIUS * math.sin(phi) * math.sin(theta)
        z = TARGET_SPAWN_RADIUS * math.cos(phi)
        
        target.setPos(x, y, z)
        target.reparentTo(self.render)
        
        # Set up collision for this target
        target_coll = CollisionNode(f'target{len(self.targets)}')
        # Create a collision sphere with the same radius as the target
        coll_sphere = CollisionSphere(0, 0, 0, TARGET_SIZE)
        target_coll.addSolid(coll_sphere)
        target_coll.setIntoCollideMask(BitMask32.bit(1))
        target_np = target.attachNewNode(target_coll)
        
        # Store the target in our list
        self.targets.append({"node": target, "collision": target_np, "hit": False})
        self.stats["targets_spawned"] += 1

    def shoot(self):
        """Handle shooting mechanic"""
        # Increment shot counter
        self.stats["shots"] += 1
        
        # Traverse the collision ray
        self.cTrav.traverse(self.render)
        
        # Check if we hit anything
        if self.shooterHandler.getNumEntries() > 0:
            # Sort entries by distance
            self.shooterHandler.sortEntries()
            entry = self.shooterHandler.getEntry(0)
            
            # Get the target we hit
            hit_target_name = entry.getIntoNode().getName()
            
            # Extract the target index from the name
            target_index = int(hit_target_name[6:])
            
            # Check if this target was already hit
            if not self.targets[target_index]["hit"]:
                # Mark as hit
                self.targets[target_index]["hit"] = True
                self.targets[target_index]["node"].setColor(*TARGET_COLORS["hit"])
                
                # Increment hit counter
                self.stats["hits"] += 1
                
                # Remove target after a short delay
                taskMgr.doMethodLater(0.3, self.remove_target, f"RemoveTarget{target_index}", 
                                      extraArgs=[target_index])
    
    def remove_target(self, target_index):
        """Remove a target after it's been hit"""
        if target_index < len(self.targets):
            # Remove the target model from the scene
            self.targets[target_index]["node"].removeNode()
            
            # Spawn a new target to replace it
            self.spawn_target()
            
            # Remove the target from our list
            self.targets.pop(target_index)
        
        return Task.done

    def update_stats_task(self, task):
        """Update the UI with current stats"""
        # Calculate accuracy
        accuracy = 0
        if self.stats["shots"] > 0:
            accuracy = (self.stats["hits"] / self.stats["shots"]) * 100
        
        # Calculate elapsed time
        elapsed_time = time.time() - self.stats["start_time"]
        
        # Update UI texts
        self.ui_text["accuracy"].setText(f"Accuracy: {accuracy:.1f}%")
        self.ui_text["hits"].setText(f"Hits: {self.stats['hits']}")
        self.ui_text["shots"].setText(f"Shots: {self.stats['shots']}")
        self.ui_text["timer"].setText(f"Time: {elapsed_time:.1f}s")
        
        return Task.cont

    def reset_game(self):
        """Reset the game state"""
        # Reset stats
        self.stats = {
            "hits": 0,
            "shots": 0,
            "start_time": time.time(),
            "targets_spawned": 0
        }
        
        # Remove all targets
        for target in self.targets:
            target["node"].removeNode()
        
        # Clear targets list
        self.targets.clear()
        
        # Spawn new targets
        self.spawn_targets(TARGET_COUNT)

    def quit_game(self):
        """Exit the game"""
        # Use the correct method to stop all tasks
        self.taskMgr.remove("MouseTask")
        self.taskMgr.remove("UpdateStatsTask")
        # Remove any pending target removal tasks
        for i in range(len(self.targets)):
            self.taskMgr.remove(f"RemoveTarget{i}")
        self.userExit()

# Run the game
app = ValorantAimTrainer()
app.run()
