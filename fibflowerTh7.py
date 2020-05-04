'''
This prog draws a series of fibonacci styled seedheads
using John Zelle's graphic.py lib. Each seedhead draws from its own thread
via a queue so achieving asynchronous or independant movement.
The queued object commands are picked up by the main thread and drawn.
This avoids hitting the Python tkinter GUI with multiple threaded
draw commands - which it doesn't seem to like!
SRR 16/04/2020
'''

from graphics import *
import math, random, queue, time, threading, os
#import sys
#sys.setswitchinterval(1)

from ctypes import windll
timeBeginPeriod = windll.winmm.timeBeginPeriod
#set windows system timer to 1mS tick
#So I guess this won't work on a Mac or Linux??
timeBeginPeriod(1)

Fib_ratio = 0.618
Phi = 1.618034 #the inverse of Fib_ratio
#A list of ratios for the patterns
head_shape_choices = [Fib_ratio, 0.45, 0.53, Fib_ratio, 0.57, Fib_ratio, 0.71]

#There are 2Pi Rads in a circle
radsInADegree = math.pi*2/360
dToRads = math.radians(1)
seeds = 700
scale = 0.5
#	1,920 x 1,080
#winWdth = 1920
#winHt = 1080
#       1,280x720
winWdth = 1280
winHt = 720
#winWdth = 1000
#winHt = 1000
centerX = winWdth / 2.0
centerY = winHt / 2.0
mouse_x = 0
mouse_y = 0

draw_control_ary=[]

#A list of colours for seedhead seeds in each iteration
#random.range for r g b doesn't provide enough control over the colours
#Without delving into colour rules...
colours =[(255, 0, 0),
(232, 81, 81),
(237, 142, 142),
(255, 94, 0),
(255, 128, 0),
(255, 191, 0),
(255, 221, 0),
(255, 247, 0),
(238, 255, 0),
(200, 255, 0),
(170, 255, 0),
(132, 255, 0),
(94, 255, 0),
(55, 255, 0),
(13, 255, 0),
(0, 255, 68),
(0, 255, 119),
(0, 255, 221),
(0, 208, 255),
(0, 145, 255),
(0, 85, 255),
(4, 0, 255),
(30, 0, 255),
(76, 0, 255),
(89, 0, 255),
(144, 0, 255),
(166, 0, 255),
(191, 0, 255),
(208, 0, 255),
(212, 0, 255),
(238, 0, 255),
(248, 156, 255),
(255, 0, 170),
(255, 0, 187),
(255, 0, 64),
(255, 143, 171),
(255, 0, 0),
(255, 0, 0),
(238, 255, 212),
(212, 255, 228),
(255, 255, 255),
(255, 255, 255),
(255, 255, 255),
(201, 201, 201),
(168, 168, 168),
(145, 145, 145)]

user_exit = False

#######################################
#Classes

class Seed():
    """Defines the seed itself - basically a circle with fill and outline the
    same colour. Its attributes:
       How to draw it, move it, delete it
       I don't think John Zelle's graphic.py lib will actually redraw when the
       colour is changed, nor will it redraw an undrawn object.
    """
    global winWdth
    global winHt
    global centerX
    global centerY

    def __init__(self, colour='white', size='5', x=0 , y=0, flgt_speed = 0.02 ):
        #The cart coords of the pos of the seedhead centre on screen
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.size = size
        self.radSize = random.randrange(0,1)
        self.flgt_speed = flgt_speed
        #Create the basic circle obj at pos x & y on canvas
        self.obj = Circle(Point(x,y),size)
        #self.obj = Point(x,y)
        self.obj.setFill(colour)
        self.obj.setOutline(colour)
        self.drawState = 0 # 0 = undrawn, 1 = draw, 2 = move, 3 = undraw

    def set_colour(self, colour):
        self.obj.setFill(colour)
        self.obj.setOutline(colour)

    def move(self):
        self.obj.move(self.dx, self.dy)

    def draw(self, gwin):
        self.obj.draw(gwin)
        self.drawState = 2

    def undraw(self):
        self.obj.undraw()
        self.drawState = 4
        
    def motion(self):
        delta = self.radSize * self.flgt_speed
        self.radSize += self.flgt_speed
        self.dx = (self.x - centerX) * delta
        self.dy = (self.y - centerY) * delta
        self.x += self.dx
        self.y += self.dy
        if not self.onscreen():
            self.drawState = 3

    def onscreen(self):
        # check if star is now outside display win
        if (0 > self.x > winWdth or 0 > self.y > winHt):
            return False
        return True

###########
class SeedHead():
    """
    Creates, animates and draws each seedhead
    """
    def __init__(self, spec):
        self.seed_count=spec['seed_count']
        #The cart coords of the pos of the seedhead centre on screen
        self.x=spec['x']
        self.y=spec['y']
        self.seed_size=spec['size']
        self.seed_colour=spec['colour']
        self.scale=spec['scale']
        #The ratio to divide 360 and produce the angle increment for each seed
        self.phi=spec['phi']
        self.seed_ary=self._create_array([])


    def _create_array(self, ary):
        #Create a list of seeds together with their location relative to centre
        #of seedhead
        sml_vec=0
        #Create first seed obj
        for seed in range(1,self.seed_count):
            draw = True
            vector = seed*scale
            middle = 2.0/scale
            #restrict the number of central seeds
            if vector < middle:
                sml_vec += 1
                if sml_vec > middle:
                    draw = False
            if draw:
                seed_angle = seed * 360.0 * self.phi
                rotPerFrame = math.fmod(seed_angle, 360)
                #Translate from polar - vector & rotPerFrame to cartesian - dx, dy
                sx = self.x + self._fix(vector * math.cos(dToRads * rotPerFrame))
                sy = self.y + self._fix(vector * math.sin(dToRads * rotPerFrame))
                #create seed
                ary.append(Seed(self.seed_colour, self.seed_size, sx , sy ))
                #time.sleep(0.01)

        return ary

    def _fix(self, no):
        int_no = 0
        if no >= 0:
            int_no = math.floor(no)
        else:
            int_no = math.ceil(no)
        return int_no

    def draw(self, gwin):
        '''
        Display all seeds marked draw or move
        Delete those marked delete
        '''
        global user_exit
        for seed in self.seed_ary:
            seed.motion()
            if seed.drawState == 1:
                seed.draw(gwin)

            elif seed.drawState == 2:
                seed.move()

            elif seed.drawState == 3:
                seed.undraw()

            if user_exit: break

    def unfoldPattern(self, speed):
        '''
        signal drawn each seed in a timed sequence
        '''
        global user_exit
        self.drawState = 0 # 0 = undrawn, 1 = draw, 2 = move, 3 = undraw
        for seed in self.seed_ary:
            if seed.drawState == 0:
                seed.drawState = 1
                intervalWait = time.perf_counter_ns() + speed
                while time.perf_counter_ns() < intervalWait:
                    time.sleep(0.005)
            if user_exit: break

    def undrawAll(self, speed):
        #undraw all drawn seeds
        global user_exit
        for seed in self.seed_ary:
            if seed.drawState > 0:
                seed.undraw()
                #seed.drawState = 0
            if user_exit: break

    def undraw(self):
        pass

    def foldPattern(self, direction, speed):
        #signal undraw all drawn seeds in a timed sequence
        global user_exit
        step = -1
        if direction : step = 1

        for seed in self.seed_ary[::step] :
            #signal remove drawn or moved seeds
            if seed.drawState == 0:
                seed.drawState = 4
            elif seed.drawState < 3:
                seed.drawState = 3
                intervalWait = time.perf_counter_ns() + speed
                while time.perf_counter_ns() < intervalWait:
                    time.sleep(0.005)
            if user_exit: break


        wait_sync = True
        while wait_sync and not user_exit:
            wait_sync = False
            for seed in self.seed_ary:
                if seed.drawState != 4:
                    wait_sync = True
            time.sleep(0.005)        

########################################
class SeedHeadTask1(threading.Thread):
    '''
    The basic fibonacci seedhead thread
    '''

    def __init__(self, id, spec, delay, seedHeadFuncPointer):
        threading.Thread.__init__(self)
        self.id=id
        self.spec = spec
        self.delay = delay
        self.seedHeadFunc = seedHeadFuncPointer


    def run(self):
        global user_exit
        time.sleep(self.delay)
        while not user_exit:

            seed_head = SeedHead(self.spec)
            self.seedHeadFunc(self.id, seed_head)
            seed_head.unfoldPattern(self.spec['speed'])
            time.sleep(random.randrange(self.delay,6))
            direction = False
            seed_head.foldPattern(direction, self.spec['speed'] * 2)
            time.sleep(random.randrange(self.delay,6))
        del seed_head


class SeedHeadTask2(threading.Thread):
    '''
    A mutable seedhead task that uses random functions to control
    various of its attribs
    '''

    def __init__(self, id, spec, delay, seedHeadFuncPointer):
        threading.Thread.__init__(self)
        self.id=id
        self.spec = spec
        self.delay = delay
        self.rand_size = False
        if self.spec['size'] == 'rand':
            self.rand_size = True
        self.seedHeadFunc = seedHeadFuncPointer

    def run(self):
        global user_exit
        global colours
        global head_shape_choices

        time.sleep(self.delay)
        while not user_exit:

            args=random.choice(colours)
            color = color_rgb(*args)
            self.spec['colour']=color

            if self.rand_size : self.spec['size'] =  random.randrange(1, 8)

            seed_head=SeedHead(self.spec)
            self.seedHeadFunc(self.id, seed_head)
            seed_head.unfoldPattern(self.spec['speed'])

            direction = random.choice([True,False,True])
            seed_head.foldPattern(direction, self.spec['speed'])

            self.spec['phi']=random.choice(head_shape_choices)
            time.sleep(random.randrange(self.delay))

        del seed_head

class SeedHeadRandPosTask3(threading.Thread):
    '''
    A mutable seedhead task that uses random functions to control
    various of its attribs including position and seed_count
    '''
    global winWdth
    global winHt
    def __init__(self, id, spec, delay, seedHeadFuncPointer):
        threading.Thread.__init__(self)
        self.id=id
        self.spec = spec
        self.delay = delay
        self.x = spec['x']
        self.y = spec['y']
        self.seed_count = spec['seed_count']
        self.rand_size = False
        if self.spec['size'] == 'rand':
            self.rand_size = True
        self.seedHeadFunc = seedHeadFuncPointer

    def run(self):
        global user_exit
        global colours
        global head_shape_choices

        time.sleep(self.delay)
        while not user_exit:

            self.spec['seed_count'] = random.randrange(20,self.seed_count)
            halfscn = winWdth/2
            self.spec['x'] = self.x + random.randrange((-1*halfscn),halfscn)
            self.spec['y'] = self.y + random.randrange((-1*halfscn),halfscn)
            if self.rand_size : self.spec['size'] =  random.randrange(1, 2)

            new_speed = random.randrange(self.spec['speed']/10,self.spec['speed'])

            args=random.choice(colours)
            color = color_rgb(*args)

            self.spec['colour']=color

            seed_head=SeedHead(self.spec)

            self.seedHeadFunc(self.id, seed_head)

            seed_head.unfoldPattern(new_speed)

            direction = random.choice([True,False,True])
            new_speed = random.randrange(self.spec['speed']/10,self.spec['speed'])
            seed_head.foldPattern(direction, new_speed)

            self.spec['phi']=random.choice(head_shape_choices)
            time.sleep(random.randrange(self.delay))

        del seed_head
#######################################
#Classes
'''
The star field is a set of randomly positioned lines, created
in each frame by joining the previous end point to a new point
calculated by simply multplying the previous end coords by a constant
flight_speed
''' 

class Star():
    '''
    A class for creating, maintaining and killing each star 
    '''
    def __init__(self,winWdth,winHt,gwin,queue,size,a_colour):
        self.colour = a_colour
        self.gwin = gwin
        self.queue = queue
        self.restart(winWdth,winHt,size)
        
    # When the star has left the window.. Restart it with this    
    def restart(self,winWdth,winHt,size):
        self.x = random.randrange(0,winWdth)
        self.y = random.randrange(0,winHt)
        self.start = Point(self.x,self.y) 
        self.size = random.randrange(0,size)

    def draw(self):
        #create coords for line end
        self.end = Point(self.x,self.y)
        #Adjust star colour alpha according to size
        star_colour = color_rgb(*self._colour_scale(self.colour, min(self.size, 1)))
        #star_colour = color_rgb(255,255,255)
        self.starObj = Line(self.start,self.end)
        #self.starObj.setFill(star_colour)
        self.starObj.setOutline(star_colour)
        args=(self.gwin,)
        self.queue.put((self.starObj.draw, args))
        #The equivalent in an unthreaded sys :self.starObj.draw(self.gwin)

        #update Point object of start of line for next draw
        self.start = self.end.clone()
 
    def undraw(self):
        self.queue.put((self.starObj.undraw,))
        #The equivalent in an unthreaded sys : self.starObj.undraw()

    # There is no alpha in Graphics.py. This method provides a rough equivalent
    # to the JS r,g,b,alpha   
    def _colour_scale(self, colour, alpha):
        return (tuple([math.floor(clr * alpha) for clr in colour]))           

class StarField(threading.Thread):
    """Animated star field from original js code by sebi@timewaster.de

    """
    global user_exit        
    global winWdth
    global winHt    
    global centerX
    global centerY

    def __init__(self, frame_rate, star_density, flight_speed, queue, gwin, delay):
        threading.Thread.__init__(self)
        self.frame_rate = frame_rate
        self.no_of_stars = int(winWdth * winHt / 1000 * star_density)
        self.flgt_speed = flight_speed
        self.queue = queue        
        self.gwin = gwin
        self.delay = delay
        self.colour=(255,255,255)
        self.stars = []
        #Build list of stars - starfield
        for star in range(self.no_of_stars):
            self.stars.append(Star(winWdth,winHt,self.gwin,self.queue,1,self.colour))


    def run(self):
        #while not user_exit:
        for star in self.stars:
            #calc new position and size
            #Al star paths expand in x&y at size*flgt_speed
            #This uses the neat trick of assuming no star will hit us!
            star.x += (star.x - centerX) * star.size * self.flgt_speed
            star.y += (star.y - centerY) * star.size * self.flgt_speed
            star.size += self.flgt_speed

            # check if star is now outside display win
            if (star.x < 0 or star.x > winWdth or star.y < 0 or star.y > winHt):
                star.restart(winWdth,winHt,1)

            star.draw()
            if user_exit: break

        time.sleep(1.0/self.frame_rate)
        for star in self.stars:
            star.undraw()
            if user_exit: break

########################################
class MouseGrapWin(GraphWin):
    """This extends GraphWin to provide mouse x y without click"""
    def __init__(self, *args):
        super(MouseGrapWin, self).__init__(*args)
        self.bind('<Motion>', self._mmotion)
        self.mouse_x = 0
        self.mouse_y = 0         

    def _mmotion(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y 

    def mouse_xy(self):
        return(self.mouse_x, self.mouse_y)      



########################################
#funcs
def fix(no):
    int_no = 0
    if no >= 0:
        int_no = math.floor(no)
    else:
        int_no = math.ceil(no)
    return int_no

def checkBreak(win):
    return (not win.isClosed() and win.checkMouse() == None)

def drawControl(task_id, drawn_obj):
    for dc in draw_control_ary:
        if dc[0] == task_id:
            dc[1] = drawn_obj
            break
    else:
        draw_control_ary.append([task_id,drawn_obj])

def mousePos(win):
    #Get the current mouse position and update the star field center
    global centerX
    global centerY
    global mouse_x
    global mouse_y

    mouse_x,mouse_y = win.mouse_xy()
    centerX = mouse_x
    centerY = mouse_y        

######################################
def main():
    win = MouseGrapWin('Fibonacci Seed Head Animated Patterns',winWdth,winHt)
    win.setBackground('black')
    message = Text(Point(win.getWidth()-200, win.getWidth()-10), 'Fibonacci Seed Head - SRRose, Romanviii.co.uk')
    message.setFace('arial')
    #message.setStyle('bold')
    message.setTextColor('white')
    message.draw(win)

    global user_exit
    #Wait for user to click
    click_msg = Text(Point((win.getWidth()/2)-30, win.getWidth()/2), 'Click Mouse To Start!')
    click_msg.setFace('arial')
    click_msg.setTextColor('white')
    click_msg.draw(win)

    while checkBreak(win): time.sleep(0.2)

    click_msg.undraw()

    x = winWdth/2.0
    y = winHt/2.0

    user_exit = False

    #Seedhead specification dicts for the 3 heads to be drawn
    seed_spec1 = {'x':x, 'y':y, 'colour': 'white', 'size': 3,
    'speed': 1000000, 'seed_count': 500, 'scale': 0.5, 'phi': Fib_ratio}

    seed_spec2 = {'x':x, 'y':y, 'colour': 'red', 'size': 'rand',
    'speed': 1000000, 'seed_count': 900,'scale': 0.01,'phi': Fib_ratio}

    seed_spec3 = {'x':x, 'y':y, 'colour': 'yellow', 'size': 'rand',
    'speed': 2000000, 'seed_count': 800,'scale': 0.005,'phi': Fib_ratio}

    seed_spec4 = {'x':x, 'y':y, 'colour': 'blue', 'size': 'rand',
    'speed': 10000000, 'seed_count': 500,'scale': 0.005,'phi': Fib_ratio}

    seed_spec5 = {'x':x, 'y':y, 'colour': 'blue', 'size': 1,
    'speed': 50000000, 'seed_count': 250,'scale': 0.5,'phi': Fib_ratio}

    queue1 = queue.Queue()

    # Starting threads for each seed head

    #t1=SeedHeadTask1(1,seed_spec1, 0, drawControl).start()
   
    #t2=SeedHeadTask2(2,seed_spec2, 4, drawControl).start()
    t3=SeedHeadTask2(3,seed_spec3, 8, drawControl).start()

    #t4=SeedHeadRandPosTask3(4,seed_spec4, 2, drawControl).start()
    #t5=SeedHeadRandPosTask3(5,seed_spec4, 4, drawControl).start()
    t6=SeedHeadRandPosTask3(6,seed_spec4, 6, drawControl).start()
    t7=SeedHeadRandPosTask3(7,seed_spec4, 8, drawControl).start()

    backgnd_seedheads = []

    for t in range(8,15):
        backgnd_seedheads.append(SeedHeadRandPosTask3(t,seed_spec5, random.choice([1,2,1,3,2,1]), drawControl).start())
    #st1 = StarField(30, 0.07, 0.02, queue1, win, 2).start()

    while checkBreak(win):
        for task in draw_control_ary:
            task[1].draw(win)
        for task in draw_control_ary:
            task[1].undraw()
        time.sleep(0.01)
        #Update starfield center with mouse position    
        mousePos(win)          

    user_exit = True

    if not win.isClosed(): win.close()

main()
