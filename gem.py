import pygame
import random
import sys

# --- Constants & Config ---
COLS, ROWS = 8, 8
TILE_SIZE = 60
GRID_WIDTH = COLS * TILE_SIZE
GRID_HEIGHT = ROWS * TILE_SIZE
UI_HEIGHT = 150
WIDTH, HEIGHT = GRID_WIDTH, GRID_HEIGHT + UI_HEIGHT
FPS = 60

# Colors
BG_COLOR     = (15, 15, 15)
GRID_COLOR   = (40, 40, 40)
PLAYER_COLOR = (79, 172, 254)
BUG_COLOR    = (241, 196, 15)
PELLET_COLOR = (46, 204, 113)  # Bright Green for currency
SHOOT_COLOR  = (255, 94, 98)
END_COLOR    = (155, 89, 182)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bug Hunter: Pellet Economy")
clock = pygame.time.Clock()
font = pygame.font.SysFont("courier", 16, bold=True)
big_font = pygame.font.SysFont("courier", 20, bold=True)

# --- Game State ---
player = [3, 3]
bugs = []
pellets = []
kills = 0
energy = 0
round_num = 1

deck = [
    {'type': 'move', 'used': False}, {'type': 'move', 'used': False},
    {'type': 'move', 'used': False}, {'type': 'move', 'used': False},
    {'type': 'move', 'used': False},
    {'type': 'shoot', 'used': False}, {'type': 'shoot', 'used': False}
]
selected_slot = -1
laser_timer = 0
laser_coords = None

# UI Rects
deck_rects = []
card_w, card_h = 55, 45
start_x = (WIDTH - (len(deck) * (card_w + 8))) // 2
for i in range(len(deck)):
    deck_rects.append(pygame.Rect(start_x + i * (card_w + 8), GRID_HEIGHT + 45, card_w, card_h))

end_btn_rect = pygame.Rect(20, GRID_HEIGHT + 100, WIDTH - 40, 35)

# --- Engine Logic ---
def get_bug_at(x, y):
    for b in bugs:
        if b[0] == x and b[1] == y: return True
    return False

def get_pellet_at(x, y):
    for p in pellets:
        if p[0] == x and p[1] == y: return p
    return None

def spawn_entities(bug_count, pellet_count):
    # Spawn Bugs
    spawned = 0
    attempts = 0
    while spawned < bug_count and attempts < 200:
        rx, ry = random.randint(0, COLS-1), random.randint(0, ROWS-1)
        if not get_bug_at(rx, ry) and not get_pellet_at(rx, ry) and [rx, ry] != player:
            bugs.append([rx, ry])
            spawned += 1
        attempts += 1
        
    # Spawn Pellets
    spawned = 0
    attempts = 0
    while spawned < pellet_count and attempts < 200:
        rx, ry = random.randint(0, COLS-1), random.randint(0, ROWS-1)
        if not get_bug_at(rx, ry) and not get_pellet_at(rx, ry) and [rx, ry] != player:
            pellets.append([rx, ry])
            spawned += 1
        attempts += 1

def is_valid_move(tx, ty):
    if tx < 0 or tx >= COLS or ty < 0 or ty >= ROWS: return False
    dx = abs(tx - player[0])
    dy = abs(ty - player[1])
    
    # Must be cardinal, max 2 spaces
    if dx > 0 and dy > 0: return False # No diagonals
    dist = dx + dy
    if dist < 1 or dist > 2: return False
    
    # Target tile must not have a bug
    if get_bug_at(tx, ty): return False
    
    # If moving 2 spaces, the intermediate space must also not have a bug
    if dist == 2:
        mid_x = player[0] + (1 if tx > player[0] else -1 if tx < player[0] else 0)
        mid_y = player[1] + (1 if ty > player[1] else -1 if ty < player[1] else 0)
        if get_bug_at(mid_x, mid_y): return False
        
    return True

def is_valid_shoot(tx, ty):
    if tx < 0 or tx >= COLS or ty < 0 or ty >= ROWS: return False
    if tx == player[0] and ty == player[1]: return False
    return tx == player[0] or ty == player[1]

# Init
spawn_entities(bug_count=4, pellet_count=2)

# --- Main Loop ---
running = True
while running:
    mx, my = pygame.mouse.get_pos()
    hover_tile = [mx // TILE_SIZE, my // TILE_SIZE] if my < GRID_HEIGHT else [-1, -1]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if end_btn_rect.collidepoint(mx, my):
                round_num += 1
                for card in deck: card['used'] = False
                selected_slot = -1
                spawn_entities(bug_count=3, pellet_count=2)
            
            for i, rect in enumerate(deck_rects):
                if rect.collidepoint(mx, my) and not deck[i]['used']:
                    selected_slot = -1 if selected_slot == i else i
            
            if my < GRID_HEIGHT and selected_slot != -1:
                tx, ty = hover_tile
                card = deck[selected_slot]
                
                if card['type'] == 'move' and is_valid_move(tx, ty):
                    # Check if we moved over an intermediate space with a pellet (for 2-space jumps)
                    dist = abs(tx - player[0]) + abs(ty - player[1])
                    if dist == 2:
                        mid_x = player[0] + (1 if tx > player[0] else -1 if tx < player[0] else 0)
                        mid_y = player[1] + (1 if ty > player[1] else -1 if ty < player[1] else 0)
                        p1 = get_pellet_at(mid_x, mid_y)
                        if p1:
                            pellets.remove(p1)
                            energy += 1

                    # Move player
                    player = [tx, ty]
                    
                    # Check destination pellet
                    p2 = get_pellet_at(tx, ty)
                    if p2:
                        pellets.remove(p2)
                        energy += 1
                        
                    card['used'] = True
                    selected_slot = -1
                    
                elif card['type'] == 'shoot' and is_valid_shoot(tx, ty):
                    min_x, max_x = min(player[0], tx), max(player[0], tx)
                    min_y, max_y = min(player[1], ty), max(player[1], ty)
                    
                    surviving_bugs = []
                    for b in bugs:
                        hit = False
                        if player[0] == tx and b[0] == player[0] and min_y <= b[1] <= max_y: hit = True
                        if player[1] == ty and b[1] == player[1] and min_x <= b[0] <= max_x: hit = True
                        
                        if hit: kills += 1
                        else: surviving_bugs.append(b)
                    
                    bugs = surviving_bugs
                    card['used'] = True
                    selected_slot = -1
                    
                    laser_coords = (
                        player[0] * TILE_SIZE + TILE_SIZE//2, player[1] * TILE_SIZE + TILE_SIZE//2,
                        tx * TILE_SIZE + TILE_SIZE//2, ty * TILE_SIZE + TILE_SIZE//2
                    )
                    laser_timer = 8

    # --- Rendering ---
    screen.fill(BG_COLOR)
    
    # Grid
    for x in range(COLS):
        for y in range(ROWS):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)
    
    # Highlights
    if selected_slot != -1:
        ctype = deck[selected_slot]['type']
        for x in range(COLS):
            for y in range(ROWS):
                if ctype == 'move' and is_valid_move(x, y):
                    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    s.fill((79, 172, 254, 30))
                    screen.blit(s, (x * TILE_SIZE, y * TILE_SIZE))
                elif ctype == 'shoot' and is_valid_shoot(x, y):
                    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    s.fill((255, 94, 98, 30))
                    screen.blit(s, (x * TILE_SIZE, y * TILE_SIZE))

    # Entities
    for p in pellets:
        # Draw smaller square for pellets
        pygame.draw.rect(screen, PELLET_COLOR, (p[0]*TILE_SIZE + 18, p[1]*TILE_SIZE + 18, TILE_SIZE-36, TILE_SIZE-36))
    for b in bugs:
        pygame.draw.rect(screen, BUG_COLOR, (b[0]*TILE_SIZE + 4, b[1]*TILE_SIZE + 4, TILE_SIZE-8, TILE_SIZE-8))
    pygame.draw.rect(screen, PLAYER_COLOR, (player[0]*TILE_SIZE + 4, player[1]*TILE_SIZE + 4, TILE_SIZE-8, TILE_SIZE-8))

    # Hover
    if selected_slot != -1 and hover_tile[0] != -1:
        hx, hy = hover_tile
        ctype = deck[selected_slot]['type']
        if ctype == 'move' and is_valid_move(hx, hy):
            pygame.draw.rect(screen, PLAYER_COLOR, (hx*TILE_SIZE+4, hy*TILE_SIZE+4, TILE_SIZE-8, TILE_SIZE-8), 3)
        elif ctype == 'shoot' and is_valid_shoot(hx, hy):
            pygame.draw.rect(screen, SHOOT_COLOR, (hx*TILE_SIZE+4, hy*TILE_SIZE+4, TILE_SIZE-8, TILE_SIZE-8), 3)
            pygame.draw.line(screen, SHOOT_COLOR, 
                (player[0]*TILE_SIZE + TILE_SIZE//2, player[1]*TILE_SIZE + TILE_SIZE//2),
                (hx*TILE_SIZE + TILE_SIZE//2, hy*TILE_SIZE + TILE_SIZE//2), 4)

    # Laser
    if laser_timer > 0 and laser_coords:
        pygame.draw.line(screen, SHOOT_COLOR, laser_coords[0:2], laser_coords[2:4], 10)
        pygame.draw.line(screen, (255, 255, 255), laser_coords[0:2], laser_coords[2:4], 4)
        laser_timer -= 1

    # --- UI ---
    round_txt = big_font.render(f"ROUND: {round_num}", True, END_COLOR)
    kills_txt = big_font.render(f"KILLS: {kills}", True, BUG_COLOR)
    energy_txt = big_font.render(f"ENERGY: {energy}", True, PELLET_COLOR)
    
    screen.blit(round_txt, (20, GRID_HEIGHT + 10))
    screen.blit(energy_txt, (WIDTH // 2 - energy_txt.get_width()//2, GRID_HEIGHT + 10))
    screen.blit(kills_txt, (WIDTH - kills_txt.get_width() - 20, GRID_HEIGHT + 10))

    for i, rect in enumerate(deck_rects):
        card = deck[i]
        base_color = PLAYER_COLOR if card['type'] == 'move' else SHOOT_COLOR
        color = (70, 70, 70) if card['used'] else base_color
        bg = (30, 30, 30)
        if i == selected_slot: bg = (80, 80, 80)
        
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, color if not card['used'] else (50,50,50), rect, 2)
        lbl = font.render("MOV" if card['type'] == 'move' else "SHT", True, color)
        screen.blit(lbl, (rect.x + rect.w//2 - lbl.get_width()//2, rect.y + rect.h//2 - lbl.get_height()//2))

    pygame.draw.rect(screen, END_COLOR, end_btn_rect)
    end_lbl = font.render("END ROUND (Spawn Bugs)", True, (255, 255, 255))
    screen.blit(end_lbl, (end_btn_rect.x + end_btn_rect.w//2 - end_lbl.get_width()//2, end_btn_rect.y + end_btn_rect.h//2 - end_lbl.get_height()//2))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()