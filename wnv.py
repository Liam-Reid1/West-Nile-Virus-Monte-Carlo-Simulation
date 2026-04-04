import pygame
import sys
import random
import math
import csv
from datetime import datetime

# Display configuration
GRID_SIZE   = 20
CELL_SIZE   = 30
SIM_W       = GRID_SIZE * CELL_SIZE    # 600
SIDEBAR_W   = 300
SCREEN_W    = SIM_W + SIDEBAR_W        # 900
SCREEN_H    = SIM_W                    # 600

#Habitat types
EMPTY        = 0
WATER        = 1
FOREST       = 2
RESIDENTIAL  = 3

HAB_COLORS = {
    EMPTY:       (18,  22,  30),
    WATER:       (20,  50,  110),
    FOREST:      (15,  60,  25),
    RESIDENTIAL: (55,  48,  28),
}

# Colours
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_BG     = (12,  12,  20)
LINE_COL    = (35,  35,  55)
SIDE_BG     = (18,  18,  30)
LIGHT_GRAY  = (180, 180, 190)
DIM_GRAY    = (100, 100, 110)

MOSQ_C      = (220, 70,  70)
BIRD_C      = (70,  190, 70)
HUMAN_C     = (70,  130, 230)
EXP_C       = (240, 200, 30)
INF_C       = (255, 120, 0)
REC_C       = (80,  220, 220)
DEAD_C      = (90,  90,  90)

G_MI        = (220, 80,  80)
G_BI        = (80,  200, 80)
G_HI        = (80,  140, 255)
G_BD        = (20,  110, 20)
G_HD        = (20,  50,  140)

# Sim parameters
SIM_DAYS        = 365
FPS_DEFAULT     = 10
MC_RUNS         = 25

# Starting populations for each entity
INIT_MOSQ       = 40
INIT_BIRDS      = 20
INIT_RESIDENTS  = 5
INIT_HUMANS     = 12

# Incubus: Time until entity goes from exposed (E) to infected (I)
MOSQ_INCUB      = 14 
BIRD_INCUB      = 3
HUMAN_INCUB     = 7

BASE_BITE_BIRD  = 0.40
BASE_BITE_HUMAN = 0.20
P_MtoB          = 0.80
P_MtoH          = 0.35
P_BtoM          = 0.50

P_BIRD_DIE      = 0.12
P_BIRD_REC      = 0.08
P_HUMAN_DIE     = 0.02
P_HUMAN_REC     = 0.04

BASE_MOSQ       = 40
MOSQ_AMP        = 30
MOSQ_PEAK       = 182

MIGRATE_IN      = 80
MIGRATE_OUT     = 330

S, E, I, R, D = 'S', 'E', 'I', 'R', 'D'

# Pygame setup
pygame.init()
SCREEN = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("West Nile Virus — Monte Carlo Simulation")
CLOCK  = pygame.time.Clock()
FONT_S = pygame.font.SysFont('monospace', 11)
FONT_M = pygame.font.SysFont('monospace', 13)
FONT_L = pygame.font.SysFont('monospace', 15, bold=True)

#Habitat generations
def generate_habitat():
    grid = [[EMPTY] * GRID_SIZE for _ in range(GRID_SIZE)]

    def place_blob(htype, n_blobs, rmin, rmax):
        for _ in range(n_blobs):
            cx = random.randint(0, GRID_SIZE - 1)
            cy = random.randint(0, GRID_SIZE - 1)
            r  = random.randint(rmin, rmax)
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        x = max(0, min(GRID_SIZE - 1, cx + dx))
                        y = max(0, min(GRID_SIZE - 1, cy + dy))
                        grid[x][y] = htype

    place_blob(WATER,       3, 2, 3)
    place_blob(FOREST,      4, 2, 4)
    place_blob(RESIDENTIAL, 2, 2, 3)
    return grid

def cells_of_type(habitat, htype):
    return [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if habitat[x][y] == htype]

def pick_cell(preferred):
    if preferred:
        return list(random.choice(preferred))
    return [random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)]

def spawn_near_water(wcells):
    if wcells:
        wx, wy = random.choice(wcells)
        return (max(0, min(GRID_SIZE - 1, wx + random.randint(-2, 2))),
                max(0, min(GRID_SIZE - 1, wy + random.randint(-2, 2))))
    return random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)

# Temps and seasons
def temperature(day):
    return 16 + 16 * math.sin(2 * math.pi * (day - 80) / 365)

def bite_rates(day):
    temp = temperature(day)
    if temp < 5: # No biting below 5C
        return 0.0, 0.0
    scale = min(1.0, (temp - 5) / 20)
    return BASE_BITE_BIRD * scale, BASE_BITE_HUMAN * scale

def seasonal_mosq_target(day):
    phase = 2 * math.pi * (day - (MOSQ_PEAK - 91)) / 365
    return max(1, int(BASE_MOSQ + MOSQ_AMP * math.sin(phase)))

def season_info(day):
    d = day % 365
    if d < 80:  return "Winter", (150, 200, 255)
    if d < 172: return "Spring", (100, 220, 100)
    if d < 264: return "Summer", (255, 200,  50)
    if d < 355: return "Fall",   (200, 130,  50)
    return "Winter", (150, 200, 255)

#Entity Factories 
_uid = [0]
def new_id():
    _uid[0] += 1
    return _uid[0]

def make_mosquito(x, y):
    return {'id': new_id(), 'coords': [x, y], 'state': S, 'timer': 0}

def make_bird(x, y, resident=False):
    return {'id': new_id(), 'coords': [x, y], 'state': S, 'timer': 0,
            'home': [x, y], 'resident': resident}

def make_human(x, y):
    return {'id': new_id(), 'coords': [x, y], 'state': S, 'timer': 0, 'home': [x, y]}

#Movement
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def step_toward(pos, target):
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    if dx == 0 and dy == 0:
        return list(pos)
    if abs(dx) >= abs(dy):
        return [pos[0] + (1 if dx > 0 else -1), pos[1]]
    return [pos[0], pos[1] + (1 if dy > 0 else -1)]

def random_walk(entity):
    dx, dy = random.choice(DIRS)
    entity['coords'][0] = clamp(entity['coords'][0] + dx, 0, GRID_SIZE - 1)
    entity['coords'][1] = clamp(entity['coords'][1] + dy, 0, GRID_SIZE - 1)

def mosquito_walk(entity, hosts):
    if hosts and random.random() < 0.40:
        living = [h for h in hosts if h['state'] != D]
        if living:
            nearest = min(living, key=lambda h: abs(h['coords'][0] - entity['coords'][0])
                                                + abs(h['coords'][1] - entity['coords'][1]))
            if nearest['coords'] != entity['coords']:
                entity['coords'] = step_toward(entity['coords'], nearest['coords'])
                return
    random_walk(entity)

def human_walk(entity):
    if random.random() < 0.30 and entity['coords'] != entity['home']:
        entity['coords'] = step_toward(entity['coords'], entity['home'])
    else:
        random_walk(entity)

#Disease Logic 
def expose(entity, incubation):
    if entity['state'] == S:
        entity['state'] = E
        entity['timer'] = incubation

def tick_entities(mosquitoes, birds, humans):
    for m in mosquitoes:
        if m['state'] == E:
            m['timer'] -= 1
            if m['timer'] <= 0:
                m['state'] = I

    for b in birds:
        if b['state'] == E:
            b['timer'] -= 1
            if b['timer'] <= 0:
                b['state'] = I
        elif b['state'] == I:
            if random.random() < P_BIRD_DIE:
                b['state'] = D
            elif random.random() < P_BIRD_REC:
                b['state'] = R

    for h in humans:
        if h['state'] == E:
            h['timer'] -= 1
            if h['timer'] <= 0:
                h['state'] = I
        elif h['state'] == I:
            if random.random() < P_HUMAN_DIE:
                h['state'] = D
            elif random.random() < P_HUMAN_REC:
                h['state'] = R

def bite_check(mosquitoes, birds, humans, p_bite_bird, p_bite_human):
    bird_map = {}
    for b in birds:
        #if b['state'] != D:
        bird_map.setdefault(tuple(b['coords']), []).append(b)
    human_map = {}
    for h in humans:
        if h['state'] != D:
            human_map.setdefault(tuple(h['coords']), []).append(h)

    for m in mosquitoes:
        key = tuple(m['coords'])
        for b in bird_map.get(key, []):
            if random.random() < p_bite_bird:
                if m['state'] == I:
                    expose(b, BIRD_INCUB)
                if ((b['state'] == I or b['state'] == D) and m['state'] == S and random.random() < P_BtoM):
                    expose(m, MOSQ_INCUB)
        for h in human_map.get(key, []):
            if random.random() < p_bite_human:
                if m['state'] == I:
                    expose(h, HUMAN_INCUB)
                # Humans are dead-end hosts — mosquitoes cannot acquire WNV from humans

# Population Management
def update_mosquito_pop(mosquitoes, day, wcells):
    target = seasonal_mosq_target(day)
    while len(mosquitoes) < target:
        x, y = spawn_near_water(wcells)
        mosquitoes.append(make_mosquito(x, y))
    while len(mosquitoes) > target:
        sus = [m for m in mosquitoes if m['state'] == S]
        mosquitoes.remove(random.choice(sus if sus else mosquitoes))

def update_bird_pop(birds, day, fcells):
    migratory = [b for b in birds if not b['resident']]
    if MIGRATE_IN <= day < MIGRATE_OUT:
        target = INIT_BIRDS - INIT_RESIDENTS
        while len(migratory) < target:
            x, y = pick_cell(fcells)
            nb = make_bird(x, y, resident=False)
            birds.append(nb)
            migratory.append(nb)
    else:
        birds[:] = [b for b in birds if (b['resident'] or b['state'] == D)]

# Stats 
def _mean(lst):
    return sum(lst) / len(lst) if lst else 0.0

def _std(lst):
    if len(lst) < 2:
        return 0.0
    m = _mean(lst)
    return math.sqrt(sum((x - m) ** 2 for x in lst) / len(lst))

def count_states(entities):
    counts = {S: 0, E: 0, I: 0, R: 0, D: 0}
    for e in entities:
        counts[e['state']] += 1
    return counts

# Headless Simulation(Monte Carlo)
def run_headless(habitat, seed):
    random.seed(seed)
    wcells = cells_of_type(habitat, WATER)
    fcells = cells_of_type(habitat, FOREST)
    rcells = cells_of_type(habitat, RESIDENTIAL)

    mosquitoes = [make_mosquito(*spawn_near_water(wcells)) for _ in range(INIT_MOSQ)]
    birds = (
        [make_bird(*pick_cell(fcells), resident=True)  for _ in range(INIT_RESIDENTS)] +
        [make_bird(*pick_cell(fcells), resident=False) for _ in range(INIT_BIRDS - INIT_RESIDENTS)]
    )
    humans = [make_human(*pick_cell(rcells)) for _ in range(INIT_HUMANS)]
    if mosquitoes:
        mosquitoes[0]['state'] = I

    history = []
    all_hosts = birds + humans

    for day in range(1, SIM_DAYS + 1):
        pb, ph = bite_rates(day)
        for m in mosquitoes:
            mosquito_walk(m, all_hosts)
        for b in birds:
            if b['state'] != D:
                random_walk(b)
        for h in humans:
            if h['state'] != D:
                human_walk(h)
        bite_check(mosquitoes, birds, humans, pb, ph)
        tick_entities(mosquitoes, birds, humans)
        update_mosquito_pop(mosquitoes, day, wcells)
        update_bird_pop(birds, day, fcells)
        mc = count_states(mosquitoes)
        bc = count_states(birds)
        hc = count_states(humans)
        history.append((mc[E], mc[I], bc[E], bc[I], hc[E], hc[I], bc[D], hc[D]))
        all_hosts = birds + humans

    return history

def compute_mc_bands(all_histories):
    n = len(all_histories)
    bands = []
    for d in range(SIM_DAYS):
        mi = [all_histories[r][d][0] + all_histories[r][d][1] for r in range(n)]
        bi = [all_histories[r][d][2] + all_histories[r][d][3] for r in range(n)]
        hi = [all_histories[r][d][4] + all_histories[r][d][5] for r in range(n)]
        bd = [all_histories[r][d][6] for r in range(n)]
        hd = [all_histories[r][d][7] for r in range(n)]
        bands.append({
            'mi': (_mean(mi), _std(mi)),
            'bi': (_mean(bi), _std(bi)),
            'hi': (_mean(hi), _std(hi)),
            'bd': (_mean(bd), _std(bd)),
            'hd': (_mean(hd), _std(hd)),
        })
    return bands

# Drawing
def entity_color(entity, base):
    s = entity['state']
    if s == S: return base
    if s == E: return EXP_C
    if s == I: return INF_C
    if s == R: return REC_C
    return DEAD_C

def draw_habitat(habitat):
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            pygame.draw.rect(SCREEN, HAB_COLORS[habitat[x][y]],
                             (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

def draw_grid():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            pygame.draw.rect(SCREEN, LINE_COL,
                             (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

def draw_entities(mosquitoes, birds, humans):
    rm = max(3, CELL_SIZE // 7)
    rb = max(4, CELL_SIZE // 6)
    rh = max(4, CELL_SIZE // 6)

    for m in mosquitoes:
        cx = m['coords'][0] * CELL_SIZE + CELL_SIZE // 4
        cy = m['coords'][1] * CELL_SIZE + CELL_SIZE // 4
        pygame.draw.circle(SCREEN, entity_color(m, MOSQ_C), (cx, cy), rm)

    for b in birds:
        cx = b['coords'][0] * CELL_SIZE + CELL_SIZE // 4
        cy = b['coords'][1] * CELL_SIZE + 3 * CELL_SIZE // 4
        pygame.draw.circle(SCREEN, entity_color(b, BIRD_C), (cx, cy), rb)
        if b['state'] == D:
            pygame.draw.line(SCREEN, BLACK, (cx - rb + 2, cy - rb + 2), (cx + rb - 2, cy + rb - 2), 2)
            pygame.draw.line(SCREEN, BLACK, (cx + rb - 2, cy - rb + 2), (cx - rb + 2, cy + rb - 2), 2)

    for h in humans:
        cx = h['coords'][0] * CELL_SIZE + 3 * CELL_SIZE // 4
        cy = h['coords'][1] * CELL_SIZE + CELL_SIZE // 2
        pygame.draw.circle(SCREEN, entity_color(h, HUMAN_C), (cx, cy), rh)
        if h['state'] == D:
            pygame.draw.line(SCREEN, BLACK, (cx - rh + 2, cy - rh + 2), (cx + rh - 2, cy + rh - 2), 2)
            pygame.draw.line(SCREEN, BLACK, (cx + rh - 2, cy - rh + 2), (cx - rh + 2, cy + rh - 2), 2)

def draw_sidebar(day, mosquitoes, birds, humans, history, mc_bands, paused, fps):
    pygame.draw.rect(SCREEN, SIDE_BG, (SIM_W, 0, SIDEBAR_W, SCREEN_H))
    pygame.draw.line(SCREEN, (60, 60, 90), (SIM_W, 0), (SIM_W, SCREEN_H), 2)

    pad = 12
    x0  = SIM_W + pad
    w   = SIDEBAR_W - 2 * pad
    y   = 8

    sname, scol = season_info(day)
    temp_c = temperature(day)

    def txt(s, col, font=FONT_M):
        nonlocal y
        surf = font.render(s, True, col)
        SCREEN.blit(surf, (x0, y))
        y += surf.get_height() + 3

    status = " [PAUSED]" if paused else f"  {fps}fps"
    txt("West Nile Virus", WHITE, FONT_L)
    txt(f"Day {day:03d}  {sname}{status}", scol)
    txt(f"Temp: {temp_c:.1f}C   Mosq target: {seasonal_mosq_target(day)}", DIM_GRAY, FONT_S)
    y += 4

    pygame.draw.line(SCREEN, (50, 50, 70), (x0, y), (x0 + w, y), 1)
    y += 6

    mc = count_states(mosquitoes)
    bc = count_states(birds)
    hc = count_states(humans)

    def species_row(label, col, counts, show_rd=True):
        nonlocal y
        SCREEN.blit(FONT_M.render(label, True, col), (x0, y))
        y += FONT_M.get_height() + 1
        inf  = counts[E] + counts[I]
        line = f"  total:{sum(counts.values())}  sick:{inf}"
        if show_rd:
            line += f"  dead:{counts[D]}"
        SCREEN.blit(FONT_S.render(line, True, LIGHT_GRAY), (x0, y))
        y += FONT_S.get_height() + 5

    species_row("Mosquitoes", MOSQ_C, mc, show_rd=False)
    species_row("Birds",      BIRD_C, bc)
    species_row("Humans",     HUMAN_C, hc)

    pygame.draw.line(SCREEN, (50, 50, 70), (x0, y), (x0 + w, y), 1)
    y += 6

    legend = [
        (MOSQ_C,  "Mosquito"), (BIRD_C, "Bird"), (HUMAN_C, "Human"),
        (EXP_C,   "Exposed"),  (INF_C,  "Infectious"), (REC_C, "Recovered"),
        (DEAD_C,  "Dead"),
    ]
    for col, label in legend:
        pygame.draw.circle(SCREEN, col, (x0 + 5, y + 6), 5)
        SCREEN.blit(FONT_S.render(label, True, LIGHT_GRAY), (x0 + 14, y + 1))
        y += 14

    txt("Space=pause  Up/Down=speed  E=export", DIM_GRAY, FONT_S)

    pygame.draw.line(SCREEN, (50, 50, 70), (x0, y), (x0 + w, y), 1)
    y += 6

    # Infection graph
    graph_h = SCREEN_H - y - 22
    if graph_h < 30 or len(history) < 2:
        return

    gx, gy, gw, gh = x0, y, w, graph_h
    pygame.draw.rect(SCREEN, (10, 10, 18), (gx, gy, gw, gh))
    pygame.draw.rect(SCREEN, (50, 50, 70), (gx, gy, gw, gh), 1)

    # Stable max_val from MC bands so the scale doesn't jump
    if mc_bands:
        max_val = max(
            max(b['mi'][0] + b['mi'][1] for b in mc_bands),
            max(b['bi'][0] + b['bi'][1] for b in mc_bands),
            max(b['hi'][0] + b['hi'][1] for b in mc_bands),
            1
        )
    else:
        all_v = ([h[0]+h[1] for h in history] +
                 [h[2]+h[3] for h in history] +
                 [h[4]+h[5] for h in history])
        max_val = max(max(all_v), 1)

    def px_of(idx, val):
        px = gx + int(idx / (SIM_DAYS - 1) * gw)
        py = gy + gh - int(clamp(val, 0, max_val) / max_val * gh)
        return px, py

    # MC confidence bands (filled semi-transparent polygon)
    if mc_bands:
        band_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for key, color in [('mi', G_MI), ('bi', G_BI), ('hi', G_HI)]:
            upper = [px_of(i, mc_bands[i][key][0] + mc_bands[i][key][1]) for i in range(len(mc_bands))]
            lower = [px_of(i, max(0.0, mc_bands[i][key][0] - mc_bands[i][key][1])) for i in range(len(mc_bands))]
            poly  = upper + lower[::-1]
            if len(poly) >= 3:
                pygame.draw.polygon(band_surf, (*color, 35), poly)
        SCREEN.blit(band_surf, (0, 0))

        # MC mean lines (dashed)
        for key, color in [('mi', G_MI), ('bi', G_BI), ('hi', G_HI)]:
            pts   = [px_of(i, mc_bands[i][key][0]) for i in range(len(mc_bands))]
            muted = tuple(c // 2 for c in color)
            for k in range(0, len(pts) - 1, 2):
                pygame.draw.line(SCREEN, muted, pts[k], pts[k + 1], 1)

    # Live run lines
    def draw_curve(series, color, width=1):
        pts = [px_of(i, v) for i, v in enumerate(series)]
        for k in range(len(pts) - 1):
            pygame.draw.line(SCREEN, color, pts[k], pts[k + 1], width)

    draw_curve([h[0] + h[1] for h in history], G_MI)
    draw_curve([h[2] + h[3] for h in history], G_BI)
    draw_curve([h[6]         for h in history], G_BD)
    draw_curve([h[4] + h[5] for h in history], G_HI, 2)
    draw_curve([h[7]         for h in history], G_HD)

    y = gy + gh + 4
    labels = [("M.inf", G_MI), ("B.inf", G_BI), ("B.dead", G_BD), ("H.inf", G_HI), ("H.dead", G_HD)]
    lx = gx
    for lbl, col in labels:
        surf = FONT_S.render(lbl, True, col)
        SCREEN.blit(surf, (lx, y))
        lx += surf.get_width() + 5

def show_loading(i, total):
    SCREEN.fill(DARK_BG)
    bar_w, bar_h = 400, 20
    bx = (SCREEN_W - bar_w) // 2
    by = SCREEN_H // 2 + 20
    prog = int(bar_w * i / total)
    SCREEN.blit(FONT_L.render("Running Monte Carlo Pre-Simulation...", True, WHITE),
                (SCREEN_W // 2 - 195, SCREEN_H // 2 - 40))
    SCREEN.blit(FONT_M.render(f"Run {i} of {total}", True, LIGHT_GRAY),
                (SCREEN_W // 2 - 55, SCREEN_H // 2))
    pygame.draw.rect(SCREEN, DIM_GRAY, (bx, by, bar_w, bar_h))
    pygame.draw.rect(SCREEN, G_HI,    (bx, by, prog,  bar_h))
    pygame.display.flip()

def show_summary(history, mc_bands):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    SCREEN.blit(overlay, (0, 0))

    cx = SCREEN_W // 2
    y  = 100
    SCREEN.blit(FONT_L.render("── Simulation Complete ──", True, WHITE), (cx - 125, y))
    y += 50

    peak_day = max(range(len(history)), key=lambda d: history[d][4] + history[d][5]) + 1
    peak_val = history[peak_day - 1][4] + history[peak_day - 1][5]
    h_dead   = history[-1][7]
    b_dead   = history[-1][6]
    days_inf = sum(1 for h in history if h[4] + h[5] > 0)

    rows = [
        ("Peak human infections:",  f"{peak_val}  (day {peak_day})"),
        ("Human deaths:",           str(h_dead)),
        ("Bird deaths:",            str(b_dead)),
        ("Days with human cases:",  str(days_inf)),
    ]
    if mc_bands:
        mc_peak = max(b['hi'][0] for b in mc_bands)
        rows.append(("MC avg peak (humans):", f"{mc_peak:.1f}"))

    for label, val in rows:
        SCREEN.blit(FONT_M.render(label, True, LIGHT_GRAY), (cx - 220, y))
        SCREEN.blit(FONT_M.render(val,   True, WHITE),      (cx + 20,  y))
        y += 30

    y += 20
    SCREEN.blit(FONT_S.render("E = export CSV     Esc = quit", True, DIM_GRAY), (cx - 115, y))
    pygame.display.flip()

def export_csv(history):
    import os
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, f"wnv_sim_{ts}.csv")
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['day', 'mosq_exposed', 'mosq_inf', 'bird_exposed', 'bird_inf',
                             'human_exposed', 'human_inf', 'bird_dead', 'human_dead'])
            for d, h in enumerate(history, 1):
                writer.writerow([d, h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]])
        print(f"Exported: {filename}")
    except OSError as e:
        print(f"Export failed: {e}")
    return filename

# Main Loop
def main():
    habitat = generate_habitat()
    wcells  = cells_of_type(habitat, WATER)
    fcells  = cells_of_type(habitat, FOREST)
    rcells  = cells_of_type(habitat, RESIDENTIAL)

    # Monte Carlo pre-runs 
    all_histories = []
    for i in range(MC_RUNS):
        show_loading(i + 1, MC_RUNS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        all_histories.append(run_headless(habitat, seed=i * 17 + 42))
    mc_bands = compute_mc_bands(all_histories)
    random.seed()  # Re-randomise for the live run

    #Live simulation setup 
    mosquitoes = [make_mosquito(*spawn_near_water(wcells)) for _ in range(INIT_MOSQ)]
    birds = (
        [make_bird(*pick_cell(fcells), resident=True)  for _ in range(INIT_RESIDENTS)] +
        [make_bird(*pick_cell(fcells), resident=False) for _ in range(INIT_BIRDS - INIT_RESIDENTS)]
    )
    humans    = [make_human(*pick_cell(rcells)) for _ in range(INIT_HUMANS)]
    # Seed 5 infectious mosquitoes and 1 infectious bird to kick off the outbreak
    for m in mosquitoes[:5]:
        m['state'] = I
    if birds:
        birds[0]['state'] = I

    history   = []
    all_hosts = birds + humans
    paused    = False
    fps       = FPS_DEFAULT
    day       = 1

    while day <= SIM_DAYS:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_UP:
                    fps = min(60, fps + 5)
                if event.key == pygame.K_DOWN:
                    fps = max(1, fps - 5)
                if event.key == pygame.K_e:
                    export_csv(history)

        SCREEN.fill(DARK_BG)
        draw_habitat(habitat)
        draw_grid()
        draw_entities(mosquitoes, birds, humans)
        draw_sidebar(day, mosquitoes, birds, humans, history, mc_bands, paused, fps)
        pygame.display.flip()
        CLOCK.tick(fps)

        if paused:
            continue

        # Sim step
        pb, ph = bite_rates(day)

        for m in mosquitoes:
            mosquito_walk(m, all_hosts)
        for b in birds:
            if b['state'] != D:
                random_walk(b)
        for h in humans:
            if h['state'] != D:
                human_walk(h)

        bite_check(mosquitoes, birds, humans, pb, ph)
        tick_entities(mosquitoes, birds, humans)
        update_mosquito_pop(mosquitoes, day, wcells)
        update_bird_pop(birds, day, fcells)

        mc = count_states(mosquitoes)
        bc = count_states(birds)
        hc = count_states(humans)
        history.append((mc[E], mc[I], bc[E], bc[I], hc[E], hc[I], bc[D], hc[D]))
        all_hosts = birds + humans
        day += 1

    # Post sim 
    #export_csv(history)
    show_summary(history, mc_bands)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_e:
                    export_csv(history)
        CLOCK.tick(10)

if __name__ == "__main__":
    main()
