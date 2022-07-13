from tkinter import *
from random import getrandbits, random
from copy import deepcopy
from colorsys import hsv_to_rgb
from textwrap import wrap
from math import sqrt, floor, ceil
from time import time

AIR = 0
WALL = 1
SAND = 2
WATER = 3
SANDCLONER = 4
WATERCLONER = 5
DELETER = 6

def alterColor(color, variation):
    h, s, v = color
    h, s, v = (h / 360), s / 100, v / 100
    s += (random() - 0.5) * variation
    v += (random() - 0.5) * variation
    if s < 0: s = 0
    if s > 1: s = 1
    if v < 0: v = 0
    if v > 1: v = 1
    r, g, b = [round(i * 255) for i in hsv_to_rgb(h, s, v)]
    return '#%02x%02x%02x' % (r, g, b)

def changeBrightness(color, variation):
    r, g, b = [int(i, 16) for i in wrap(color[1:], 2)]
    r += variation
    g += variation
    b += variation
    if r < 0: r = 0
    if r > 255: r = 255
    if g < 0: g = 0
    if g > 255: g = 255
    if b < 0: b = 0
    if b > 255: b = 255
    return '#%02x%02x%02x' % (r, g, b)

def randomBool(): return bool(getrandbits(1))

class Sandbox:
    def __init__(self):
        self.CELLSIZE = 20

        self.BG = '#c0e8fc'

        self.SANDCOLOR = (45, 45, 86)
        self.WATERCOLOR = (193, 95, 100)
        self.WALLCOLOR = (224, 37, 34)
        self.DELETERCOLOR = (15, 100, 74)

        self.TARGETFPS = 300
        
        self.master = Tk()
        self.master.title('Sand Simulation')
        self.master.resizable(0, 0)
        self.master.attributes('-fullscreen', True)
        self.WIDTH = self.master.winfo_screenwidth() // self.CELLSIZE
        self.HEIGHT = self.master.winfo_screenheight() // self.CELLSIZE
        self.canvas = Canvas(self.master, width=self.WIDTH * self.CELLSIZE, height=self.HEIGHT * self.CELLSIZE, bg=self.BG, highlightthickness=0)
        self.canvas.pack()

        self.map = [[AIR] * self.WIDTH for i in range(self.HEIGHT)]
        self.colors = [[self.BG] * self.WIDTH for i in range(self.HEIGHT)]
        self.positions = []
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self.positions.append([x, y])
        self.positions.reverse()

        self.dragging, self.dragX, self.dragY = False, 0, 0
        self.rightPressed, self.deleteX, self.deleteY = False, 0, 0
        self.canvas.bind('<Button-1>', self.mouseDown)
        self.canvas.bind('<B1-Motion>', self.mouseDrag)
        self.canvas.bind('<ButtonRelease-1>', self.mouseUp)
        self.canvas.bind('<Button-3>', self.rightDown)
        self.canvas.bind('<B3-Motion>', self.rightDrag)
        self.canvas.bind('<ButtonRelease-3>', self.rightUp)

        self.images = [PhotoImage(file='images/sandButton.png'), PhotoImage(file='images/sandButtonActivated.png'),
                       PhotoImage(file='images/waterButton.png'), PhotoImage(file='images/waterButtonActivated.png'),
                       PhotoImage(file='images/wallButton.png'), PhotoImage(file='images/wallButtonActivated.png'),
                       PhotoImage(file='images/playButton.png'), PhotoImage(file='images/pauseButton.png'),
                       PhotoImage(file='images/cloneButton.png'), PhotoImage(file='images/cloneButtonActivated.png'),
                       PhotoImage(file='images/deleterButton.png'), PhotoImage(file='images/deleterButtonActivated.png'),
                       PhotoImage(file='images/sand.png'), PhotoImage(file='images/water.png'),
                       PhotoImage(file='images/settingsButton.png'), PhotoImage(file='images/settingsMenu.png')]
        self.sandButton = self.canvas.create_image(125, 125, image=self.images[1])
        self.waterButton = self.canvas.create_image(325, 125, image=self.images[2])
        self.wallButton = self.canvas.create_image(525, 125, image=self.images[4])
        self.cloneButton = self.canvas.create_image(925, 125, image=self.images[8])
        self.cloneModeImage = self.canvas.create_image(925, 125, image=self.images[12])
        self.deleterButton = self.canvas.create_image(1125, 125, image=self.images[10])
        self.settingsButton = self.canvas.create_image(self.WIDTH * self.CELLSIZE - 325, 125, image=self.images[14])
        self.playPauseButton = self.canvas.create_image(self.WIDTH * self.CELLSIZE - 125, 125, image=self.images[7])
        self.settingsMenu = self.canvas.create_image(self.WIDTH * self.CELLSIZE // 2, self.HEIGHT * self.CELLSIZE // 2, image=self.images[15], state=HIDDEN)

        self.drawingMode = SAND
        self.playing = True
        self.cloneMode = SAND
        self.cloneModeOn = False
        self.sandCloners = []
        self.waterCloners = []
        self.deleters = []
        self.settingsShown = False
        self.midX = self.WIDTH * self.CELLSIZE // 2
        self.midY = self.HEIGHT * self.CELLSIZE // 2
        self.settingsMenuElements = [
            [self.settingsMenu,
             self.canvas.create_text(self.midX, self.midY - 400, text='Settings Menu', font=('Helvetica', 40), state=HIDDEN)]
        ]

        self.master.after(round(1 / self.TARGETFPS * 1000), self.frame)
        self.master.mainloop()

    def showSettingsMenu(self):
        for element in self.settingsMenuElements[0]:
            self.canvas.itemconfig(element, state=NORMAL)

        self.playing = False
        self.settingsShown = True

    def hideSettingsMenu(self):
        for element in self.settingsMenuElements[0]:
            self.canvas.itemconfig(element, state=HIDDEN)

        self.playing = True
        self.settingsShown = False

    def swapBlocks(self, x1, y1, x2, y2):
        block1 = self.map[y1][x1]
        color1 = self.colors[y1][x1]
        self.map[y1][x1] = self.map[y2][x2]
        self.colors[y1][x1] = self.colors[y2][x2]
        self.map[y2][x2] = block1
        self.colors[y2][x2] = color1

    def rightDown(self, event):
        if 850 < event.x < 1000 and 50 < event.y < 200:
            if self.cloneMode == SAND:
                self.cloneMode = WATER
                self.canvas.itemconfig(self.cloneModeImage, image=self.images[13])
            else:
                self.cloneMode = SAND
                self.canvas.itemconfig(self.cloneModeImage, image=self.images[12])
        else:
            self.rightPressed = True
            self.deleteX = event.x // self.CELLSIZE
            self.deleteY = event.y // self.CELLSIZE

    def rightDrag(self, event):
        self.deleteX = event.x // self.CELLSIZE
        self.deleteY = event.y // self.CELLSIZE

    def rightUp(self, event):
        self.rightPressed = False

    def mouseDown(self, event):
        if self.settingsShown:
            x, y = event.x - self.midX, event.y - self.midY

            if 500 < x < 600 and -450 < y < -350: self.hideSettingsMenu()
            elif -600 < x < 600 and -350 < y < 450: print('On God')
        else:
            if 50 < event.y < 200:
                if 50 < event.x < 200:
                    self.drawingMode = SAND
                    self.canvas.itemconfig(self.sandButton, image=self.images[1])
                    self.canvas.itemconfig(self.waterButton, image=self.images[2])
                    self.canvas.itemconfig(self.wallButton, image=self.images[4])
                    self.canvas.itemconfig(self.cloneButton, image=self.images[8])
                    self.canvas.itemconfig(self.deleterButton, image=self.images[10])
                    self.cloneModeOn = False
                if 250 < event.x < 400:
                    self.drawingMode = WATER
                    self.canvas.itemconfig(self.sandButton, image=self.images[0])
                    self.canvas.itemconfig(self.waterButton, image=self.images[3])
                    self.canvas.itemconfig(self.wallButton, image=self.images[4])
                    self.canvas.itemconfig(self.cloneButton, image=self.images[8])
                    self.canvas.itemconfig(self.deleterButton, image=self.images[10])
                    self.cloneModeOn = False
                if 450 < event.x < 600:
                    self.drawingMode = WALL
                    self.canvas.itemconfig(self.sandButton, image=self.images[0])
                    self.canvas.itemconfig(self.waterButton, image=self.images[2])
                    self.canvas.itemconfig(self.wallButton, image=self.images[5])
                    self.canvas.itemconfig(self.cloneButton, image=self.images[8])
                    self.canvas.itemconfig(self.deleterButton, image=self.images[10])
                    self.cloneModeOn = False
                if 850 < event.x < 1000:
                    self.drawingMode = None
                    self.canvas.itemconfig(self.sandButton, image=self.images[0])
                    self.canvas.itemconfig(self.waterButton, image=self.images[2])
                    self.canvas.itemconfig(self.wallButton, image=self.images[4])
                    self.canvas.itemconfig(self.deleterButton, image=self.images[10])
                    if self.cloneModeOn:
                        self.cloneModeOn = False
                        self.canvas.itemconfig(self.cloneButton, image=self.images[8])
                    else:
                        self.cloneModeOn = True
                        self.canvas.itemconfig(self.cloneButton, image=self.images[9])
                if 1050 < event.x < 1200:
                    self.drawingMode = DELETER
                    self.canvas.itemconfig(self.sandButton, image=self.images[0])
                    self.canvas.itemconfig(self.waterButton, image=self.images[2])
                    self.canvas.itemconfig(self.wallButton, image=self.images[4])
                    self.canvas.itemconfig(self.cloneButton, image=self.images[8])
                    self.canvas.itemconfig(self.deleterButton, image=self.images[11])
                    self.cloneModeOn = False
                if self.WIDTH * self.CELLSIZE - 200 < event.x < self.WIDTH * self.CELLSIZE - 50:
                    self.playing = not self.playing
                    self.canvas.itemconfig(self.playPauseButton, image=self.images[7] if self.playing else self.images[6])
                if self.WIDTH * self.CELLSIZE - 400 < event.x < self.WIDTH * self.CELLSIZE - 250:
                    self.drawingMode = None
                    self.canvas.itemconfig(self.sandButton, image=self.images[0])
                    self.canvas.itemconfig(self.waterButton, image=self.images[2])
                    self.canvas.itemconfig(self.wallButton, image=self.images[4])
                    self.canvas.itemconfig(self.deleterButton, image=self.images[10])
                    self.canvas.itemconfig(self.cloneButton, image=self.images[8])
                    self.cloneModeOn = False
                    self.showSettingsMenu()
            else:
                self.dragging = True
                
                self.dragX = event.x // self.CELLSIZE
                self.dragY = event.y // self.CELLSIZE

                if self.dragX > self.WIDTH - 1: self.dragX = self.WIDTH - 1
                if self.dragX < 0: self.dragX = 0
                if self.dragY > self.HEIGHT - 1: self.dragY = self.HEIGHT - 1
                if self.dragY < 0: self.dragY = 0

    def mouseDrag(self, event):
        self.dragX = event.x // self.CELLSIZE
        self.dragY = event.y // self.CELLSIZE

        if self.dragX > self.WIDTH - 1: self.dragX = self.WIDTH - 1
        if self.dragX < 0: self.dragX = 0
        if self.dragY > self.HEIGHT - 1: self.dragY = self.HEIGHT - 1
        if self.dragY < 0: self.dragY = 0

    def mouseUp(self, event):
        self.dragging = False

    def updateParticles(self):
        movedWaterBlocks = []
        
        for block in self.positions:
            x, y = block
            block = self.map[y][x]

            if block not in [AIR, WALL]:
                if x == 0: left, belowLeft = WALL, WALL
                else:
                    left = self.map[y][x - 1]
                    if y < self.HEIGHT - 1: belowLeft = self.map[y + 1][x - 1]
                    else: belowLeft = WALL

                if x == self.WIDTH - 1: right, belowRight = WALL, WALL
                else:
                    right = self.map[y][x + 1]
                    if y < self.HEIGHT - 1: belowRight = self.map[y + 1][x + 1]
                    else: belowRight = WALL

                if y == self.HEIGHT - 1: down, belowLeft, belowRight = WALL, WALL, WALL
                else: down = self.map[y + 1][x]

                if block == WATER and [x, y] not in movedWaterBlocks:
                    if down == AIR: self.swapBlocks(x, y, x, y + 1)
                    else:
                        if [left, right] == [AIR, AIR] and belowLeft != AIR and belowRight != AIR:
                            if randomBool():
                                self.swapBlocks(x, y, x - 1, y)
                                movedWaterBlocks.append([x - 1, y])
                            else:
                                self.swapBlocks(x, y, x + 1, y)
                                movedWaterBlocks.append([x + 1, y])
                        else:
                            if left != AIR and right == AIR and belowRight != AIR:
                                self.swapBlocks(x, y, x + 1, y)
                                movedWaterBlocks.append([x + 1, y])
                            if right != AIR and left == AIR and belowLeft != AIR:
                                self.swapBlocks(x, y, x - 1, y)
                                movedWaterBlocks.append([x - 1, y])

                        if [left, right, belowLeft, belowRight] == [AIR, AIR, AIR, AIR]:
                            if randomBool():
                                self.swapBlocks(x, y, x - 1, y + 1)
                                movedWaterBlocks.append([x - 1, y + 1])
                            else:
                                self.swapBlocks(x, y, x + 1, y + 1)
                                movedWaterBlocks.append([x + 1, y + 1])
                        else:
                            if left == AIR and belowLeft == AIR:
                                self.swapBlocks(x, y, x - 1, y + 1)
                                movedWaterBlocks.append([x - 1, y + 1])
                            if right == AIR and belowRight == AIR:
                                self.swapBlocks(x, y, x + 1, y + 1)
                                movedWaterBlocks.append([x + 1, y + 1])

                elif block == SAND:
                    if y == 0: up = WALL
                    else: up = self.map[y - 1][x]

                    inWater = False
                    if up == WATER or left == WATER or right == WATER or down == WATER:
                        inWater = True
                    
                    if down in [AIR, WATER]:
                        if inWater:
                            if randomBool(): self.swapBlocks(x, y, x, y + 1)
                        else: self.swapBlocks(x, y, x, y + 1)
                    else:
                        if left in [AIR, WATER] and right in [AIR, WATER] and belowLeft in [AIR, WATER] and belowRight in [AIR, WATER]:
                            if randomBool():
                                if inWater:
                                    if randomBool(): self.swapBlocks(x, y, x - 1, y + 1)
                                else: self.swapBlocks(x, y, x - 1, y + 1)
                            else:
                                if inWater:
                                    if randomBool(): self.swapBlocks(x, y, x + 1, y + 1)
                                else: self.swapBlocks(x, y, x + 1, y + 1)
                        else:
                            if belowLeft in [AIR, WATER] and left in [AIR, WATER]:
                                if inWater:
                                    if randomBool(): self.swapBlocks(x, y, x - 1, y + 1)
                                else: self.swapBlocks(x, y, x - 1, y + 1)
                            if belowRight in [AIR, WATER] and right in [AIR, WATER]:
                                if inWater:
                                    if randomBool(): self.swapBlocks(x, y, x + 1, y + 1)
                                else: self.swapBlocks(x, y, x + 1, y + 1)

    def handleCloners(self):
        for cloner in self.sandCloners:
            x, y = cloner

            if x == 0: left = WALL
            else: left = self.map[y][x - 1]

            if x == self.WIDTH - 1: right = WALL
            else: right = self.map[y][x + 1]

            if y == 0: up = WALL
            else: up = self.map[y - 1][x]

            if y == self.HEIGHT - 1: down = WALL
            else: down = self.map[y + 1][x]

            if down == AIR:
                self.map[y + 1][x] = SAND
                self.colors[y + 1][x] = alterColor(self.SANDCOLOR, 0.1)

            if left == AIR:
                self.map[y][x - 1] = SAND
                self.colors[y][x - 1] = alterColor(self.SANDCOLOR, 0.1)

            if right == AIR:
                self.map[y][x + 1] = SAND
                self.colors[y][x + 1] = alterColor(self.SANDCOLOR, 0.1)

            if up == AIR:
                self.map[y - 1][x] = SAND
                self.colors[y - 1][x] = alterColor(self.SANDCOLOR, 0.1)

        for cloner in self.waterCloners:
            x, y = cloner

            if x == 0: left = WALL
            else: left = self.map[y][x - 1]

            if x == self.WIDTH - 1: right = WALL
            else: right = self.map[y][x + 1]

            if y == 0: up = WALL
            else: up = self.map[y - 1][x]

            if y == self.HEIGHT - 1: down = WALL
            else: down = self.map[y + 1][x]

            if down == AIR:
                self.map[y + 1][x] = WATER
                self.colors[y + 1][x] = alterColor(self.WATERCOLOR, 0.1)

            if left == AIR:
                self.map[y][x - 1] = WATER
                self.colors[y][x - 1] = alterColor(self.WATERCOLOR, 0.1)

            if right == AIR:
                self.map[y][x + 1] = WATER
                self.colors[y][x + 1] = alterColor(self.WATERCOLOR, 0.1)

            if up == AIR:
                self.map[y - 1][x] = WATER
                self.colors[y - 1][x] = alterColor(self.WATERCOLOR, 0.1)

    def handleDeleters(self):
        for deleter in self.deleters:
            x, y = deleter
            
            canDeleteUp = True
            if y == 0: canDeleteUp = False

            canDeleteLeft = True
            if x == 0: canDeleteLeft = False

            canDeleteRight = True
            if x == self.WIDTH - 1: canDeleteRight = False

            canDeleteDown = True
            if y == self.HEIGHT - 1: canDeleteDown = False

            if canDeleteUp and self.map[y - 1][x] not in [WALL, DELETER]:
                self.map[y - 1][x] = AIR
                self.colors[y - 1][x] = self.BG

            if canDeleteLeft and self.map[y][x - 1] not in [WALL, DELETER]:
                self.map[y][x - 1] = AIR
                self.colors[y][x - 1] = self.BG

            if canDeleteRight and self.map[y][x + 1] not in [WALL, DELETER]:
                self.map[y][x + 1] = AIR
                self.colors[y][x + 1] = self.BG

            if canDeleteDown and self.map[y + 1][x] not in [WALL, DELETER]:
                self.map[y + 1][x] = AIR
                self.colors[y + 1][x] = self.BG
            

    def handleDragging(self):
        x, y = self.dragX, self.dragY
        if self.dragging and self.map[y][x] != self.drawingMode:
            self.map[y][x] = self.drawingMode

            if self.drawingMode == SAND: self.colors[y][x] = alterColor(self.SANDCOLOR, 0.1)
            if self.drawingMode == WATER: self.colors[y][x] = alterColor(self.WATERCOLOR, 0.05)
            if self.drawingMode == WALL: self.colors[y][x] = alterColor(self.WALLCOLOR, 0.1)
            if self.drawingMode == DELETER:
                self.colors[y][x] = alterColor(self.DELETERCOLOR, 0.05)
                self.deleters.append([x, y])

        if self.rightPressed:
            if [self.deleteX, self.deleteY] in self.sandCloners:
                index = self.sandCloners.index([self.deleteX, self.deleteY])
                del self.sandCloners[index]
            if [self.deleteX, self.deleteY] in self.waterCloners:
                index = self.waterCloners.index([self.deleteX, self.deleteY])
                del self.waterCloners[index]
            if [x, y] in self.deleters:
                index = self.deleters.index([x, y])
                del self.deleters[index]
            self.map[self.deleteY][self.deleteX] = AIR
            self.colors[self.deleteY][self.deleteX] = self.BG

        if self.cloneModeOn and self.dragging:
            if self.cloneMode == SAND and self.map[y][x] != SANDCLONER and [x, y] not in self.sandCloners and [x, y] not in self.waterCloners:
                self.map[y][x] = SANDCLONER
                self.colors[y][x] = changeBrightness(alterColor(self.SANDCOLOR, 0.1), -100)
                self.sandCloners.append([x, y])
            if self.cloneMode == WATER and self.map[y][x] != WATERCLONER and [x, y] not in self.sandCloners and [x, y] not in self.waterCloners:
                self.map[y][x] = WATERCLONER
                self.colors[y][x] = changeBrightness(alterColor(self.WATERCOLOR, 0.1), -100)
                self.waterCloners.append([x, y])
                        
    def renderMap(self, previousMap, previousColors):
        for block in self.positions:
            x, y = block
            previousBlock = previousMap[y][x]
            currentBlock = self.map[y][x]

            x1, y1 = x * self.CELLSIZE, y * self.CELLSIZE
            x2, y2 = x1 + self.CELLSIZE, y1 + self.CELLSIZE

            if previousBlock == AIR and currentBlock != AIR:
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline='', fill=self.colors[y][x])
                self.canvas.tag_lower(rect)

            if previousBlock != AIR and currentBlock == AIR:
                blockAtPosition = self.canvas.find_enclosed(x1, y1, x2, y2)
                self.canvas.delete(blockAtPosition)

            if previousBlock != AIR and currentBlock != AIR and previousBlock != currentBlock:
                blockAtPosition = self.canvas.find_enclosed(x1, y1, x2, y2)
                self.canvas.delete(blockAtPosition)
                
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline='', fill=self.colors[y][x])
                self.canvas.tag_lower(rect)

            # John Haggerty from StackOverflow (https://stackoverflow.com/questions/72917837/a-few-minor-problems-with-my-tkinter-sand-simulation)
            if previousBlock == currentBlock and currentBlock not in [AIR, WALL]:
                color1 = previousColors[y][x]
                color2 = self.colors[y][x]

                if color1 != color2:
                    blockAtPosition = self.canvas.find_enclosed(x1, y1, x2, y2)
                    self.canvas.delete(blockAtPosition)
                    
                    rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline='', fill=self.colors[y][x])
                    self.canvas.tag_lower(rect)

        self.canvas.update()

    def frame(self):
        timeBefore = time()
        
        previousMap = deepcopy(self.map)
        previousColors = deepcopy(self.colors)
        if self.playing:
            self.updateParticles()
            self.handleCloners()
            self.handleDeleters()
        self.handleDragging()
        self.renderMap(previousMap, previousColors)

        timeAfter = time()
        calculatedTime = 1 / self.TARGETFPS - (timeAfter - timeBefore)
        if calculatedTime < 1 / self.TARGETFPS: calculatedTime = 1 / self.TARGETFPS
        self.master.after(round(calculatedTime * 1000), self.frame)

if __name__ == '__main__':
    app = Sandbox()
