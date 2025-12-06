from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import os
import time
import psutil
import json
import pickle
from math import atan2, degrees
from tkinter import Tk, simpledialog, filedialog
from PIL import Image

# -----------------------------
# USERNAME & SKIN SELECTION
# -----------------------------
def get_player_info():
    root = Tk()
    root.withdraw()
    
    # Get username
    username = simpledialog.askstring("Player Name", "Enter your username:", parent=root)
    if not username:
        username = "Player"
    
    # Get skin file
    skin_path = filedialog.askopenfilename(
        title="Select your Minecraft skin (64x64 PNG)",
        filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
        parent=root
    )
    
    root.destroy()
    
    return username, skin_path if skin_path else None

player_username, player_skin_path = get_player_info()

app = Ursina(title=f"Minecraft-like Prototype - {player_username}")

# -----------------------------
# SKIN PROCESSING
# -----------------------------
def load_minecraft_skin(skin_path):
    """Load and validate Minecraft skin texture"""
    if not skin_path or not os.path.exists(skin_path):
        return None
    
    try:
        img = Image.open(skin_path)
        # Minecraft skins are 64x64 (new format) or 64x32 (old format)
        if img.size not in [(64, 64), (64, 32)]:
            print(f"Warning: Skin size {img.size} is not standard Minecraft format (64x64 or 64x32)")
        
        # Save to a known location for Ursina to load
        processed_path = "player_skin.png"
        img.save(processed_path)
        return processed_path
    except Exception as e:
        print(f"Error loading skin: {e}")
        return None

processed_skin = load_minecraft_skin(player_skin_path)

# -----------------------------
# SKYBOX
# -----------------------------
if os.path.exists("skybox.png"):
    sky = Entity(
        model="sphere",
        texture=load_texture("skybox.png"),
        scale=500,
        double_sided=True
    )
else:
    Sky()

# -----------------------------
# PLAYER
# -----------------------------
player = FirstPersonController(speed=5, mouse_sensitivity=Vec2(40,40))
camera.fov = 115

# Now set the actual starting position
player.position = Vec3(0, 100, 0)

# Player model/skin (visible in 3rd person)
# Create a parent entity for the entire player model
player_model = Entity(
    position=player.position,
    visible=False
)

# -----------------------------
# HELD ITEM MODEL (3D Preview)
# -----------------------------
held_item_model = Entity(
    parent=player.camera_pivot,   # follows camera in first person
    model='cube',
    texture='white_cube',
    scale=0.25,
    position=Vec3(0.4, -0.4, 0.7),   # lower-right corner
    rotation=Vec3(30, -40, 0),
    visible=False
)

# Load skin texture or use default colors
if processed_skin and os.path.exists(processed_skin):
    skin_texture = load_texture(processed_skin)
else:
    skin_texture = None

# Torso
player_torso = Entity(
    model='cube',
    texture=skin_texture if skin_texture else 'white_cube',
    color=color.white if skin_texture else color.rgb(100, 150, 200),
    scale=(0.5, 0.75, 0.25),
    parent=player_model,
    position=(0, 0, 0)
)

# Head
player_head = Entity(
    model='cube',
    texture=skin_texture if skin_texture else 'white_cube',
    color=color.white if skin_texture else color.rgb(255, 220, 177),
    scale=(0.5, 0.5, 0.5),
    parent=player_model,
    position=(0, 0.625, 0)
)

# Right Leg
player_right_leg = Entity(
    model='cube',
    texture=skin_texture if skin_texture else 'white_cube',
    color=color.white if skin_texture else color.rgb(50, 50, 150),
    scale=(0.25, 0.75, 0.25),
    parent=player_model,
    position=(0.125, -0.75, 0)
)

# Left Leg
player_left_leg = Entity(
    model='cube',
    texture=skin_texture if skin_texture else 'white_cube',
    color=color.white if skin_texture else color.rgb(50, 50, 150),
    scale=(0.25, 0.75, 0.25),
    parent=player_model,
    position=(-0.125, -0.75, 0)
)

# Right Arm
player_right_arm = Entity(
    model='cube',
    texture=skin_texture if skin_texture else 'white_cube',
    color=color.white if skin_texture else color.rgb(255, 220, 177),
    scale=(0.25, 0.75, 0.25),
    parent=player_model,
    position=(0.375, 0.125, 0)
)

# Left Arm
player_left_arm = Entity(
    model='cube',
    texture=skin_texture if skin_texture else 'white_cube',
    color=color.white if skin_texture else color.rgb(255, 220, 177),
    scale=(0.25, 0.75, 0.25),
    parent=player_model,
    position=(-0.375, 0.125, 0)
)

# Camera perspective system
camera_mode = 0  # 0 = first person, 1 = third person back, 2 = third person front
camera_distance = 5


# -----------------------------
# BLOCK CLASS
# -----------------------------
class WorldBlock(Entity):
    def __init__(self, position, block_type="stone-block"):
        # Get texture for this block type using Ursina's load_texture
        try:
            texture_to_use = load_texture(block_type)
            block_color = color.white
        except:
            # Fallback if texture doesn't exist
            texture_to_use = 'white_cube'
            block_color = color.gray
        
        super().__init__(
            model='cube',
            texture=texture_to_use,
            color=block_color,
            collider='box',
            position=position
        )
        self.block_type = block_type

# Keep track of all blocks for saving
world_blocks = []

# -----------------------------
# BLOCK OUTLINE SYSTEM
# -----------------------------
block_outline = Entity(
    model='wireframe_cube',
    color=color.black,
    scale=1.01,
    visible=False,
    eternal=True
)

def update_block_outline():
    """Update the outline to show which block face is being looked at"""
    # Use mouse raycast from center of screen (where crosshair is)
    hit = raycast(
        origin=camera.world_position,
        direction=camera.forward,
        distance=5,
        ignore=[player, block_outline, player_model, player_torso, player_head, 
                player_right_leg, player_left_leg, player_right_arm, player_left_arm]
    )
    
    if hit.hit and hasattr(hit.entity, '__class__') and isinstance(hit.entity, WorldBlock):
        try:
            block_outline.visible = True
            block_outline.position = hit.entity.position
        except:
            block_outline.visible = False
    else:
        block_outline.visible = False

# -----------------------------
# INITIAL PLATFORM (6x6)
# -----------------------------
for x in range(-3,3):
    for z in range(-3,3):
        block = WorldBlock(position=(x,0,z), block_type="block")
        world_blocks.append(block)

# -----------------------------
# SAVE/LOAD SYSTEM
# -----------------------------
WORLDS_DIR = "worlds"

def ensure_worlds_directory():
    """Create worlds directory if it doesn't exist"""
    if not os.path.exists(WORLDS_DIR):
        os.makedirs(WORLDS_DIR)

def save_world(world_name=None):
    """Save the current world to a file"""
    ensure_worlds_directory()
    
    if not world_name:
        root = Tk()
        root.withdraw()
        world_name = simpledialog.askstring("Save World", "Enter world name:", parent=root)
        root.destroy()
        
        if not world_name:
            add_chat_message("Save cancelled")
            return
    
    # Clean filename
    world_name = "".join(c for c in world_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not world_name:
        add_chat_message("Invalid world name")
        return
    
    filepath = os.path.join(WORLDS_DIR, f"{world_name}.world")
    
    try:
        # Collect all block data
        blocks_data = []
        for entity in scene.entities:
            if isinstance(entity, WorldBlock):
                blocks_data.append({
                    'position': (entity.x, entity.y, entity.z),
                    'block_type': getattr(entity, 'block_type', 'stone-block')
                })
        
        # Save player data
        player_data = {
            'position': (player.x, player.y, player.z),
            'rotation': (player.rotation_x, player.rotation_y, player.rotation_z),
            'fly_mode': fly_mode,
            'speed': player.speed,
            'gamemode': gamemode
        }
        
        # Save inventory (survival mode inventory)
        inventory_data = inventory.copy()
        
        # Combine all data
        world_data = {
            'blocks': blocks_data,
            'player': player_data,
            'inventory': inventory_data,
            'version': '1.0'
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(world_data, f, indent=2)
        
        add_chat_message(f"World saved: {world_name}")
        print(f"Saved {len(blocks_data)} blocks to {filepath}")
        
    except Exception as e:
        add_chat_message(f"Error saving world: {str(e)}")
        print(f"Save error: {e}")

def load_world(world_name=None):
    """Load a world from a file"""
    global world_blocks, fly_mode, gamemode
    
    ensure_worlds_directory()
    
    if not world_name:
        root = Tk()
        root.withdraw()
        
        # List available worlds
        world_files = [f[:-6] for f in os.listdir(WORLDS_DIR) if f.endswith('.world')]
        
        if not world_files:
            root.destroy()
            add_chat_message("No saved worlds found")
            return
        
        world_name = simpledialog.askstring(
            "Load World", 
            f"Enter world name to load:\n\nAvailable worlds:\n" + "\n".join(world_files),
            parent=root
        )
        root.destroy()
        
        if not world_name:
            add_chat_message("Load cancelled")
            return
    
    filepath = os.path.join(WORLDS_DIR, f"{world_name}.world")
    
    if not os.path.exists(filepath):
        add_chat_message(f"World not found: {world_name}")
        return
    
    try:
        # Load world data
        with open(filepath, 'r') as f:
            world_data = json.load(f)
        
        # Clear existing blocks
        for entity in scene.entities.copy():
            if isinstance(entity, WorldBlock):
                destroy(entity)
        world_blocks.clear()
        
        # Load blocks
        blocks_data = world_data.get('blocks', [])
        for block_info in blocks_data:
            pos = block_info['position']
            block_type = block_info.get('block_type', 'stone-block')
            block = WorldBlock(position=Vec3(*pos), block_type=block_type)
            world_blocks.append(block)
        
        # Load player data
        player_data = world_data.get('player', {})
        if 'position' in player_data:
            player.position = Vec3(*player_data['position'])
        if 'rotation' in player_data:
            player.rotation = Vec3(*player_data['rotation'])
        if 'fly_mode' in player_data:
            fly_mode = player_data['fly_mode']
            player.gravity = 0 if fly_mode else 1
        if 'speed' in player_data:
            player.speed = player_data['speed']
        if 'gamemode' in player_data:
            gamemode = player_data['gamemode']
            if gamemode == 1:
                populate_creative_inventory()
        
        # Load inventory
        inventory_data = world_data.get('inventory', [])
        if inventory_data:
            for i, slot_data in enumerate(inventory_data):
                if i < len(inventory):
                    inventory[i] = slot_data
            update_hotbar_selector()
        
        # Refresh UI for gamemode
        create_hotbar()
        update_hotbar_selector()
        
        add_chat_message(f"World loaded: {world_name} ({len(blocks_data)} blocks)")
        print(f"Loaded {len(blocks_data)} blocks from {filepath}")
        
    except Exception as e:
        add_chat_message(f"Error loading world: {str(e)}")
        print(f"Load error: {e}")

def list_worlds():
    """List all available worlds"""
    ensure_worlds_directory()
    world_files = [f[:-6] for f in os.listdir(WORLDS_DIR) if f.endswith('.world')]
    
    if not world_files:
        add_chat_message("No saved worlds found")
    else:
        add_chat_message(f"Available worlds ({len(world_files)}):")
        for world in world_files:
            add_chat_message(f"  - {world}")

# -----------------------------
# GAMEMODE SYSTEM
# -----------------------------
gamemode = 0  # 0 = survival, 1 = creative
creative_inventory_scroll = 0  # For scrolling through all available items
all_available_items = []  # Will be populated with all textures

def get_all_available_items():
    """Scan for all available item textures"""
    texture_folders = [".", "assets", "textures"]
    items = set()
    
    for folder in texture_folders:
        if os.path.isdir(folder):
            item_files = [
                f[:-4] for f in os.listdir(folder)
                if f.endswith(".png") and f not in ["skybox.png", "player_skin.png"]
            ]
            items.update(item_files)
    
    return sorted(items)

all_available_items = get_all_available_items()

# -----------------------------
# INVENTORY / HOTBAR
# -----------------------------
inventory_open = False
selected_slot = 0

# 36 slots total: slots 27-35 are the hotbar (bottom row)
inventory = [{"item": "air", "count": 0} for _ in range(36)]
# Give some blocks in the first hotbar slot - survival mode starting items
inventory[27] = {"item": "block", "count": 64}

# Creative mode inventory (dynamically populated)
creative_inventory = [{"item": "air", "count": 0} for _ in range(36)]

hotbar_parent = Entity(parent=camera.ui)
hotbar_slots = []
selector = None

def create_hotbar():
    global hotbar_slots, selector
    for s in hotbar_slots:
        for e in s:
            if e: destroy(e)
    hotbar_slots.clear()
    
    # Get current inventory based on gamemode
    current_inv = creative_inventory if gamemode == 1 else inventory
    
    for i in range(9):
        x = (i-4)*0.11
        hotbar_index = 27 + i  # Bottom row of inventory
        
        bg = Entity(parent=hotbar_parent, model='quad', color=color.rgba(0,0,0,0), 
                    scale=(0.09,0.09), position=(x,-0.45))
        
        # Position text in bottom-right corner, with proper z-layering
        count_text = ""
        if gamemode == 0:  # Survival - show count
            count_text = str(current_inv[hotbar_index]["count"]) if current_inv[hotbar_index]["item"]!="air" else ""
        # Creative mode doesn't show count
        
        text = Text(parent=hotbar_parent, 
                    text=count_text,
                    position=(x+0.03,-0.48), scale=0.9, color=color.white, z=-0.2)
        
        item = current_inv[hotbar_index]["item"]
        if item != "air":
            # Try to load texture, fall back to white_cube if not found
            try:
                tex = load_texture(item)
                icon = Entity(parent=hotbar_parent, model='quad', 
                             texture=tex,
                             scale=0.08, position=(x,-0.45), z=-0.1)
            except:
                # Fallback to colored cube if texture doesn't exist
                icon = Entity(parent=hotbar_parent, model='quad', 
                             texture='white_cube',
                             color=color.gray,
                             scale=0.08, position=(x,-0.45), z=-0.1)
        else:
            icon = None
        
        hotbar_slots.append((bg,text,icon))
    
    selector = Entity(parent=hotbar_parent, model='wireframe_quad', color=color.azure, 
                     scale=(0.11,0.11), position=(-4*0.11,-0.45), z=-0.15)

create_hotbar()

def update_hotbar_selector():
    global selector
    selector.x = (selected_slot-4)*0.11
    
    # Get current inventory based on gamemode
    current_inv = creative_inventory if gamemode == 1 else inventory
    
    # Update hotbar display from bottom row (slots 27-35)
    for i, (bg, text, icon) in enumerate(hotbar_slots):
        hotbar_index = 27 + i
        x = (i-4)*0.11
        
        # Update count text - position in bottom-right corner with proper z-layering
        count = current_inv[hotbar_index]["count"]
        if gamemode == 0:  # Survival - show count
            text.text = str(count) if current_inv[hotbar_index]["item"]!="air" and count > 0 else ""
        else:  # Creative - no count
            text.text = ""
        text.position = (x+0.03, -0.48)
        text.z = -0.2  # Ensure text is on top
        
        item = current_inv[hotbar_index]["item"]
        
        if icon:
            if item=="air" or (gamemode == 0 and count == 0):
                destroy(icon)
                hotbar_slots[i] = (bg, text, None)
            else:
                try:
                    tex = load_texture(item)
                    icon.texture = tex
                    icon.color = color.white
                except:
                    icon.texture = 'white_cube'
                    icon.color = color.gray
                icon.position = (x, -0.45)
                icon.z = -0.1
        elif item!="air" and (gamemode == 1 or count > 0):
            try:
                tex = load_texture(item)
                new_icon = Entity(parent=hotbar_parent, model='quad', 
                                texture=tex,
                                scale=0.08, position=(x,-0.45), z=-0.1)
            except:
                new_icon = Entity(parent=hotbar_parent, model='quad', 
                                texture='white_cube',
                                color=color.gray,
                                scale=0.08, position=(x,-0.45), z=-0.1)
            hotbar_slots[i] = (bg, text, new_icon)
    update_held_item_model()

# -----------------------------
# INVENTORY MENU UI
# -----------------------------
inventory_parent = Entity(parent=camera.ui, enabled=False)
inventory_slots_ui = []

rows = 4
cols = 9
slot_size = 0.09
spacing = 0.01
start_x = -((cols-1)/2)*(slot_size + spacing)
start_y = 0.25

for row in range(rows):
    for col in range(cols):
        x = start_x + col*(slot_size + spacing)
        y = start_y - row*(slot_size + spacing)
        
        bg = Entity(parent=inventory_parent, model='quad', color=color.rgba(0,0,0,0), 
                   scale=(slot_size,slot_size), position=(x,y))
        border = Entity(parent=inventory_parent, model='wireframe_quad', color=color.white, 
                       scale=(slot_size+0.005,slot_size+0.005), position=(x,y), z=-0.1)
        
        slot_index = row*cols + col
        # Position text in bottom-right corner with proper z-layering
        text = Text(parent=inventory_parent, 
                   text=str(inventory[slot_index]["count"]) if inventory[slot_index]["item"]!="air" else "", 
                   position=(x+0.03, y-0.03), scale=0.7, color=color.white, z=-0.3)
        
        # Add item icons
        item = inventory[slot_index]["item"]
        if item != "air" and inventory[slot_index]["count"] > 0:
            try:
                tex = load_texture(item)
                icon = Entity(parent=inventory_parent, model='quad',
                             texture=tex,
                             scale=0.08, position=(x,y), z=-0.2)
            except:
                icon = Entity(parent=inventory_parent, model='quad',
                             texture='white_cube',
                             color=color.gray,
                             scale=0.08, position=(x,y), z=-0.2)
        else:
            icon = None
        
        inventory_slots_ui.append((bg, border, text, icon))

def toggle_inventory():
    global inventory_open
    inventory_open = not inventory_open
    inventory_parent.enabled = inventory_open
    mouse.locked = not inventory_open
    if inventory_open:
        update_inventory_ui()

def update_inventory_ui():
    update_hotbar_selector()
    
    # Get current inventory based on gamemode
    current_inv = creative_inventory if gamemode == 1 else inventory
    
    for i, (bg, border, text, icon) in enumerate(inventory_slots_ui):
        item = current_inv[i]["item"]
        count = current_inv[i]["count"]
        
        row = i // 9
        col = i % 9
        x = start_x + col*(slot_size + spacing)
        y = start_y - row*(slot_size + spacing)
        
        # Update text - position in bottom-right corner with proper z-layering
        if gamemode == 0:  # Survival - show count
            text.text = str(count) if item != "air" and count > 0 else ""
        else:  # Creative - no count
            text.text = ""
        text.position = (x+0.03, y-0.03)
        text.z = -0.3  # Ensure text is on top
        
        # Update icon
        if icon:
            if item == "air" or (gamemode == 0 and count == 0):
                destroy(icon)
                inventory_slots_ui[i] = (bg, border, text, None)
            else:
                try:
                    tex = load_texture(item)
                    icon.texture = tex
                    icon.color = color.white
                except:
                    icon.texture = 'white_cube'
                    icon.color = color.gray
                icon.position = (x, y)
                icon.z = -0.2
        elif item != "air" and (gamemode == 1 or count > 0):
            try:
                tex = load_texture(item)
                new_icon = Entity(parent=inventory_parent, model='quad',
                                texture=tex,
                                scale=0.08, position=(x,y), z=-0.2)
            except:
                new_icon = Entity(parent=inventory_parent, model='quad',
                                texture='white_cube',
                                color=color.gray,
                                scale=0.08, position=(x,y), z=-0.2)
            inventory_slots_ui[i] = (bg, border, text, new_icon)

# -----------------------------
# INVENTORY CLICK / DRAG HANDLING
# -----------------------------
selected_inventory_slot = None
last_mouse_state = False  # Track previous mouse button state

def inventory_click(slot_index):
    global selected_inventory_slot

    if slot_index < 0 or slot_index >= len(inventory):
        return

    # Get current inventory based on gamemode
    current_inv = creative_inventory if gamemode == 1 else inventory

    # If no slot picked up, pick up this one
    if selected_inventory_slot is None:
        if current_inv[slot_index]["item"] != "air":
            selected_inventory_slot = slot_index
            # highlight the slot
            bg, border, text, icon = inventory_slots_ui[slot_index]
            border.color = color.yellow
    else:
        # Swap items (only in survival mode)
        if gamemode == 0:
            if slot_index != selected_inventory_slot:
                current_inv[slot_index], current_inv[selected_inventory_slot] = current_inv[selected_inventory_slot], current_inv[slot_index]
        # remove highlight and clear selection
        bg, border, text, icon = inventory_slots_ui[selected_inventory_slot]
        border.color = color.white
        selected_inventory_slot = None

        update_inventory_ui()

# -----------------------------
# INVENTORY UI INPUT
# -----------------------------
def inventory_input():
    global last_mouse_state
    
    if not inventory_open:
        return

    # Detect mouse button press (transition from not pressed to pressed)
    current_mouse_state = held_keys['left mouse']
    
    if current_mouse_state and not last_mouse_state:
        # Mouse was just pressed, process the click
        for i, (bg, border, text, icon) in enumerate(inventory_slots_ui):
            x_min = bg.x - bg.scale_x/2
            x_max = bg.x + bg.scale_x/2
            y_min = bg.y - bg.scale_y/2
            y_max = bg.y + bg.scale_y/2
            if x_min <= mouse.x <= x_max and y_min <= mouse.y <= y_max:
                inventory_click(i)
                break
    
    last_mouse_state = current_mouse_state

# -----------------------------
# UPDATE HELD ITEM VISUAL
# -----------------------------
held_text = Text(parent=camera.ui, text="", scale=0.7, color=color.white, z=-0.3, enabled=False)

def update_held_item_ui():
    if selected_inventory_slot is not None:
        current_inv = creative_inventory if gamemode == 1 else inventory
        item = current_inv[selected_inventory_slot]["item"]
        count = current_inv[selected_inventory_slot]["count"]
        held_text.enabled = True
        if gamemode == 0:  # Survival - show count
            held_text.text = str(count) if count>1 else ""
        else:  # Creative - no count
            held_text.text = ""
        held_text.position = Vec2(mouse.x + 0.02, mouse.y - 0.02)
    else:
        held_text.enabled = False

# -----------------------------
# HELPERS
# -----------------------------
def get_look_ray():
    return raycast(
        origin=camera.world_position,
        direction=camera.forward,
        distance=5,
        ignore=[player, block_outline, player_model, player_torso, player_head, 
                player_right_leg, player_left_leg, player_right_arm, player_left_arm],
        traverse_target=scene
    )

# -----------------------------
# CREATIVE MODE INVENTORY POPULATION
# -----------------------------
def populate_creative_inventory():
    """Populate creative inventory with items based on scroll position"""
    global creative_inventory, all_available_items, creative_inventory_scroll
    
    if not all_available_items:
        return
    
    # Clear creative inventory
    for slot in creative_inventory:
        slot["item"] = "air"
        slot["count"] = 0
    
    # Calculate which items to show (9 items per page in hotbar)
    items_per_page = 9
    start_index = creative_inventory_scroll * items_per_page
    
    # Populate hotbar (slots 27-35) with items from current page
    for i in range(items_per_page):
        item_index = start_index + i
        if item_index < len(all_available_items):
            creative_inventory[27 + i] = {
                "item": all_available_items[item_index],
                "count": 999  # Infinite in creative
            }

# -----------------------------
# CAMERA PERSPECTIVE SYSTEM
# -----------------------------
def update_camera_perspective():
    global camera_mode
    
    if camera_mode == 0:  # First person
        camera.parent = player.camera_pivot
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)
        player_model.visible = False
        
    elif camera_mode == 1:  # Third person back
        camera.parent = player
        # Position camera behind and above player
        offset = Vec3(0, 2, -camera_distance)
        camera.position = offset
        camera.rotation_x = 10
        camera.rotation_y = 0
        player_model.visible = True
        
    elif camera_mode == 2:  # Third person front
        camera.parent = player
        # Position camera in front and above player
        offset = Vec3(0, 2, camera_distance)
        camera.position = offset
        camera.rotation_x = 10
        camera.rotation_y = 180
        player_model.visible = True

def cycle_camera_mode():
    global camera_mode
    camera_mode = (camera_mode + 1) % 3
    update_camera_perspective()

# -----------------------------
# CHAT SYSTEM
# -----------------------------
chat_parent = Entity(parent=camera.ui)
chat_messages = []
chat_timeout = 15
chat_y_offset = -0.3
chat_open = False
chat_buffer = ""

def add_chat_message(text):
    msg = Text(text, parent=chat_parent, origin=(-.5,-.5), position=(-0.85, chat_y_offset + len(chat_messages)*0.035), scale=0.9, color=color.white)
    chat_messages.append((msg, time.time()))

fly_mode = False

def process_chat_command(text):
    global fly_mode, player, gamemode, creative_inventory, all_available_items, creative_inventory_scroll
    parts = text.split()
    if text.startswith("/fly"):
        fly_mode = not fly_mode
        player.gravity = 0 if fly_mode else 1
        add_chat_message(f"Fly mode {'enabled' if fly_mode else 'disabled'}")
    elif parts[0]=="/gamemode" and len(parts)==2:
        try:
            mode = int(parts[1])
            if mode not in [0, 1]:
                add_chat_message("Gamemode must be 0 (survival) or 1 (creative)")
                return
            
            gamemode = mode
            
            if gamemode == 1:  # Creative mode
                add_chat_message("Switched to Creative mode")
                # Populate creative inventory with all available items
                all_available_items = get_all_available_items()
                populate_creative_inventory()
            else:  # Survival mode
                add_chat_message("Switched to Survival mode")
                # Disable fly mode in survival
                if fly_mode:
                    fly_mode = False
                    player.gravity = 1
            
            # Refresh hotbar
            create_hotbar()
            update_hotbar_selector()
            
        except:
            add_chat_message("Usage: /gamemode <0|1>")
    elif parts[0]=="/speed" and len(parts)==2:
        try:
            val = float(parts[1])
            player.speed = val
            add_chat_message(f"Speed set to {val}")
        except:
            add_chat_message("Invalid speed")
    elif parts[0]=="/tp" and len(parts)==4:
        try:
            x=float(parts[1])
            y=float(parts[2])
            z=float(parts[3])
            player.position = Vec3(x,y,z)
            add_chat_message(f"Teleported to {x},{y},{z}")
        except:
            add_chat_message("Invalid coordinates")
    elif text.startswith("/save"):
        parts = text.split(maxsplit=1)
        world_name = parts[1] if len(parts) > 1 else None
        save_world(world_name)
    elif text.startswith("/load"):
        parts = text.split(maxsplit=1)
        world_name = parts[1] if len(parts) > 1 else None
        load_world(world_name)
    elif text.startswith("/worlds"):
        list_worlds()
    elif parts[0] == "/give" and len(parts) == 3:
        item = parts[1]  # Keep original case/format

        # Validate number
        try:
            qty = int(parts[2])
        except:
            add_chat_message("Invalid quantity.")
            return

        if qty <= 0:
            add_chat_message("Quantity must be > 0.")
            return

        # Try to verify the texture exists by attempting to load it
        texture_exists = False
        try:
            test_tex = load_texture(item)
            texture_exists = True
        except:
            add_chat_message(f"Warning: '{item}' texture not found. Item will appear gray.")
            add_chat_message("Use /itemlist to see available items.")

        # Find first slot with same item OR empty slot
        placed = False

        # 1) Try stacking first - check ALL slots including hotbar
        for slot in inventory:
            if slot["item"] == item:
                slot["count"] += qty
                placed = True
                break

        # 2) If no stacking slot found, use first empty slot
        if not placed:
            for slot in inventory:
                if slot["item"] == "air" or slot["count"] == 0:
                    slot["item"] = item
                    slot["count"] = qty
                    placed = True
                    break

        # 3) If no slot available
        if not placed:
            add_chat_message("Inventory full.")
            return

        if texture_exists:
            add_chat_message(f"Gave {qty}x {item}.")
        else:
            add_chat_message(f"Gave {qty}x {item} (no texture).")
        update_inventory_ui()
        update_hotbar_selector()
    elif parts[0] == "/itemlist":
        # Check both root directory and assets folder for textures
        texture_folders = [".", "assets", "textures"]
        all_items = set()
        
        for folder in texture_folders:
            if os.path.isdir(folder):
                item_files = [
                    f[:-4] for f in os.listdir(folder)
                    if f.endswith(".png") and f not in ["skybox.png", "player_skin.png"]
                ]
                all_items.update(item_files)
        
        if not all_items:
            add_chat_message("No item textures found.")
            add_chat_message("Place .png files in the root directory or 'assets' folder.")
        else:
            items = sorted(all_items)
            add_chat_message(f"Available items ({len(items)}):")
            for item in items:
                add_chat_message(f" - {item}")
            add_chat_message("")
            add_chat_message("Usage: /give <item-name> <quantity>")

chat_input = Text("", parent=chat_parent, origin=(-.5,-.5), position=(-0.85, chat_y_offset-0.06), scale=0.9, color=color.gray)
chat_input.enabled=False

def update_chat():
    now = time.time()
    for msg,t in chat_messages:
        if now - t > chat_timeout:
            msg.enabled = False
    chat_messages[:] = [(m,t) for m,t in chat_messages if m.enabled]
    for i,(msg,_) in enumerate(chat_messages):
        msg.position = (-0.85, chat_y_offset + i*0.035)
    if chat_open:
        chat_input.text = "> " + chat_buffer

# -----------------------------
# F3 DEBUG
# -----------------------------
coord_text = Text("", parent=camera.ui, origin=(-.5,.5), position=(-0.87,0.47), scale=1, color=color.yellow)
debug_enabled = False
debug_text = Text("", parent=camera.ui, origin=(-.5,.5), position=(-0.87,0.43), scale=0.8, color=color.white, enabled=False)

# Display username in top-right
username_text = Text(f"{player_username}", parent=camera.ui, origin=(.5,.5), position=(0.81,0.47), scale=1, color=color.cyan)

def get_facing_direction():
    forward = camera.forward
    angle = atan2(forward.x, forward.z)
    deg = (degrees(angle)+360)%360
    if 315<=deg or deg<45: return "South"
    if 45<=deg<135: return "West"
    if 135<=deg<225: return "North"
    if 225<=deg<315: return "East"

def update_coordinates():
    x = round(player.x,2)
    y = round(player.y,2)
    z = round(player.z,2)
    coord_text.text = f"XYZ: {x},{y},{z}"

def update_player_model():
    # Update player model position to follow player
    player_model.position = player.position + Vec3(0, 1.25, 0)
    player_model.rotation_y = player.rotation_y
    
    player_head.rotation_x = camera.rotation_x
    player_head.rotation_y = camera.rotation_y
    player_torso.rotation_y = player.rotation_y
    player_right_arm.rotation_y = player.rotation_y
    player_left_arm.rotation_y = player.rotation_y

    player_head.position = Vec3(0, 0.60, 0)
    player_torso.position = Vec3(0, 0, 0)
    player_right_arm.position = Vec3(0.375, 0.125, 0)
    player_left_arm.position = Vec3(-0.375, 0.125, 0)
    player_right_leg.position = Vec3(0.125, -0.75, 0)
    player_left_leg.position = Vec3(-0.125, -0.75, 0)


def update_debug_info():
    if debug_enabled:
        debug_text.enabled = True
        
        fps = int(1/time.dt) if time.dt > 0 else 0
        direction = get_facing_direction()
        forward = camera.forward
        yaw = round((degrees(atan2(forward.x, forward.z)) + 360) % 360, 1)
        pitch = round(degrees(atan2(-forward.y, (forward.x**2 + forward.z**2)**0.5)), 1)
        
        hit = get_look_ray()
        block_info = ""
        if hit.hit and isinstance(hit.entity, WorldBlock):
            bx, by, bz = int(hit.entity.x), int(hit.entity.y), int(hit.entity.z)
            block_info = f"Looking at: {bx}, {by}, {bz}"
        else:
            block_info = "Looking at: none"
        
        process = psutil.Process(os.getpid())
        mem_mb = round(process.memory_info().rss / 1024 / 1024, 1)
        
        gamemode_name = "Creative" if gamemode == 1 else "Survival"
        
        debug_info = f"""FPS: {fps}
Facing: {direction} (Yaw: {yaw}°, Pitch: {pitch}°)
{block_info}
Memory: {mem_mb} MB
Gamemode: {gamemode_name}
Fly Mode: {'ON' if fly_mode else 'OFF'}
Speed: {player.speed}
Username: {player_username}"""
        
        if gamemode == 1 and all_available_items:
            max_scroll = (len(all_available_items) - 1) // 9
            debug_info += f"\nCreative Page: {creative_inventory_scroll + 1}/{max_scroll + 1}"
        
        debug_text.text = debug_info
    else:
        debug_text.enabled = False

# -----------------------------
# INPUT
# -----------------------------
last_space_press_time = 0
space_double_tap_window = 0.3  # seconds

def input(key):
    global chat_open, chat_buffer, selected_slot, fly_mode, creative_inventory_scroll, last_space_press_time

    if chat_open:
        if key=="enter":
            if chat_buffer.strip()!="":
                if chat_buffer.startswith("/"):
                    process_chat_command(chat_buffer)
                else:
                    add_chat_message(f"<{player_username}> {chat_buffer}")
            chat_open=False
            chat_input.enabled=False
            mouse.locked=True
        elif key=="escape":
            chat_open=False
            chat_input.enabled=False
            mouse.locked=True
        elif key=="backspace":
            chat_buffer=chat_buffer[:-1]
        elif key=="space":
            chat_buffer+=" "
        elif len(key)==1:
            chat_buffer+=key
        return

    if key in "123456789":
        selected_slot=int(key)-1
        update_hotbar_selector()
    if key=='scroll up':
        if gamemode == 1 and not inventory_open:  # Creative mode - scroll through items
            creative_inventory_scroll = max(0, creative_inventory_scroll - 1)
            populate_creative_inventory()
            create_hotbar()
            update_hotbar_selector()
        else:
            selected_slot=(selected_slot-1)%9
            update_hotbar_selector()
    if key=='scroll down':
        if gamemode == 1 and not inventory_open:  # Creative mode - scroll through items
            max_scroll = (len(all_available_items) - 1) // 9 if all_available_items else 0
            creative_inventory_scroll = min(max_scroll, creative_inventory_scroll + 1)
            populate_creative_inventory()
            create_hotbar()
            update_hotbar_selector()
        else:
            selected_slot=(selected_slot+1)%9
            update_hotbar_selector()

    # Double-tap space for flight in creative mode
    if key == "space" and gamemode == 1 and not inventory_open and not chat_open:
        current_time = time.time()
        if current_time - last_space_press_time < space_double_tap_window:
            # Double tap detected
            fly_mode = not fly_mode
            player.gravity = 0 if fly_mode else 1
            add_chat_message(f"Flight {'enabled' if fly_mode else 'disabled'}")
            last_space_press_time = 0  # Reset to prevent triple tap
        else:
            last_space_press_time = current_time

    if key=="e":
        toggle_inventory()
    if key=="t":
        chat_open=True
        chat_buffer=""
        chat_input.enabled=True
        mouse.locked=False
    if key=="f3":
        global debug_enabled
        debug_enabled = not debug_enabled
    if key=="o":
        cycle_camera_mode()

    # Block interaction disabled when inventory or chat is open
    if inventory_open or chat_open:
        return

    # -----------------------------
    # Grid-based block placement - FIXED to use item type
    # -----------------------------
    if key=="right mouse down":
        # Check hotbar slot (27 + selected_slot)
        hotbar_index = 27 + selected_slot
        current_inv = creative_inventory if gamemode == 1 else inventory
        slot = current_inv[hotbar_index]
        
        if slot["item"]!="air" and (gamemode == 1 or slot["count"]>0):
            hit = get_look_ray()
            # Only place on the block you're actually looking at
            if hit.hit and isinstance(hit.entity, WorldBlock):
                # Place block on the face that was hit
                pos = hit.entity.position + hit.normal
                pos = Vec3(round(pos.x), round(pos.y), round(pos.z))

                # Check if position is not occupied
                occupied = False
                for e in scene.entities:
                    if isinstance(e, WorldBlock) and e.position == pos:
                        occupied = True
                        break
                
                if not occupied:
                    # Prevent placing inside player
                    if (pos - player.position).length() > 1:
                        # Use the item type from inventory
                        block = WorldBlock(pos, block_type=slot["item"])
                        world_blocks.append(block)
                        if gamemode == 0:  # Only consume in survival
                            slot["count"]-=1
                        update_hotbar_selector()

    # Break blocks - FIXED to return actual block type
    if key=="left mouse down":
        hit = get_look_ray()
        # Only break the exact block you're looking at
        if hit.hit and isinstance(hit.entity, WorldBlock):
            block_to_remove = hit.entity
            broken_block_type = block_to_remove.block_type
            
            if block_to_remove in world_blocks:
                world_blocks.remove(block_to_remove)
            destroy(block_to_remove)
            
            # Only add to inventory in survival mode
            if gamemode == 0:
                # Add to first available slot with same block type or first empty slot
                added = False
                for s in inventory:
                    if s["item"] == broken_block_type:
                        s["count"]+=1
                        added = True
                        break
                if not added:
                    for s in inventory:
                        if s["item"]=="air":
                            s["item"] = broken_block_type
                            s["count"]=1
                            break
            update_hotbar_selector()

def update_held_item_model():
    """Updates the 3D model based on the selected hotbar item."""
    hotbar_index = 27 + selected_slot
    current_inv = creative_inventory if gamemode == 1 else inventory
    item = current_inv[hotbar_index]["item"]

    # No item → hide model
    if item == "air" or (gamemode == 0 and current_inv[hotbar_index]["count"] == 0):
        held_item_model.visible = False
        return

    # Try to apply block texture
    try:
        tex = load_texture(item)
        held_item_model.texture = tex
        held_item_model.color = color.white
    except:
        held_item_model.texture = "white_cube"
        held_item_model.color = color.gray

    held_item_model.visible = True


# -----------------------------
# UPDATE LOOP
# -----------------------------
def update():
    if player.y<-30:
        player.position = Vec3(0,3,0)
    update_chat()
    update_coordinates()
    update_debug_info()
    update_held_item_ui()
    update_held_item_model()
    update_player_model()
    update_block_outline()  # Update block outline
    
    if fly_mode:
        move_dir = Vec3(
            held_keys["d"]-held_keys["a"],
            0,
            held_keys["w"]-held_keys["s"]
        )
        if move_dir.length()>0:
            move_dir = move_dir.normalized()*player.speed*time.dt*3
        forward = camera.forward
        forward.y=0
        right = camera.right
        move_vec = forward*move_dir.z + right*move_dir.x
        if held_keys["space"]:
            move_vec.y+=player.speed*time.dt*5
        if held_keys["shift"]:
            move_vec.y-=player.speed*time.dt*7
        player.position+=move_vec

    if inventory_open:
        inventory_input()

app.run()
