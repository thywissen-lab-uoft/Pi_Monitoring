#Playing around with tkinter and multiprocessing
import tkinter as tk # developing with 8.6
import numpy as np
from functools import partial # to link callback functions with arguments
from multiprocessing import Process, Queue
import time
import random

class Gerty(tk.Canvas):
    " A class to summon gerty, based on the tk.Canvas. "
    
    emotions = ['neutral','happy','sad','winkleft','winkright',\
                'oooh','dooh','mad','angry','concerned','winkboth',\
                'supersad','supersupersad','asleep']
    defaults = {'emo':'happy','scale':0.9,'linewidth':4,\
                'volatile_objs':[],'alive':True,'auto_tau':1}
    
    def __init__(self,root,**kwargs):
        # initialize a generic canvas
        tk.Canvas.__init__(self,root)
        valid_kws = self.config()
        # separate canvas kwargs from others
        addtl_kwargs = {}
        for kw in kwargs:
            if kw not in valid_kws:
                addtl_kwargs[kw] = kwargs[kw]
        for kw in addtl_kwargs:
            kwargs.pop(kw)
        # configure canvas
        self.config(kwargs)
        # set default attributes, then update
        for kw in self.defaults:
            self.__setattr__(kw,self.defaults[kw])
        self.auto_emos = self.emotions
        for kw in addtl_kwargs:
            self.__setattr__(kw,addtl_kwargs[kw])
        # initialize the canvas (background, circle, etc)
        self.initialize()
        self.draw()
        self.auto_emos={'happy':(20,7),'neutral':(2,4),\
                        'winkleft':(3,1),'winkright':(1,1),\
                        'winkboth':(1,2),'sad':(1,5),\
                        'supersad':(1,15),\
                        'thinkleft':(2,2),'thinkright':(2,2),\
                        'asleep':(1,120)}
        self.auto_emotion()
        

    def initialize(self):
        " Draws the first appearance of gerty. " 
        w = int(self.cget('width')); h = int(self.cget('height'))
        W = min([w,h])*self.scale; H = W
        w = (w-W)*0.5; h = (h-H)*0.5
        self.delete('all')
        self.config(background='#bbccee')
        self.create_oval(w,h,w+W,h+H,fill='#ffbb66',outline='black',width=self.linewidth)
        self.draw()

    def auto_emotion(self):
        if self.alive:
            if type(self.auto_emos) is dict:
                emotions = []
                for emo in self.auto_emos:
                    for i in range(0,self.auto_emos[emo][0]):
                        emotions.append(emo)
                self.emo = emotions[random.randint(0,len(emotions)-1)]
                self.draw()
                self.auto_tau = self.auto_emos[self.emo][1]
            else:
                self.emo = self.auto_emos[random.randint(0,len(self.auto_emos)-1)]
            waittime = int(-np.log(1-random.random())*self.auto_tau*1000)
            self.after(waittime, self.auto_emotion)
        else:
            pass

  

    def create_eye(self,pos,mode=None):
        " Draws an eye for gerty, based on mode. Coordinate system is centered\
        on center of canvas and scaled by self.scale. With self.scale = 1, the\
        full scale square ranges from -0.5 to 0.5."
        # calculate scaling and offset in pixels
        w = int(self.cget('width')); h = int(self.cget('height'))
        W = min([w,h])*self.scale; H = W
        w = (w-W)*0.5; h = (h-H)*0.5
        # decide whether its a left or a right eye
        if (pos[0]<0): isleft = 1
        else: isleft = -1
        # draw it and return the object handle
        if mode == 'closed':
            return self.create_line(W*(0.5+pos[0]-0.07)+w,H*(0.5-pos[1])+h,\
                                    W*(0.5+pos[0]+0.07)+w,H*(0.5-pos[1])+h,\
                                    fill='black',width=self.linewidth)
        elif mode == 'closedup':
            return self.create_line(W*(0.5+pos[0]-0.07)+w,H*(0.5-pos[1]-0.02*isleft)+h,\
                                    W*(0.5+pos[0]+0.07)+w,H*(0.5-pos[1]+0.02*isleft)+h,\
                                    fill='black',width=self.linewidth)
        elif mode == 'closeddown':
            return self.create_line(W*(0.5+pos[0]-0.07)+w,H*(0.5-pos[1]+0.02*isleft)+h,\
                                        W*(0.5+pos[0]+0.07)+w,H*(0.5-pos[1]-0.02*isleft)+h,\
                                        fill='black',width=self.linewidth)
        else:
            return self.create_oval(W*(0.5+pos[0]-0.06)+w,H*(0.5-pos[1]+0.12)+h,\
                                    W*(0.5+pos[0]+0.06)+w,H*(0.5-pos[1]-0.12)+h,\
                                    fill='black')
        
    def create_eyebrow(self,pos,mode=None,length=0.12):
        " Draws an eye for gerty, based on mode. Coordinate system is centered\
        on center of canvas and scaled by self.scale. With self.scale = 1, the\
        full scale square ranges from -0.5 to 0.5."
        # calculate scaling and offset in pixels
        w = int(self.cget('width')); h = int(self.cget('height'))
        W = min([w,h])*self.scale; H = W
        w = (w-W)*0.5; h = (h-H)*0.5
        # decide whether its a left or a right eye
        if (pos[0]<0): isleft = 1
        else: isleft = -1
        # draw it and return the object handle
        if mode == 'flatup':
            return self.create_line([W*(0.5+pos[0]-length/2)+w,H*(0.5-pos[1]-length/6*isleft)+h,\
                                     W*(0.5+pos[0]+length/2)+w,H*(0.5-pos[1]+length/6*isleft)+h],\
                                    fill='black',width=self.linewidth)
        elif mode == 'flatdown':
            return self.create_line([W*(0.5+pos[0]-length/2)+w,H*(0.5-pos[1]+length/6*isleft)+h,\
                                     W*(0.5+pos[0]+length/2)+w,H*(0.5-pos[1]-length/6*isleft)+h],\
                                    fill='black',width=self.linewidth)
        else:
            return self.create_line(W*(0.5+pos[0]-0.07)+w,H*(0.5-pos[1]-0.02*isleft)+h,\
                                    W*(0.5+pos[0]+0.07)+w,H*(0.5-pos[1]+0.02*isleft)+h,\
                                    fill='black',width=self.linewidth)
            
        
        
    def create_mouth(self,pos,mode=None,length=0.2):
        " Draws a mouth for gerty, based on mode. Coordinate system is centered\
        on center of canvas and scaled by self.scale. With self.scale = 1, the\
        full scale square ranges from -0.5 to 0.5."
        # calculate scaling and offset in pixels
        w = int(self.cget('width')); h = int(self.cget('height'))
        W = min([w,h])*self.scale; H = W
        w = (w-W)*0.5; h = (h-H)*0.5
        # draw it and return the object handle
        if mode == 'neutral':
            return self.create_line([W*(0.5+pos[0]-length/2)+w,H*(0.5-pos[1])+h,\
                                     W*(0.5+pos[0]+length/2)+w,H*(0.5-pos[1])+h],\
                                    fill='black',width=self.linewidth)
        elif mode == 'flatup':
            return self.create_line([W*(0.5+pos[0]-length/2)+w,H*(0.5-pos[1]+length/8)+h,\
                                     W*(0.5+pos[0]+length/2)+w,H*(0.5-pos[1]-length/8)+h],\
                                    fill='black',width=self.linewidth)
        elif mode == 'flatdown':
            return self.create_line([W*(0.5+pos[0]-length/2)+w,H*(0.5-pos[1]-length/8)+h,\
                                     W*(0.5+pos[0]+length/2)+w,H*(0.5-pos[1]+length/8)+h],\
                                    fill='black',width=self.linewidth)       
        elif mode == 'oooh':
            return self.create_oval(W*(0.5+pos[0]-0.05)+w,H*(0.5-pos[1]+0.03)+h,\
                                    W*(0.5+pos[0]+0.05)+w,H*(0.5-pos[1]-0.03)+h,\
                                    fill='black')
        elif mode == 'sad':
            return self.create_arc(W*(0.5+pos[0]-0.4)+w,H*(0.5-pos[1])+h,\
                                   W*(0.5+pos[0]+0.4)+w,H*(0.5-pos[1]+0.8)+h,\
                                   fill='black',width=self.linewidth, style='arc',\
                                   start=45,extent=90)            
        else:
            return self.create_arc(W*(0.5+pos[0]-0.4)+w,H*(0.5-pos[1]-0.8)+h,\
                                   W*(0.5+pos[0]+0.4)+w,H*(0.5-pos[1])+h,\
                                   fill='black',width=self.linewidth, style='arc',\
                                   start=215,extent=110)
        

    def draw(self,emo=None):
        " Draws gerty with specified emotion. "
        if emo:
            if emo == 'random':
                self.emo = self.emotions[random.randint(0,len(self.emotions)-1)]
            else:
                self.emo = emo
        w = int(self.cget('width')); h = int(self.cget('height'))
        W = min([w,h])*self.scale; H = W
        w = (w-W)*0.5; h = (h-H)*0.5
        # delete existing eyes, mouth, brows, etc.
        for obj_id in self.volatile_objs: self.delete(obj_id)
        self.volatile_objs == []
        # draw emotion
        if self.emo == 'sad':
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_mouth([0,-0.05],mode='sad'))
        elif self.emo == 'supersad':
            self.volatile_objs.append(self.create_eye([-0.12,0.1],mode='closeddown'))
            self.volatile_objs.append(self.create_eye([0.12,0.1],mode='closeddown'))
            self.volatile_objs.append(self.create_mouth([0,-0.05],mode='sad'))
        elif self.emo == 'supersupersad':
            self.volatile_objs.append(self.create_eye([-0.12,0.1],mode='closeddown'))
            self.volatile_objs.append(self.create_eye([0.12,0.1],mode='closeddown'))
            self.volatile_objs.append(self.create_mouth([0,-0.05],mode='sad'))
        elif self.emo == 'wink' or self.emo == 'winkleft':
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_eye([0.12,0.1],mode='closedup'))
            self.volatile_objs.append(self.create_mouth([0,-0.15]))
        elif self.emo == 'winkboth':
            self.volatile_objs.append(self.create_eye([-0.12,0.1],mode='closedup'))
            self.volatile_objs.append(self.create_eye([0.12,0.1],mode='closedup'))
            self.volatile_objs.append(self.create_mouth([0,-0.15]))
        elif self.emo == 'winkright':
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_eye([-0.12,0.1],mode='closedup'))
            self.volatile_objs.append(self.create_mouth([0,-0.15]))
        elif self.emo == 'neutral':
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_mouth([0,-0.13],mode='neutral',length=0.2))
        elif self.emo == 'asleep':
            self.volatile_objs.append(self.create_eye([0.12,0.08],mode='closed'))
            self.volatile_objs.append(self.create_eye([-0.12,0.08],mode='closed'))
            self.volatile_objs.append(self.create_mouth([0.05,-0.12],mode='neutral',length=0.1))
        elif self.emo == 'think' or self.emo == 'thinkright':
            self.volatile_objs.append(self.create_eye([-0.14,0.18]))
            self.volatile_objs.append(self.create_eye([0.08,0.18]))
            self.volatile_objs.append(self.create_mouth([0.05,-0.15],mode='flatup',length=0.10))
        elif self.emo == 'thinkleft':
            self.volatile_objs.append(self.create_eye([0.14,0.18]))
            self.volatile_objs.append(self.create_eye([-0.08,0.18]))
            self.volatile_objs.append(self.create_mouth([-0.05,-0.15],mode='flatdown',length=0.10))
        elif self.emo == 'oooh':
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_mouth([0,-0.14],mode='oooh'))
        elif self.emo == 'dooh':
            self.volatile_objs.append(self.create_eye([0.10,0.1],mode='closedup'))
            self.volatile_objs.append(self.create_eye([-0.10,0.1],mode='closedup'))
            self.volatile_objs.append(self.create_mouth([0,-0.14],mode='oooh'))
        elif self.emo == 'mad':
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_eyebrow([0.12,0.26],mode='flatup'))
            self.volatile_objs.append(self.create_eyebrow([-0.12,0.26],mode='flatup'))
            self.volatile_objs.append(self.create_mouth([0.05,-0.13],mode='flatup',length=0.2))
        elif self.emo == 'concerned':
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_eyebrow([0.12,0.29],mode='flatdown'))
            self.volatile_objs.append(self.create_eyebrow([-0.12,0.29],mode='flatdown'))
            self.volatile_objs.append(self.create_mouth([0,-0.13],mode='flatup',length=0.2))
        elif self.emo == 'angry':
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_eyebrow([0.12,0.26],mode='flatup'))
            self.volatile_objs.append(self.create_eyebrow([-0.12,0.26],mode='flatup'))
            self.volatile_objs.append(self.create_mouth([0.0,-0.13],mode='oooh'))
        else:
            self.volatile_objs.append(self.create_eye([-0.12,0.1]))
            self.volatile_objs.append(self.create_eye([0.12,0.1]))
            self.volatile_objs.append(self.create_mouth([0,-0.15]))



class GertyApp(tk.Frame):
# a simple class descending from tk.Frame.
   
    
    def __init__(self, master=None): # creator
        # call creator for tk.Frame object, create in master
        tk.Frame.__init__(self, master)
        # register with the object handling system
        self.pack()
        # create and initialize widgets
        self.createWidgets()


   
    def createWidgets(self):
    # Creates and places all widgets in the application.

        # Quit button
        #self.btnEmotion = tk.Button(self, text='Emo!')
        #self.btnEmotion.config(command = partial(self.btnEmotionCallback, self.btnEmotion))
        #self.btnEmotion.pack()
        # Quit button
        #self.btnQuit = tk.Button(self, text='Quit', command = self.kill)
        #self.btnQuit.pack()        
        # canvas for plotting
        self.gerty = Gerty(self,width=300,height=200,linewidth=6,emo='happy')
        self.gerty.pack()
        self.gerty.draw()

    def btnEmotionCallback(self,obj):
        self.gerty.draw(emo='random')
        
    def kill(self):
        self.quit()

