'''
Starfield sim written in Python uses Graphics.py as an interface to tinkter.
SRR 23/04/2020
'''

from graphics import *

import math, random, queue, time, threading, os

from ctypes import windll 
timeBeginPeriod = windll.winmm.timeBeginPeriod 
#set windows system timer to 1mS tick
#So I guess this won't work on a Mac or Linux??
timeBeginPeriod(1) 

#winWdth = 1000
#winHt = 1000
winWdth = 1280
winHt = 720

centerX = winWdth / 2.0
centerY = winHt / 2.0
mouse_x = 0
mouse_y = 0

user_exit = False

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
        while not user_exit:
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
def checkBreak(win):
    #Break flagged on any click or window closed
    return (not win.isClosed() and win.checkMouse() == None)

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
    win = MouseGrapWin('Animated StarField',winWdth,winHt)
    win.setBackground('black')
    message = Text(Point(win.getWidth()-200, win.getWidth()-10), 'Animated StarField - SRRose, Romanviii.co.uk')
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
    queue1 = queue.Queue()
    user_exit = False

   
    st1 = StarField(30, 0.07, 0.02, queue1, win, 2).start()

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
        #Update starfield center with mouse position    
        mousePos(win)    
    user_exit = True         
    if not win.isClosed(): win.close()
    
main()    
