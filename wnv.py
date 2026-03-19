import pygame
import sys
import random
import numpy as np



SCREEN_WIDTH = 500
SCREEN_HEIGHT = 500
GRID_SIZE = 5
CELL_SIZE = SCREEN_WIDTH // GRID_SIZE 

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 165, 0)
LINE_COLOR = (200, 200, 200)

pygame.init()
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("5x5 Pygame Grid")
CLOCK = pygame.time.Clock()

def randomCell():
    return(random.randint(0, GRID_SIZE - 1))

def createMosquito(x, y):
    return {
        'x': x,
        'y': y,
        'infected': False
    }
def createBird(x, y):
    return {
        'x': x,
        'y': y,
        'infected': False,
        'dead': False
    }
def createHuman(x, y):
    return {
        'x': x,
        'y': y,
        'infected': False,
        'dead': False
    }

def biteCheck(host, victim):
    if (host['infected']):
        #add percentage here
        victim['infected'] = True
    return victim

def drawGrid():
    for x in range(0, SCREEN_WIDTH, CELL_SIZE):
        for y in range(0, SCREEN_HEIGHT, CELL_SIZE):

            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

            pygame.draw.rect(SCREEN, LINE_COLOR, rect, 1) 

def drawMosquito(x, y, infected):
    mPos = ((CELL_SIZE * x) + (CELL_SIZE * 1 / 4), (CELL_SIZE * y) + (CELL_SIZE * 1 / 4))
    miPos = ((CELL_SIZE * x) + (CELL_SIZE * 2 / 4), (CELL_SIZE * y) + (CELL_SIZE * 1 / 4))
    outerCircle = 50 / GRID_SIZE
    innerCircle = 25 / GRID_SIZE

    if (infected):
        pygame.draw.circle(SCREEN, RED, miPos, outerCircle)
        pygame.draw.circle(SCREEN, ORANGE, miPos, innerCircle)
    else:
        pygame.draw.circle(SCREEN, RED, mPos, outerCircle)

def drawBird(x, y, infected, dead):
    bPos = ((CELL_SIZE * x) + (CELL_SIZE * 1 / 4), (CELL_SIZE * y) + (CELL_SIZE * 2 / 4))
    biPos = ((CELL_SIZE * x) + (CELL_SIZE * 2 / 4), (CELL_SIZE * y) + (CELL_SIZE * 2 / 4))
    bdPos = ((CELL_SIZE * x) + (CELL_SIZE * 3 / 4), (CELL_SIZE * y) + (CELL_SIZE * 2 / 4))
    outerCircle = 50 / GRID_SIZE
    innerCircle = 25 / GRID_SIZE

    
    if (dead):
        pygame.draw.circle(SCREEN, GREEN, bdPos, outerCircle)
        pygame.draw.circle(SCREEN, BLACK, bdPos, innerCircle)
    elif (infected):
        pygame.draw.circle(SCREEN, GREEN, biPos, outerCircle)
        pygame.draw.circle(SCREEN, ORANGE, biPos, innerCircle)
    else:
        pygame.draw.circle(SCREEN, GREEN, bPos, outerCircle)

def drawHuman(x, y, infected, dead):
    hPos = ((CELL_SIZE * x) + (CELL_SIZE * 1 / 4), (CELL_SIZE * y) + (CELL_SIZE * 3 / 4))
    hiPos = ((CELL_SIZE * x) + (CELL_SIZE * 2 / 4), (CELL_SIZE * y) + (CELL_SIZE * 3 / 4))
    hdPos = ((CELL_SIZE * x) + (CELL_SIZE * 3 / 4), (CELL_SIZE * y) + (CELL_SIZE * 3 / 4))
    outerCircle = 50 / GRID_SIZE
    innerCircle = 25 / GRID_SIZE

    
    if (dead):
        pygame.draw.circle(SCREEN, BLUE, hdPos, outerCircle)
        pygame.draw.circle(SCREEN, BLACK, hdPos, innerCircle)
    elif (infected):
        pygame.draw.circle(SCREEN, BLUE, hiPos, outerCircle)
        pygame.draw.circle(SCREEN, ORANGE, hiPos, innerCircle)
    else:
        pygame.draw.circle(SCREEN, BLUE, hPos, outerCircle)

def placeEntities(m, b, h):
    for x in range(0, GRID_SIZE):
        for y in range(0, GRID_SIZE):
            for i in m:
                if (m[i]['x'] == x and m[i]['y'] == y):
                    drawMosquito(x, y, m[i]['infected'])
            for i in b:
                if (b[i]['x'] == x and b[i]['y'] == y):
                    drawBird(x, y, b[i]['infected'], b[i]['dead'])
            for i in h:
                if (h[i]['x'] == x and h[i]['y'] == y):
                    drawHuman(x, y, h[i]['infected'], h[i]['dead'])


def main():
    m = {}
    b = {}
    h = {}

    for i in range(0, 100):
        m[i] = createMosquito(randomCell(), randomCell())

    for i in range(0, 25):
        b[i] = createBird(randomCell(), randomCell())
        if (random.randint(0, 1) == 1):
            b[i]['infected'] = True
            if (random.randint(0, 1) == 1):
                b[i]['dead'] = True

    for i in range(0, 25):
        h[i] = createHuman(randomCell(), randomCell())
        if (random.randint(0, 1) == 1):
            h[i]['infected'] = True
            if (random.randint(0, 1) == 1):
                h[i]['dead'] = True
    
    #print(h['infected'])
    m[0]['infected'] = True
    #h = biteCheck(h[0], m[0])
   # print(h['infected'])
    print(m[0]['x'], m[0]['y'])

    while True:
        SCREEN.fill(BLACK)  # Fill the background with black

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        drawGrid()  # Call the function to draw the grid
        placeEntities(m, b, h)
        pygame.display.update()  # Update the display to make changes visible
        CLOCK.tick(30) # Cap the frame rate at 30 FPS

if __name__ == "__main__":
    main()
