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
PELLET_COLOR = (46, 204, 113)
SHOOT_COLOR  = (255, 94, 98)
END_COLOR    = (155, 89, 182)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bug Hunter: Meat Shields")
clock = pygame.time.Clock()
font = pygame.font.SysFont("courier", 16, bold=True)
big_font = pygame.font.SysFont("courier", 20, bold=True)

# --- Global State Variables ---
player = []
bugs = []
pellets = []
kills = 0
energy = 0
round_num = 1
deck = []
selected_slot = -1
laser_timer = 0
laser_coords = None
active_explosions = []
game_over = False

# UI Rects
card_w, card_h = 55, 45
start_x = 0
deck_rects = []
end_btn_rect = pygame.Rect(20, GRID_HEIGHT + 100, WIDTH - 40, 35)

def reset_game():
    global player, bugs, pellets, kills, energy, round_num, deck
    global selected_slot, laser_timer, laser_coords, active_explosions, game_over
    global deck_rects, start_x
    
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
    
    start_x = (WIDTH - (len(deck) * (card_w + 8))) // 2
    deck_rects = []
    for i in range(len(deck)):
        deck_rects.append(pygame.Rect(start_x + i * (card_w + 8), GRID_HEIGHT + 45, card_w, card_h))
        
    selected_slot = -1
    laser_timer = 0
    laser_coords = None
    active_explosions = []
    game_over = False
    
    spawn_entities(bug_count=4, pellet_count=3)

def get_bug_at(x, y):
    for b in bugs:
        if b[0] == x and b[1] == y: return b
    return None

def get_pellet_at(x, y):
    for p in pellets:
        if p[0] == x and p[1] == y: return p
    return None

def spawn_entities(bug_count, pellet_count):
    spawned = 0
    attempts = 0
    while spawned < bug_count and attempts < 200:
        rx, ry = random.randint(0, COLS-1), random.randint(0, ROWS-1)
        if not get_bug_at(rx, ry) and not get_pellet_at(rx, ry) and [rx, ry] != player:
            bugs.append([rx, ry])
            spawned += 1
        attempts += 1
        
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
    dx = tx - player[0]
    dy = ty - player[1]
    
    if dx != 0 and dy != 0: return False
    dist = abs(dx) + abs(dy)
    if dist < 1 or dist > 2: return False
    
    vx = 1 if dx > 0 else -1 if dx < 0 else 0
    vy = 1 if dy > 0 else -1 if dy < 0 else 0
    
    bugs_in_path = []
    for step in range(1, dist + 1):
        check_x = player[0] + vx * step
        check_y = player[1] + vy * step
        b = get_bug_at(check_x, check_y)
        if b: bugs_in_path.append(b)
        
    if len(bugs_in_path) > 1: return False 
        
    if len(bugs_in_path) == 1:
        push_x = tx + vx
        push_y = ty + vy
        
        if push_x < 0 or push_x >= COLS or push_y < 0 or push_y >= ROWS: return False 
        if get_bug_at(push_x, push_y): return False
            
    return True

def is_valid_shoot(tx, ty):
    if tx < 0 or tx >= COLS or ty < 0 or ty >= ROWS: return False
    if tx == player[0] and ty == player[1]: return False
    return tx == player[0] or ty == player[1]

# Recursive Explosion Resolver (3x3 AoE)
def resolve_explosions(initial_coords):
    global game_over, kills
    queue = initial_coords[:]
    exploded = set()
    
    while queue:
        cx, cy = queue.pop(0)
        if (cx, cy) in exploded: continue
        exploded.add((cx, cy))
        
        p = get_pellet_at(cx, cy)
        if p: pellets.remove(p)
        
        # radius=1 means 3x3 grid
        active_explosions.append({'x': cx, 'y': cy, 'timer': 20, 'radius': 1})
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = cx + dx, cy + dy
                
                if player[0] == nx and player[1] == ny:
                    game_over = True
                    
                if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS: continue
                
                b = get_bug_at(nx, ny)
                if b:
                    bugs.remove(b)
                    kills += 1
                
                np = get_pellet_at(nx, ny)
                if np and (nx, ny) not in exploded:
                    queue.append((nx, ny))

# Init
reset_game()

# --- Main Loop ---
running = True
while running:
    mx, my = pygame.mouse.get_pos()
    hover_tile = [mx // TILE_SIZE, my // TILE_SIZE] if my < GRID_HEIGHT else [-1, -1]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            
            if game_over:
                reset_game()
                continue
                
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
                    old_player = [player[0], player[1]]
                    dx = tx - player[0]
                    dy = ty - player[1]
                    dist = abs(dx) + abs(dy)
                    vx = 1 if dx > 0 else -1 if dx < 0 else 0
                    vy = 1 if dy > 0 else -1 if dy < 0 else 0
                    
                    pushed_bug = None
                    for step in range(1, dist + 1):
                        b = get_bug_at(player[0] + vx * step, player[1] + vy * step)
                        if b: pushed_bug = b
                        
                    # 1. Resolve Bug Push & Meat Shield
                    if pushed_bug:
                        push_x = pushed_bug[0] + vx
                        push_y = pushed_bug[1] + vy
                        
                        p = get_pellet_at(push_x, push_y)
                        if p:
                            # Meat Shield: Bug and Pellet annihilate! No AoE.
                            pellets.remove(p)
                            bugs.remove(pushed_bug)
                            kills += 1
                            # radius=0 means localized 1x1 pop
                            active_explosions.append({'x': push_x, 'y': push_y, 'timer': 15, 'radius': 0})
                        else:
                            pushed_bug[0] = push_x
                            pushed_bug[1] = push_y
                    
                    # 2. Resolve Energy Collection
                    for step in range(1, dist + 1):
                        check_x = old_player[0] + vx * step
                        check_y = old_player[1] + vy * step
                        p = get_pellet_at(check_x, check_y)
                        if p:
                            pellets.remove(p)
                            energy += 1

                    # 3. Move Player
                    player = [tx, ty]
                    card['used'] = True
                    selected_slot = -1
                    
                elif card['type'] == 'shoot' and is_valid_shoot(tx, ty):
                    min_x, max_x = min(player[0], tx), max(player[0], tx)
                    min_y, max_y = min(player[1], ty), max(player[1], ty)
                    
                    surviving_bugs = []
                    triggered_pellets = []
                    
                    for b in bugs:
                        hit = False
                        if player[0] == tx and b[0] == player[0] and min_y <= b[1] <= max_y: hit = True
                        if player[1] == ty and b[1] == player[1] and min_x <= b[0] <= max_x: hit = True
                        if hit: kills += 1
                        else: surviving_bugs.append(b)
                    
                    bugs = surviving_bugs
                    
                    for p in pellets:
                        hit = False
                        if player[0] == tx and p[0] == player[0] and min_y <= p[1] <= max_y: hit = True
                        if player[1] == ty and p[1] == player[1] and min_x <= p[0] <= max_x: hit = True
                        if hit: triggered_pellets.append((p[0], p[1]))
                        
                    card['used'] = True
                    selected_slot = -1
                    
                    laser_coords = (
                        player[0] * TILE_SIZE + TILE_SIZE//2, player[1] * TILE_SIZE + TILE_SIZE//2,
                        tx * TILE_SIZE + TILE_SIZE//2, ty * TILE_SIZE + TILE_SIZE//2
                    )
                    laser_timer = 8
                    
                    # 4. Trigger AoE Explosions from Shoot
                    if triggered_pellets:
                        resolve_explosions(triggered_pellets)

    # --- Rendering ---
    screen.fill(BG_COLOR)
    
    # Grid
    for x in range(COLS):
        for y in range(ROWS):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)
    
    # Highlights
    if selected_slot != -1 and not game_over:
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
        pygame.draw.rect(screen, PELLET_COLOR, (p[0]*TILE_SIZE + 18, p[1]*TILE_SIZE + 18, TILE_SIZE-36, TILE_SIZE-36))
    for b in bugs:
        pygame.draw.rect(screen, BUG_COLOR, (b[0]*TILE_SIZE + 4, b[1]*TILE_SIZE + 4, TILE_SIZE-8, TILE_SIZE-8))
    
    if not game_over:
        pygame.draw.rect(screen, PLAYER_COLOR, (player[0]*TILE_SIZE + 4, player[1]*TILE_SIZE + 4, TILE_SIZE-8, TILE_SIZE-8))

    # Hover
    if selected_slot != -1 and hover_tile[0] != -1 and not game_over:
        hx, hy = hover_tile
        ctype = deck[selected_slot]['type']
        if ctype == 'move' and is_valid_move(hx, hy):
            pygame.draw.rect(screen, PLAYER_COLOR, (hx*TILE_SIZE+4, hy*TILE_SIZE+4, TILE_SIZE-8, TILE_SIZE-8), 3)
            
            dx, dy = hx - player[0], hy - player[1]
            dist = abs(dx) + abs(dy)
            vx, vy = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
            
            pushing = False
            for step in range(1, dist + 1):
                if get_bug_at(player[0] + vx * step, player[1] + vy * step): pushing = True
            
            if pushing:
                ghost_x, ghost_y = hx + vx, hy + vy
                # Highlight in Pellet color to show it's a safe defuse!
                color = PELLET_COLOR if get_pellet_at(ghost_x, ghost_y) else BUG_COLOR 
                pygame.draw.rect(screen, color, (ghost_x*TILE_SIZE+4, ghost_y*TILE_SIZE+4, TILE_SIZE-8, TILE_SIZE-8), 3)
                
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

    # Explosions (Supports both 1x1 Meat Shields and 3x3 AoE)
    if active_explosions:
        blast_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        blast_surf.fill((255, 94, 98, 120))
        for exp in active_explosions:
            r = exp.get('radius', 1)
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    bx, by = exp['x'] + dx, exp['y'] + dy
                    if 0 <= bx < COLS and 0 <= by < ROWS:
                        screen.blit(blast_surf, (bx*TILE_SIZE, by*TILE_SIZE))
            exp['timer'] -= 1
        active_explosions = [e for e in active_explosions if e['timer'] > 0]

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
        color = (70, 70, 70) if card['used'] or game_over else base_color
        bg = (30, 30, 30)
        if i == selected_slot: bg = (80, 80, 80)
        
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, color if not card['used'] and not game_over else (50,50,50), rect, 2)
        lbl = font.render("MOV" if card['type'] == 'move' else "SHT", True, color)
        screen.blit(lbl, (rect.x + rect.w//2 - lbl.get_width()//2, rect.y + rect.h//2 - lbl.get_height()//2))

    # Draw End Button
    pygame.draw.rect(screen, (50,50,50) if game_over else END_COLOR, end_btn_rect)
    end_lbl = font.render("END ROUND (Spawn Bugs)", True, (255, 255, 255))
    screen.blit(end_lbl, (end_btn_rect.x + end_btn_rect.w//2 - end_lbl.get_width()//2, end_btn_rect.y + end_btn_rect.h//2 - end_lbl.get_height()//2))

    # Game Over Overlay
    if game_over:
        overlay = pygame.Surface((WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        go_txt = big_font.render("KILLED IN ACTION", True, SHOOT_COLOR)
        sub_txt = font.render("Click anywhere to Reboot", True, (200, 200, 200))
        
        screen.blit(go_txt, (WIDTH//2 - go_txt.get_width()//2, GRID_HEIGHT//2 - 20))
        screen.blit(sub_txt, (WIDTH//2 - sub_txt.get_width()//2, GRID_HEIGHT//2 + 20))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()