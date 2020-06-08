'''
This prog draws a series of seedheads including those based on fibonacci numbers.
This is now done on a backdrop of a starfield
Graphics is via John Zelle's graphic.py lib.
For independence of motion, the starfield and seedhead objects are run in separate threads.
Each thread provides the main thread with a draw routine and semaphore to sync the object's
output with the graphics library draw control interface. So the main thread does all the drawing.

Updated 06/06/2020
Now includes an embrionic automatic sequencer to provide a means of globally controlling the 
sequence of events. 
This throttles back or promotes individual tasks to suit different scenes.

Updated 2/06/2020
Smoothed starfield animation by fitting undraw and draw into the same frame.
Used win.autoflush to control when screen updates are done in cycle. This
massively improves PC framerate performance now running pretty soomthly at 30Hz
Dampened starfield boost in lull period.. It was too leary!
Fixed star flicker when size was a dot, by drawing a point for stars less than 2 in size
and morphing to a line for larger.
Fixed various sync problems with fast seedheads not being completely drawn before being
folded up.

SRR 16/04/2020
Original seedhead threaded code.
'''

from graphics import *
import math, random, time, threading, os


#import sys
sys.setswitchinterval(1)

from ctypes import windll
timeBeginPeriod = windll.winmm.timeBeginPeriod
#set windows system timer to 1mS tick

timeBeginPeriod(1)
slug_factor = 1.5
frameTime = 0.02 * slug_factor
flight_period_const = 0.3/slug_factor
lull_period_const = 1
lull_period = lull_period_const
lull_increment = 0.004
lull_decrement = 0.004
star_density = 0.04 

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
winWdth = 1920
winHt = 1080
#       1,280x720
#winWdth = 1280
#winHt = 720
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

    def __init__(self, colour='white', size='5', x=0 , y=0):
        #The cart coords of the pos of the seedhead centre on screen
        self.x = x
        self.y = y
        #Change in position for move()
        self.dx = 0
        self.dy = 0
        self.size = size
        self.radSize = 0.001 #Virtual seed radius
        self.flgt_time = time.time()
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

    def undraw(self):
        self.obj.undraw()

    def motion(self, flight_speed):
        #Calc how long the seed has flown since last update
        flight_period = (time.time() - self.flgt_time)
        flight_period *= flight_speed
        self.flgt_time = time.time()
        delta = self.radSize * flight_period
        self.radSize += flight_period
        #Create delta move
        self.dx = (self.x - centerX) * delta
        self.dy = (self.y - centerY) * delta
        #Update seed screen position 
        self.x += self.dx
        self.y += self.dy

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
    global frameTime
    global flight_period_const
    
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
        self.motion = spec['motion']
        self.seed_ary=self._create_array([])
        self.flight_speed = random.random() * flight_period_const
        self.mutate = random.random() < 0.5


    def _create_array(self, ary):
        #Create a list of seeds together with their location relative to centre
        #of seedhead
        sml_vec=0
        #Create first seed obj
        for seed in range(1,self.seed_count):
            start = time.time()
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
                #Offset from seedhead coords
                sx = self.x + self._fix(vector * math.cos(dToRads * rotPerFrame))
                sy = self.y + self._fix(vector * math.sin(dToRads * rotPerFrame))
                #create seed
                ary.append(Seed(self.seed_colour, self.seed_size, sx , sy ))
                end = time.time()
                frameTimer(start,end, 1)

        return ary

    def _fix(self, no):
        #Maths for int nearest zero either + or -
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

            if self.motion :
                #Make this random it changes the dynamic shape!
                if seed.drawState == 0 and not self.mutate :
                    seed.flgt_time = time.time() #start flight period timer

                seed.motion(self.flight_speed)

            if not seed.onscreen():
                seed.drawState = 3
                
            if seed.drawState == 1:
                seed.draw(gwin)
                seed.drawState = 2

            elif seed.drawState == 2:
                seed.move()

            elif seed.drawState == 3:
                seed.undraw()
                seed.drawState = 4                

            if user_exit: break


    def unfoldPattern(self, direction, speed):
        '''
        signal drawn each seed in a timed sequence
        '''
        global user_exit
        global frameTime
        self.drawState = 0 # 0 = undrawn, 1 = draw, 2 = move, 3 = undraw

        step = -1
        if direction : step = 1
        
        for seed in self.seed_ary[::step]:
            if seed.drawState == 0:
                seed.drawState = 1
                time.sleep(frameTime * speed)
            if user_exit: break

        #Wait for all seeds to be drawn or off screen    
        wait_sync = True
        while wait_sync and not user_exit:
            wait_sync = False
            for seed in self.seed_ary:
                if seed.drawState == 1:
                    wait_sync = True
    
            time.sleep(frameTime)

    def undrawAll(self, speed):
        #undraw all drawn seeds
        global user_exit
        for seed in self.seed_ary:
            if seed.drawState > 0:
                seed.undraw()
                seed.drawState = 0
            if user_exit: break

    def undraw(self):
        pass

    def foldPattern(self, direction, speed):
        #signal undraw all drawn seeds in a timed sequence
        global user_exit
        global frameTime
        step = -1
        if direction : step = 1

        for seed in self.seed_ary[::step] :
            #signal remove drawn or moved seeds
            if seed.drawState == 0:
                seed.drawState = 4
            elif seed.drawState < 3:
                seed.drawState = 3
                time.sleep(frameTime * speed)
            if user_exit: break

        #Wait for seeds to be all undrawn
        wait_sync = True
        #wait_ctr = 0
        #seed_error = 4
        while wait_sync and not user_exit:
            wait_sync = False
            for seed in self.seed_ary:
                if seed.drawState != 4:
                    #seed_error = seed.drawState
                    wait_sync = True
            #wait_ctr += 1        
            time.sleep(frameTime)
        #return(wait_ctr, seed_error)   

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
        #setup task controller interface
        self.seqr = Sequencer()
        #Configure the generator sync controller
        self.taskController = self.seqr.taskControlGen(self.id)        


    def run(self):
        global user_exit
        time.sleep(self.delay)
        while not user_exit:
            seed_head = SeedHead(self.spec)
            #setup drawing interface
            self.seedHeadFunc(self.id, seed_head)
            seed_head.unfoldPattern(True, self.spec['speed'])
            time.sleep(random.randrange(self.delay,6))
            direction = False
            seed_head.foldPattern(direction, self.spec['speed'] * 2)
            time.sleep(random.random() * (frameTime*self.delay*600))
            del seed_head
            #Signal remove seedHead from drawing list
            self.seedHeadFunc(self.id, None)
            #Sync task to main event sequence
            try:
                next(self.taskController)
            except StopIteration:
                pass            
        try:
            del seed_head
        except NameError:
            pass
#......................... 

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
        #setup task controller interface
        self.seqr = Sequencer()
        #Configure the generator sync controller
        self.taskController = self.seqr.taskControlGen(self.id)        

    def run(self):
        global user_exit
        global colours
        global head_shape_choices
        self.loop_ctr = 0        

        time.sleep(self.delay)
        while not user_exit:

            args=random.choice(colours)
            color = color_rgb(*args)
            self.spec['colour']=color

            self.spec['motion'] = random.choice([True,False,True])

            if self.rand_size : self.spec['size'] =  random.randrange(1, 4)

            seed_head=SeedHead(self.spec)
            #Setup drawing interface
            self.seedHeadFunc(self.id, seed_head)
            seed_head.unfoldPattern(True, self.spec['speed'])

            direction = random.choice([True,False,True])
            seed_head.foldPattern(direction, self.spec['speed'])

            self.spec['phi']=random.choice(head_shape_choices)

            self.loop_ctr+=1 
            #Sync task to main event sequence
            try:
                next(self.taskController)
            except StopIteration:
                pass                 
            print(f"Task 2 a id = {self.id} run={self.loop_ctr}")

            time.sleep(random.random() * (frameTime*self.delay*100))
            del seed_head
            #Signal remove seedHead from drawing list
            self.seedHeadFunc(self.id, None)
            try:
                next(self.taskController)
            except StopIteration:
                pass              
            print(f"Task 2 b id = {self.id} run={self.loop_ctr}")

        try:
            del seed_head
        except NameError:
            pass
#......................... 
class SeedHeadRandPosTask3(threading.Thread):
    '''
    An even more mutable seedhead task that uses random functions to control
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
        #setup task controller interface
        self.seqr = Sequencer()
        #Configure the generator sync controller
        self.taskController = self.seqr.taskControlGen(self.id)
     

    def run(self):
        global user_exit
        global colours
        global head_shape_choices
        self.loop_ctr = 0

        time.sleep(self.delay)
        while not user_exit:

            self.spec['seed_count'] = random.randrange(20,self.seed_count)
            halfscnwd = (winWdth/2) - 100
            halfscnht = (winHt/2) - 80
            self.spec['x'] = self.x + random.randrange((-1*halfscnwd),halfscnwd)
            self.spec['y'] = self.y + random.randrange((-1*halfscnht),halfscnht)
            if self.rand_size : self.spec['size'] =  random.randrange(1, 2)
            topspeed = int(self.spec['speed'] * 100) + 10
            bspeed = topspeed - 5
            new_speed = random.randrange(bspeed,topspeed)/100

            args=random.choice(colours)
            color = color_rgb(*args)

            self.spec['colour']=color
            self.spec['motion']= random.choice([True,False,True])

            seed_head=SeedHead(self.spec)
            direction = random.choice([True,False,True,True])

            #Setup drawing interface
            self.seedHeadFunc(self.id, seed_head)

            seed_head.unfoldPattern(direction, new_speed)

            direction = random.choice([True,False,True])
            #topspeed = int(self.spec['speed'] * 100) + 10
            #bspeed = topspeed - 5
            new_speed = random.randrange(bspeed,topspeed)/100
            #ctr, seed_state =
            seed_head.foldPattern(direction, new_speed)

            self.spec['phi']=random.choice(head_shape_choices)

            #Sync task to main event sequence
            try:
                next(self.taskController)
            except StopIteration:
                pass
            
            time.sleep(random.random() * (frameTime*self.delay*100))
            
            del seed_head
            #Signal remove seedHead from drawing list
            self.seedHeadFunc(self.id, None)
            self.loop_ctr+=1

            #Sync task to main event sequence
            try:
                next(self.taskController)
            except StopIteration:
                pass
            
            #self.seqr.taskControl(self.id)

            #print(f"Task 3 id = {self.id} run={self.loop_ctr}")

        try:
            del seed_head
        except NameError:
            pass
        


        
#######################################
#Star Field Classes
'''
The star field is a set of randomly positioned points/lines, created
in each frame by joining the previous end point to a new point
calculated by simply multplying the previous end coords by a constant
flight_period
'''

class Star():
    '''
    A class for creating, maintaining and killing each star
    '''
    global winWdth
    global winHt
    
    #Class variables
    s_warp = False
    
    def __init__(self,size,a_colour):
        self.colour = a_colour
        self.restart(size)

    # When the star has left the window.. Restart it with this
    def restart(self,size):
        #set star origin
        self.x = random.randrange(0,winWdth)
        self.y = random.randrange(0,winHt)
        #get the first point of the line
        self.start = Point(self.x,self.y)
        self.size = random.random() * size
        if Star.s_warp :
            self.colour = random.choice(colours)
        else:
            self.colour = (255,255,255) 

    def draw(self,gwin):
        #create coords for line end
        self.end = Point(self.x,self.y)
        
        #Adjust star colour alpha according to size
        star_colour = color_rgb(*self._colour_scale(self.colour, min(self.size/2, 1)))
        
        #is it still too small for a line?
        if self.size > 2 :
            self.starObj = Line(self.start,self.end)
        else: self.starObj = self.end    

        self.starObj.setFill(star_colour)
        #self.starObj.setOutline(star_colour)
        self.starObj.draw(gwin)


        #update Point object of start of line for next draw
        self.start = self.end.clone()

    def undraw(self):
        self.starObj.undraw()


    # There is no alpha in Graphics.py. This method provides a rough equivalent
    # to the JS r,g,b,alpha
    def _colour_scale(self, colour, alpha):
        return (tuple([math.floor(clr * alpha) for clr in colour]))
#......................... 
class StarField():
    global user_exit
    global winWdth
    global winHt

    def __init__(self,star_density):
        #Keeping the number of stars about 20 as processing is slow 
        self.no_of_stars = int(winWdth * winHt / 1000 * star_density)
        self.starFieldControl = 0
        self.starFieldDrawn = False
        self.colour=(255,255,255)
        self.stars = []
        #Build list of stars - starfield
        for star in range(self.no_of_stars):
            self.stars.append(Star(1,self.colour))

    def draw(self, gwin):
        if self.starFieldControl == 1:
            #Dodge the not drawn yet gotcha
            if self.starFieldDrawn :
                for star in self.stars:
                    star.undraw()
                    if user_exit: break
                    
            for star in self.stars:
                star.draw(gwin)
                if user_exit: break
            self.starFieldDrawn = True
            #signal new cycle            
            self.starFieldControl = 0
            
    def undraw(self):
        pass
#......................... 

class StarFieldTask(threading.Thread):
    """Animated star field from original js code by sebi@timewaster.de

    """
    global user_exit
    global winWdth
    global winHt
    global centerX
    global centerY
    global slug_factor
    global lull_period
    
    #Class variable
    sft_warp = False

    def __init__(self, id, star_density, gwin, delay, starFieldFuncPtr):
        threading.Thread.__init__(self)
        self.delay = delay
        self.id = id
        self.starFieldFunc = starFieldFuncPtr
        self.star_field = StarField(star_density)
        self.starFieldFunc(self.id, self.star_field)
        #setup task controller interface
        self.seqr = Sequencer()        

    def run(self):
        '''
        starFieldControl
        0 = update
        1 = updated
        2 = drawn
        '''
        flight_period = 0.01
        line_length_adjust = 0.5
        
        while not user_exit:
            #Setup Star class var
            Star.s_warp = StarFieldTask.sft_warp
            start = time.time()
            if StarFieldTask.sft_warp :
                #line_length_adjust = 1
                if flight_period < 0.25:
                    flight_period *= 1.01
            else:
                if flight_period > 0.01:
                    flight_period /= 1.1
                #line_length_adjust = 0.5
            				
            line_length = flight_period * lull_period
            
            for star in self.star_field.stars:
                #calc new position and size
                #Al star paths expand in x&y at size*flight_period
                #This assumes no star will hit us!
                star.x += (star.x - centerX) * star.size * line_length * line_length_adjust
                star.y += (star.y - centerY) * star.size * line_length * line_length_adjust
                star.size += line_length
                # check if star is now outside display win
                if (star.x < 0 or star.x > winWdth or star.y < 0 or star.y > winHt):
                    star.restart(1)

                if user_exit: break
                    
            end = time.time()
            frameTimer(start,end, 1)
            #Signal ready to draw
            self.star_field.starFieldControl = 1
            #Wait till drawn
            while not user_exit and self.star_field.starFieldControl != 0:
                time.sleep(0.0001)
                
#########################################
class Sequencer():
    '''
    A class to provide global, indirect control of threaded tasks. 
    Both main and tasks use this class as a means of synchronising
    events.
    '''

    global user_exit

    #shared variables
    task_ctl_dict = {}
    c_warped = False

    
    def __init__(self):
        self.start_time = time.time()
        self.warp_lapse_time = time.time() + self.get_warp_time()
        self.tick_done = True
        self.dodge_warp = 0
        self.set_dodge_warp()

    def addTaskToDict(self, task_id, task_data):
        #Used by the main task to setup the references in the control dict
        #For all tasks. 
        try:
            Sequencer.task_ctl_dict[task_id] = task_data
        except:
            pass
        #setup pause control
        self.setTaskCtlDict(task_id, False, 4)
            
    def setTaskCtlDict(self, task_id, pause_state, delay):
        #Sets up the sync control for a task
        try:
            Sequencer.task_ctl_dict[task_id]['pause'] = pause_state
            Sequencer.task_ctl_dict[task_id]['delay'] = delay
            Sequencer.task_ctl_dict[task_id]['paused'] = False            
        except:
            Sequencer.task_ctl_dict[task_id]={'pause': pause_state, 'delay':delay, 'paused': False}         
  
    def getTaskFromDict(self, task_id):
        pass

    def checkForWarp(self):
        #Is the current warp period over
        if self.warp_lapse_time <= time.time():
            return True
        return False

    def pause_task(self, delay):
        #Signal tasks to pause
        #Set up the pause 'tick' in seconds and control flag for each task 
        for t in Sequencer.task_ctl_dict :
            self.setTaskCtlDict(t, True, delay)

    def flag_pause_task(self, pause_state):
        #task pause flag set
        for val in Sequencer.task_ctl_dict.values() :
            val['pause'] = pause_state            
    
    def sequenceControl(self):
        '''
        Control the warp sequence
        '''
        if self.checkForWarp():
            if Sequencer.c_warped :
                #Clear the task pauses
                self.flag_pause_task(False)
                #Clear the seq Warp Flag
                Sequencer.c_warped = False
                #Turn off starfield warp
                StarFieldTask.sft_warp = False
                #Set the none warp length
                self.set_warp_lapse_time(self.get_warp_time())
                self.set_dodge_warp()
                
            elif not Sequencer.c_warped:
                #either dodge warp, wait for task 3 to pause and setup warp
                if self.dodge_warp > 0:
                    self.set_warp_lapse_time(self.get_warp_time())
                    self.dodge_warp-=1
                    print(f"Warp: dodge={self.dodge_warp}")
                elif Sequencer.task_ctl_dict[3]['paused'] == False:
                    #setup the sync
                    self.setTaskCtlDict(3, True, 8)
                    self.set_warp_lapse_time(2)
                else:
                    #Task 3 is paused so set the warp signal  
                    Sequencer.c_warped = True
                    #Signal all tasks to be paused
                    self.tick_done = False
                    #Allow 30 sec for the warp to start
                    self.set_warp_lapse_time(30)
                    print(f"Warp:Task 3 paused waiting 30sec for sync")
        else:
            #So not a warp period end but if a new warp is flagged and the
            #Other tasks are not paused, Setup the Starfield warp and task pause
            if Sequencer.c_warped and self.tick_done == False:
                if Sequencer.task_ctl_dict[3]['paused']:
                    #print(f"here2!{Sequencer.task_ctl_dict[3]['paused']}")
                    StarFieldTask.sft_warp = True            
                    #Create the base 'tick' in seconds for each task
                    #To poll for the next operational period
                    self.pause_task(8)
                    self.tick_done = True
                    #Set the actual warp length
                    self.set_warp_lapse_time(self.get_warp_time())
                    print(f"Warp:{Sequencer.c_warped} time:{self.warp_lapse_time}")
                    
    def set_dodge_warp(self):
        if self.dodge_warp == 0:
            self.dodge_warp = random.randint(4, 12)

    def set_warp_lapse_time(self, lapse):
        self.pause_lapse_time = time.time()
        self.warp_lapse_time = time.time() + lapse 

    def get_warp_time(self):
    	#Provides a range of periods in seconds for warp
        #return random.choice([30, 6, 10, 50, 20, 40])
        return random.choice([21, 20, 23, 18, 25])
        #return(25)

    def taskControl(self, task_id):
    	#When in a warp period this controller holds all
    	#Signalled tasks, back. Warp status is polled at the
    	#Tick rate set for each task. 
        
        t = Sequencer.task_ctl_dict[task_id]
        #print(f"task: {task_id} warped: {Sequencer.c_warped}")
        ctr=0
        while Sequencer.c_warped and t['pause']:
            t['paused'] = True        	
            time.sleep(t['delay'])
            ctr+=1
        #print(f"task paused:{task_id} by ctr {ctr} x {t['delay']}")
        #t['pause'] = False
        t['paused'] = False        

    def taskControlGen(self, task_id):
    	#This is a generator version of the task sync controller above.
        while not user_exit :
            ctr=0
            t = Sequencer.task_ctl_dict[task_id]
            while(Sequencer.c_warped or task_id == 3) and t['pause']:
                t['paused'] = True
                time.sleep(t['delay'])
                ctr+=1
            #print(f"task paused:{task_id} by ctr {ctr} x {t['delay']}")
            #t['pause'] = False
            t['paused'] = False
            yield    

########################################
class MouseGrapWin(GraphWin):
    """
        This extends GraphWin to provide mouse x y without click
        It gets rid of the title bar and positions the window top left
    """
    global winWdth
    global winHt    
    def __init__(self, *args):
        super(MouseGrapWin, self).__init__(*args)

        # Get the screen which contains top
        w, h = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        print(f"Screen width {w} Screen height {h}")
        #Set window display to actual screen size and position the window top left
        self.master.geometry(f"{w}x{h}+0+0")
        winWdth = w
        winHt = h
        
        #Hide Titlebar
        self.master.wm_overrideredirect(True)
        #Make sure you've got control
        self.master.focus_force() 
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
#......................... 

def checkBreak(win):
    return (not win.isClosed() and win.checkMouse() == None)
#......................... 

def drawControl(task_id, drawn_obj):
    if drawn_obj == None:
        for dc in draw_control_ary:
            if dc[0] == task_id:
                draw_control_ary.remove(dc)
            break
    else:
        for dc in draw_control_ary:
            if dc[0] == task_id:
                dc[1] = drawn_obj
                break
        else:
            draw_control_ary.append([task_id,drawn_obj])
            
#.........................
            
def mousePos(win):
    #Get the current mouse position and update the star field center
    global centerX
    global centerY
    global mouse_x
    global mouse_y
    global lull_period
    
    #Commented out for videoing coz I don't want the
    #mouse cursor in the display center
    mouse_x,mouse_y = win.mouse_xy()
    centerX = mouse_x
    centerY = mouse_y

    #centerX = (winWdth / 2.0) + 2
    #centerY = (winHt / 2.0) + 1
#......................... 

def frameTimer(start, end, frames):
    global lull_period
    draw_time= end - start
    time_given = frameTime*frames
    time_left = time_given-draw_time

    if time_left > 0:
        time.sleep(time_left)
  
    else:
        time.sleep(0.001)
#.........................         

def mainFrameTimer(start, end, frames):
    global lull_period
    draw_time= end - start
    time_given = frameTime*frames
    time_left = time_given-draw_time

    if time_left > 0:
        if draw_time <= (time_given * 0.2):
            lull_period += lull_increment
        elif lull_period > (lull_period_const + lull_decrement) :
            lull_period -= lull_decrement
           
        time.sleep(time_left)
        return(False,time_left)    
    else:
        if lull_period > lull_period_const:
           lull_period -= lull_decrement
        time.sleep(0.001)
        return(True,time_left)
      
######################################
def main():
    win = MouseGrapWin('Starfield and Fibonacci Seedhead Animated Patterns',winWdth,winHt)
    win.setBackground('black')
    message = Text(Point(win.getWidth()-200, win.getWidth()-10), 'Fibonacci Seed Head - SRRose, Romanviii.co.uk')
    message.setFace('arial')
    #message.setStyle('bold')
    message.setTextColor('white')
    message.draw(win)

    global user_exit
    global frameTime
    
    #Wait for user to click
    click_msg = Text(Point((win.getWidth()/2)-30, win.getWidth()/2), 'Click Mouse To Start & End!')
    click_msg.setFace('arial')
    click_msg.setTextColor('white')
    click_msg.draw(win)

    while checkBreak(win): time.sleep(0.2)

    click_msg.undraw()

    x = winWdth/2.0
    y = winHt/2.0

    user_exit = False

    #Setup Sequencer
    sequencer = Sequencer()
    

    #Seedhead specification dicts for the 3 heads to be drawn
    seed_spec1 = {'x':x, 'y':y, 'colour': 'white', 'size': 3,
    'speed': 2, 'seed_count': 500, 'scale': 0.5,
                  'phi': Fib_ratio, 'motion':False}

    seed_spec2 = {'x':x, 'y':y, 'colour': 'red', 'size': 'rand',
    'speed': 2, 'seed_count': 900,'scale': 0.01,
                  'phi': Fib_ratio, 'motion':True}

    seed_spec3 = {'x':x, 'y':y, 'colour': 'yellow', 'size': 'rand',
    'speed': 2, 'seed_count': 800,'scale': 0.005,
                  'phi': Fib_ratio, 'motion':True}

    seed_spec4 = {'x':x, 'y':y, 'colour': 'blue', 'size': 'rand',
    'speed': 0.5, 'seed_count': 500,'scale': 0.005,
                  'phi': Fib_ratio, 'motion':True}

    seed_spec5 = {'x':x, 'y':y, 'colour': 'blue', 'size': 1,
    'speed': 1, 'seed_count': 250,'scale': 0.5,
                  'phi': Fib_ratio, 'motion':False}

    # Starting threads for each seed head

    #t1=SeedHeadTask1(1,seed_spec1, 0, drawControl).start()

    #t2=SeedHeadTask2(2,seed_spec2, 4, drawControl).start()
    
    t3=SeedHeadTask2(3,seed_spec3, 8, drawControl).start()
    sequencer.addTaskToDict(3, {'task' : t3})

    #t4=SeedHeadRandPosTask3(4,seed_spec4, 2, drawControl).start()
    #t5=SeedHeadRandPosTask3(5,seed_spec4, 4, drawControl).start()
    
    t6=SeedHeadRandPosTask3(6,seed_spec4, 6, drawControl).start()
    sequencer.addTaskToDict(6, {'task' : t6})
    
    t7=SeedHeadRandPosTask3(7,seed_spec4, 8, drawControl).start()
    sequencer.addTaskToDict(7, {'task' : t7})

    for t in range(8,15):
        tsk =SeedHeadRandPosTask3(t,seed_spec5, random.choice([1,2,1,3,2,1]), drawControl).start()
        sequencer.addTaskToDict(t, {'task' : tsk})

    st1 = StarFieldTask(16, star_density, win, 2, drawControl).start()
    sequencer.addTaskToDict(16, {'task' : st1})

    
    while checkBreak(win):
        start = time.time()
        win.autoflush = False
        for task in draw_control_ary:
            task[1].draw(win)
        end = time.time()
        time_over, time_left = mainFrameTimer(start,end, 1)
        win.autoflush = True
        
        #Update starfield center with mouse position
        mousePos(win)
        if time_over :
            #Keep a check on framerate performance
            print(f"Over: {time_left}")
            
        sequencer.sequenceControl()    

    user_exit = True

    if not win.isClosed(): win.close()

main()
