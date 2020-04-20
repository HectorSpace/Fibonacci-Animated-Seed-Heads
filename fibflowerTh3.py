'''
This prog draws a series of fibonacci styled seedheads using John Zelle's graphic.py lib.
Each seedhead draws from its own thread via a queue so achieving asynchronous or independant movement.
The queued object commands are picked up by the main thread and drawn.
This avoids hitting the Python tkinter GUI with multiple threaded draw commands - which it doesn't seem to like!
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
winWdth = 1000
winHt = 1000

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
    """Defines the seed itself - basically a circle with fill and outline the  same colour. Its attributes:
       How to draw it, move it, delete it
       I don't think John Zelle's graphic.py lib will actually redraw when the colour is changed, nor will it redraw an undrawn object.
    """

    def __init__(self, colour='white', size='5', x=0 , y=0 ):
        #The cart coords of the pos of the seedhead centre on screen
        self.x = x
        self.y = y
        #These are cart coords of pos rel to seedhead centre
        self.dx = 0
        self.dy = 0       
        #Create the basic circle obj at pos x & y on canvas
        self.obj = Circle(Point(x,y),size) 
        self.obj.setFill(colour)
        self.obj.setOutline(colour)

    def set_colour(self, colour):
        self.obj.setFill(colour)
        self.obj.setOutline(colour)

    def move(self, dx, dy): 
        #Move the seed to a new pos rel to previous pos  
        #Maintain rel to centre coords
        self.dx = self.dx + dx
        self.dy = self.dy + dy
        #Graphics.py will add these deltas onto the existing x & y
        #so changing x & y held by Graphics.py
        self.obj.move(dx, dy) 

    def draw(self, dx, dy, gwin):
        #Maintain rel to centre coords
        self.dx= self.dx + dx
        self.dy= self.dy + dy
        #Graphics.py will add these deltas onto the existing x & y
        self.obj.move(dx, dy)
        self.obj.draw(gwin)

    def undraw(self):
        self.obj.undraw()

class SeedClone(Seed):
    def __init__(self, seed, dx, dy, x, y):
        self.obj = seed.obj.clone()
        #The cart coords of the pos of the seedhead centre on screen
        self.x = x
        self.y = y        
        #These are cart coords of pos rel to seedhead centre
        self.dx = dx
        self.dy = dy


###########
class SeedHead():
    """docstring for seedHead"""
    def __init__(self, spec, queue):
        #spec = {'x':x, 'y':y, 'colour': 'white', 'size': 5, 'speed': 0.005, 'seed_count': seeds, 'scale': scale}
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
        self.queue = queue

    def _create_array(self, ary):
        #Create a list of seeds together with their location relative to centre
        #of seedhead
        sml_vec=0
        #Create first seed obj
        seed_shape = Seed(self.seed_colour, self.seed_size, self.x , self.y )
       
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
                seed_angle = seed*360.0*self.phi
                rotPerFrame = math.fmod(seed_angle,360)
                #Translate from polar - vector & rotPerFrame to cartesian - dx, dy
                dx = self._fix(vector * math.cos(dToRads * rotPerFrame))
                dy = self._fix(vector * math.sin(dToRads * rotPerFrame))

                #Used graphic.py clone method but it's probably not faster
                #The SeedClone class stores the cart coords of the rel pos
                #So it would be easy to move the whole head round the screen 
                #or perform some other transforms e.g. scale, rotate etc
                seed2_shape = SeedClone(seed_shape, dx, dy, self.x , self.y )
                ary.append(seed2_shape)

        return ary    
 
    def draw(self, speed, gwin):
        #timer.sleep doesn't give enough time delay range. So i've used time.perf_counter_ns + about 10mSec. Although it needed something to deschedule the thread in the wait
        #loop time.sleep(0.001) with the system tick set to 1mS seems to do this OK!!       
        global user_exit    
        for seed in self.seed_ary:
            args=(seed.dx, seed.dy, gwin)
            self.queue.put((seed.draw, args))
            intervalWait = time.perf_counter_ns() + speed
            while time.perf_counter_ns() < intervalWait:
                time.sleep(0.001)
            if user_exit: break

    def undraw(self, direction, speed):
        global user_exit
        step = -1
        if direction : step = 1
        
        for seed in self.seed_ary[::step] :
            self.queue.put((seed.undraw,))
            intervalWait = time.perf_counter_ns() + speed
            while time.perf_counter_ns() < intervalWait:
                time.sleep(0.001)
            if user_exit: break    

    def _fix(self, no):
        int_no = 0
        if no >= 0:
            int_no = math.floor(no)
        else:
            int_no = math.ceil(no)
        return int_no                 


########################################
class SeedHeadTask1(threading.Thread):
    '''
    The basic fibonacci seedhead thread
    '''

    def __init__(self, spec, queue, gwin, delay):
        threading.Thread.__init__(self)
        self.spec = spec
        self.queue = queue
        self.gwin = gwin
        self.delay = delay

    def run(self):    
        global user_exit
        time.sleep(self.delay)
        while not user_exit:

            seed_head=SeedHead(self.spec, self.queue)
                 
            seed_head.draw(self.spec['speed'], self.gwin)

            direction = False
            seed_head.undraw(direction, self.spec['speed'])
            time.sleep(random.randrange(self.delay,6))        
        del seed_head

class SeedHeadTask2(threading.Thread):
    '''
    A mutable seedhead task that uses random functions to control
    various of its attribs
    '''

    def __init__(self, spec, queue, gwin, delay):
        threading.Thread.__init__(self)
        self.spec = spec
        self.queue = queue
        self.gwin = gwin
        self.delay = delay
        self.rand_size = False
        if self.spec['size'] == 'rand':
            self.rand_size = True

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
 
            seed_head=SeedHead(self.spec, self.queue)
                 
            seed_head.draw(self.spec['speed'], self.gwin)
            
            direction = random.choice([True,False,True])
            seed_head.undraw(direction, self.spec['speed'])

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
    def __init__(self, spec, queue, gwin, delay):
        threading.Thread.__init__(self)
        self.spec = spec
        self.queue = queue
        self.gwin = gwin
        self.delay = delay
        self.x = spec['x']
        self.y = spec['y']
        self.seed_count = spec['seed_count']
        self.rand_size = False
        if self.spec['size'] == 'rand':
            self.rand_size = True        

    def run(self):    
        global user_exit
        global colours
        global head_shape_choices

        time.sleep(self.delay)
        while not user_exit:
            
            self.spec['seed_count'] = random.randrange(100,self.seed_count)
            halfscn = winWdth/2
            self.spec['x'] = self.x + random.randrange((-1*halfscn),halfscn)
            self.spec['y'] = self.y + random.randrange((-1*halfscn),halfscn)
            if self.rand_size : self.spec['size'] =  random.randrange(1, 3)
            
            args=random.choice(colours)
            color = color_rgb(*args)

            self.spec['colour']=color

            seed_head=SeedHead(self.spec, self.queue)
                 
            seed_head.draw(self.spec['speed'], self.gwin)
            
            direction = random.choice([True,False,True])
            seed_head.undraw(direction, self.spec['speed'])

            self.spec['phi']=random.choice(head_shape_choices)
            time.sleep(random.randrange(self.delay))
             
        del seed_head  

########################################
#funcs
def checkBreak(win):
    return (not win.isClosed() and win.checkMouse() == None)        

######################################
def main():
    win = GraphWin('Fibonacci Seed Head Animated Patterns',winWdth,winHt)
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
    seed_spec1 = {'x':x, 'y':y, 'colour': 'white', 'size': 5, 'speed': 10000000, 'seed_count': seeds, 'scale': 0.5, 'phi': Fib_ratio}

    seed_spec2 = {'x':x, 'y':y, 'colour': 'red', 'size': 'rand', 'speed': 1000000, 'seed_count': 900,'scale': 0.01,'phi': Fib_ratio}

    seed_spec3 = {'x':x, 'y':y, 'colour': 'yellow', 'size': 'rand', 'speed': 2000000, 'seed_count': 800,'scale': 0.005,'phi': Fib_ratio}
    
    seed_spec4 = {'x':x, 'y':y, 'colour': 'blue', 'size': 'rand', 'speed': 10000000, 'seed_count': 500,'scale': 0.005,'phi': Fib_ratio}

    seed_spec5 = {'x':x, 'y':y, 'colour': 'blue', 'size': 1, 'speed': 10000000, 'seed_count': 200,'scale': 0.005,'phi': Fib_ratio}
    
    queue1 = queue.Queue()

    # Starting threads for each seed head
    t1=SeedHeadTask1(seed_spec1, queue1, win, 0).start()
    t2=SeedHeadTask2(seed_spec2, queue1, win, 4).start()
    t3=SeedHeadTask2(seed_spec3, queue1, win, 8).start()
    
    t4=SeedHeadRandPosTask3(seed_spec4, queue1, win, 2).start()
    t5=SeedHeadRandPosTask3(seed_spec4, queue1, win, 4).start()
    t6=SeedHeadRandPosTask3(seed_spec4, queue1, win, 6).start()
    t7=SeedHeadRandPosTask3(seed_spec4, queue1, win, 8).start()

    backgnd_seedheads = []

    for t in range(8,20):
        backgnd_seedheads.append(SeedHeadRandPosTask3(seed_spec5, queue1, win, random.choice([1,2,1,3,2,1])).start())
   
    
    
    while checkBreak(win):
        try:
            qargs = queue1.get()
            func=qargs[0]

            if len(qargs) > 1:
                args = qargs[1]
                func(*args)
            else: 
                func()
        except queue.Empty:
            #sleep(0.001) seems to be enough to deshedule the task briefly
            time.sleep(0.001)        
    
    user_exit = True     
            
    if not win.isClosed(): win.close()
    
main()    
