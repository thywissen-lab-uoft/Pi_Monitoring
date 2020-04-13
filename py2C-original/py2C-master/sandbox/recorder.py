#Playing around with tkinter and multiprocessing
import tkinter as tk # developing with 8.6
import numpy as np
from functools import partial # to link callback functions with arguments
from multiprocessing import Process, Queue
import time
import i2c_v3 as i2c
from gerty import Gerty as gerty


def buildTrace(x,y,scale=[None,None],offset=[None,None],width=400,height=200):
    " Builds the multi-segment line that displays (x,y) data on a \
    TkCanvas object. the data can be scaled and shifted vertically."
    out = []
    assert len(x) == len(y)
    if scale[0] == None:
        if max(x) == min(x): scale[0] = 1.0
        else: scale[0] = width/(max(x)-min(x))
        offset[0] = None
    if scale[1] == None:
        if max(y) == min(y): scale[1] = 1.0
        else: scale[1] = (height-1)/(max(y)-min(y))
        offset[1] = None
    if not offset[0]: offset[0] = -min(x)
    if not offset[1]: offset[1] = -min(y)
    for i in range(0,len(x)):
        out.append((x[i]+offset[0])*scale[0])
        out.append(height-(y[i]+offset[1])*scale[1])
    return(out)

class fake_device():
    ct = 0
    def __init__(self):
        pass
    def get(self):
        self.ct += 1
        return (0.001*self.ct)%2

def meas_process(device,readQ,writeQ,*args):
    " The measurement process. "
    config = {'max_lag':1,'meas_rate':8,'max_data':64}
    if len(args) > 0 and type(args[0]) == dict:
        kwargs = args[0]
    else:
        kwargs = dict()
    for kw in kwargs: config[kw] = kwargs[kw]
    print(config)
    Done = False
    Send = False
    start = time.time()
    last = 0
    data = []; 
    # Measurement loop.
    while not Done:
        # Read new data from device and pair with current time.
        now = time.time() - start
        data.append(now)
        data.append(device.get())
        # Check lag in data acquisition (THIS IS NOT A REALTIME MEASUREMENT)
        if (now-last-1/config['meas_rate']) > config['max_lag']:
            writeQ.put("Lag exceeds allowance!")
        last = last+1/config['meas_rate']
        # follow commands sent through the readQueue
        while not readQ.empty():
            cmd = readQ.get()
            assert cmd.__class__ == str
            assert len(cmd) >= 4
            if cmd[:4] == "done":
                # Exits the loop.
                Done = True
            elif cmd[:4] == "send":
                writeQ.put("Sending data.")
                writeQ.put(data)
                data = []
        # If holding more than max_data, push to writeQueue
        if len(data) > 2*config['max_data']:
            writeQ.put("Max data reached!")
            writeQ.put(data)
            data = []
        # Wait some time
        while (time.time()-start-last) < (1/config['meas_rate']):
            pass
                           
    writeQ.put("Measurement process ended.")


class continuousMeasurement():
    " A generic API to a continuous measurement. "
    config_keys = {'data_rate','update_rate','max_lag','max_data'}

    def __init__(self,*args,**kwargs):
        self.config(**kwargs)
        self.readQ = Queue()
        self.writeQ = Queue()
        self.started = False

    def start(self):
        " Creates and starts the process. "
        if self.started:
            print("Process already running!")
            return
        self.started = True
        self.process = Process(target=meas_process, \
                               args=(fake_device(),self.writeQ,self.readQ))
        self.process.start()

    def stop(self):
        " Requests data from process; then stops it. "
        self.writeQ.put("done")
        # empty the queue discarting all contents
        while not self.readQ.empty():
            self.readQ.get()
        self.process.join()
        self.started = False

    def pull_data(self):
        if self.started:
            self.writeQ.put("send")
            data = []
            received = False
            while not received:
                read = self.readQ.get()
                if read == "Sending data.":
                    data = data + self.readQ.get()
                    received = True
                elif read == "Max data reached!":
                    print(read)
                    data = data + self.readQ.get()
                    received = False
                else:
                    print(read)
            return data
        else:
            print("Process not started!")
            return []

    def config(self,**kwargs):
        " self.conig() returns a dictionary with the current configuration \
        values. With keyword arguments: sets the respective configuration. "
        if len(kwargs) == 0:
            return self.get_config('all')
        else:
            for kw in kwargs:
                self.set_config(kw,kwarks[kw])

    def get_config(self,*args):
        " For a single keyword, returns the configuration value. Returns a \
        dictionary for multiple keywords. 'all' triggers return of a complete \
        dictionary of the configuration. "
        if len(args) == 1:
            if args[0] == 'all':
                out = dict()
                for kw in self.config_keys:
                    out[kw] = self.get_config(kw)
                return out
            else:
                if args[0] in self.config_keys:
                    return 0#self.cfg(args[0]) 
                else:
                    raise KeyError('Unknown configuration key: {}'.format(args[0]))
        else:
            out = dict()
            for kw in args:
                out[kw] = self.get_config(kw)
            return out

    def set_config(self,**kwargs):
        " Change configuration via keyword arguments. "
        for kw in kwargs:
            if kw in self.config_keys:
                print("Known: ",kw,kwargs[kw])
            else:
                print("Unknown: ",kw,kwargs[kw])


                
                
    
    
    # API should contain:
    # - routine for repeated "measurements" (adding values to a buffer)
    # - starting and stopping the process
    # - signalling available new data when prompted
    # - transmitting buffer of data when prompted
    # Use queue and pipes

class dataCanvas(tk.Canvas):
    " A tk canvas to display data. Basically similar to what is available with\
    matplotlib, but taylored to simpler needs. "

    defaults = {'range':None,\
                'data':None,'data_color':None,\
                'data_linewidth':None,'data_visible':None,\
                'x_ticks':None,'y_ticks':None,\
                'x_tick_gen':None,'y_tick_gen':None}
    colors = ('blue','red','green','black')

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
        for kw in addtl_kwargs:
            self.__setattr__(kw,addtl_kwargs[kw])
        # overwrite with empty data arrays for each new instance
        self.data = []
        self.data_color = []
        self.data_linewidth = []
        self.data_visible = []
        self.trace_id = []
        # then add data properly, if any was given (not allowing for color
        # and line specs for now)
        if 'data' in kwargs:
            data = kwargs('data')
            assert type(data) is list and len(data) > 0
            data = data.copy()
            if type(data[0]) is list and len(data[0]) > 0:
                if type(data[0][0]) is list:
                    # multiple data sets are given
                    for dataset in data:
                        self.add_dataset(dataset)
                else:
                    # one dataset was given
                    self.add_dataset(data)
            else:
                # only y-data was given
                self.add_dataset(data)
        # initialize the canvas (background, circle, etc)
        if self.range == None: self.range = [None,None]
        self.initialize_canvas()
        self.draw_data()

    def initialize_canvas(self):
        W = int(self.cget('width'))
        H = int(self.cget('height'))
        # build dummy data if none is given
        if self.data: data=self.data
        else: data = [[0,1],[0,1]]
        # get full range if no range is given
        print(data)
        for i in [0,1]:
            if not self.range[i]:
                self.range[i] = [min(data[i]),max(data[i])]
                if not self.range[i][0]: self.range[i][0] = 0
                if not self.range[i][1]: self.range[i][1] = 1
                if self.range[i][0] == self.range[i][1]:
                    self.range[i][0] -= 1
                    self.range[i][1] += 1
        # clear canvas and initialize id arrays
        self.delete('all') 
        self.frame_id = []; self.tick_id = []; self.trace_id = []
        self.ticklabels = [];
        # draw frame and ticks
        self.frame_id.append(self.create_rectangle(1,1,W,H))
        self.sort_data(direction=0)
        self.draw_ticks()
        self.create_ticklabels()

    def draw_ticks(self):
        " Draws x and y ticks on the frame. "
        W = int(self.cget('width'))
        H = int(self.cget('height'))
        L = max([min([H,W])/40,3])
        # remove existing ticks
        for tick_id in self.tick_id:
            self.delete(tick_id)
        self.tick_id = []
        # if tick generation is defined, generate ticks
        if self.x_tick_gen != None:
            self.x_ticks = []
            for i in range(int(self.range[0][0]/self.x_tick_gen),\
                           int(self.range[0][1]/self.x_tick_gen)+1):
                self.x_ticks.append(i*self.x_tick_gen)
        if self.y_tick_gen != None:
            self.y_ticks = []
            for i in range(int(self.range[0][0]/self.y_tick_gen),\
                           int(self.range[0][1]/self.y_tick_gen)+1):
                self.y_ticks.append(i*self.y_tick_gen)
        # draw x ticks
        if self.x_ticks != None:
            for x in self.x_ticks:
                X,Y = self.canvas_coords(x,0)
                self.tick_id.append(self.create_line([X,1,X,L+1],fill='black'))
                self.tick_id.append(self.create_line([X,H,X,H-L],fill='black'))
        if self.y_ticks != None:
            for y in self.y_ticks:
                X,Y = self.canvas_coords(0,y)
                self.tick_id.append(self.create_line([1,Y,L+1,Y],fill='black'))
                self.tick_id.append(self.create_line([W,Y,W-L,Y],fill='black'))

    def create_ticklabels(self):
        " Places tick labels left and at the bottom. "
        # remove existing ticklabels
        return
        # DIFFICULT TO PLACE LABELS OUTSIDE CANVAS WITHOUT
        # HAVIGN ACCESS TO CANVAS WIDGET PLACEMENT ... MAY NEED
        # TO BUILD BOUNDING BOX FOR CANVAS AND LABELS FIRST ...
        for ticklabel in self.ticklabels:
            self.master.delete(ticklabel)
        self.ticklabels = []

    def change_range(self,draw_range=[None,None],redraw=True):
        " Changes the range of the canvas area and redraws visible\
        datasets."
        # keep old range to decide whether to redraw
        old_range = self.range.copy()
        # get full range if no range is given
        for i in [0,1]:
            if draw_range[i] == None:
                if len(self.data) == 0: self.range[i] = [0,1]
                elif len(self.data[0]) == 0: self.range[i] = [0,1]
                elif len(self.data[0][0]) == 0: self.range[i] = [0,1]
                else:
                    self.range[i] = [min(self.data[0][i]),max(self.data[0][i])]
                    for idx in range(1,len(self.data)):
                        self.range[i][0] = min([self.range[i][0],min(self.data[idx][i])])
                        self.range[i][1] = max([self.range[i][1],max(self.data[idx][i])])
            else:
                self.range[i] = draw_range[i]
            if self.range[i][0] == self.range[i][1]:
                self.range[i][0] -= 1
                self.range[i][1] += 1
        # redraw visible data if requested and necessary
        if redraw and (old_range[0] != self.range[0]\
                    or old_range[1] != self.range[1]):
            for i in range(0,len(self.data)):
                if self.data_visible[i]:
                    self.draw_data(idx=i)
            self.draw_ticks()

    def add_dataset(self,data,color=None,drawnow=False,autorange=False,\
                    linewidth=1):
        " Adds a dataset to the canvas. "
        # check the format of data; data is appended as [x,y] with x and y
        # being lists of same length
        assert type(data) is list
        if type(data[0]) is not list:
            data = [[i for i in range(0,len(data))],data]
        assert len(data) == 2
        assert type(data[0]) == list and type(data[1]) == list
        assert len(data[0]) == len(data[1])
        # add data to the canvas
        if not color: color = self.colors[len(self.data)%len(self.colors)]
        self.data.append(data)
        self.data_color.append(color)
        self.data_linewidth.append(linewidth)
        self.data_visible.append(True)
        self.trace_id.append(None)
        if autorange: self.change_range()
        elif drawnow: self.draw_data(idx=-1)

    def remove_dataset(self,idx,autorange=False):
        " Removes a dataset from the canvas. "
        assert idx in range(-1,len(self.data))
        self.data.pop(idx)
        self.data_color.pop(idx)
        self.data_linewidth.pop(idx)
        self.data_visible.pop(idx)
        trace_id = self.trace_id.pop(idx)
        self.delete(trace_id)
        if autorange:
            self.change_range()

    def move_dataset(self,idx,jdx,redraw=True):
        " Moves dataset idx to position jdx, shifting others as necessary. "
        assert idx in range(-1,len(self.data))
        assert jdx in range(-1,len(self.data))
        idx = idx%len(self.data)
        jdx = jdx%len(self.data)
        # swap entries to bubble from idx to jdx
        if idx != jdx:
            if idx > jdx: d = -1
            else: d = 1
            i = idx
            while i != jdx:
                self.swap_dataset(i,i+d)
                i += d

    def swap_dataset(self,idx,jdx,redraw=True):
        " Swaps datasets idx and jdx. "
        assert idx in range(-1,len(self.data))
        assert jdx in range(-1,len(self.data))
        idx = idx%len(self.data)
        jdx = jdx%len(self.data)        
        if idx != jdx:
            #swap
            data = self.data[idx]
            color = self.data_color[idx]
            linewidth = self.data_linewidth[idx]
            visible = self.data_visible[idx]
            trace_id = self.trace_id[idx]
            self.data[idx] = self.data[jdx]
            self.data_color[idx] = self.data_color[jdx]
            self.data_linewidth[idx] = self.data_linewidth[jdx]
            self.data_visible[idx] = self.data_visible[jdx]
            self.trace_id[idx] = self.trace_id[jdx]
            self.data[jdx] = data
            self.data_color[jdx] = color
            self.data_linewidth[jdx] = linewidth
            self.data_visible[jdx] = visible
            self.trace_id[jdx] = trace_id
            # redraw if requested
            if redraw:
                self.draw_data(idx=idx)
                self.draw_data(idx=jdx)

    def sort_data(self,idx=None,direction=0):
        " Sorts data by its x (direction=0) or y (1) values. "
        if idx == None:
            for i in range(0,len(self.data)):
                self.sort_data(idx=i,direction=direction)
        else:
            sorted_idx = [t[1] for t in \
                         sorted((e,i) for i,e in\
                                enumerate(self.data[idx][direction]))]
            self.data[idx][0] = [self.data[idx][0][i] for i in sorted_idx]
            self.data[idx][1] = [self.data[idx][1][i] for i in sorted_idx]

    def draw_data(self,idx=None):
        if idx == None:
            for i in range(0,len(self.data)):
                self.draw_data(idx=i)
        else:
            if len(self.data[idx][0]) == 0: return
            X,Y=self.canvas_coords(self.data[idx][0],self.data[idx][1])
            XY = self.build_xy(X,Y)
            if self.trace_id[idx]: self.delete(self.trace_id[idx])
            self.trace_id[idx] = self.create_line(XY,fill=self.data_color[idx])

    def canvas_coords(self,x,y):
        " Converts data coordinates into pixel coordinates. "
        islist = True
        if type(x) is not list:
            x = [x]; y = [y]
            islist = False
        assert type(y) is list
        assert len(x) == len(y)
        X = []; Y = [];
        # get scaling facors
        W = int(self.cget('width'))
        H = int(self.cget('height'))
        xscale = 1.0/(self.range[0][1] - self.range[0][0])
        yscale = 1.0/(self.range[1][1] - self.range[1][0])
        # transform all values
        for i in range(0,len(x)):
            X.append((W-2)*(x[i] - self.range[0][0])*xscale+2)
            Y.append(H-1-(H-3)*(y[i] - self.range[1][0])*yscale)
        if islist: return X,Y
        else: return X[0],Y[0]

    def build_xy(self,x,y):
        " Merges x and y lists to a single list of xy pairs:\
        x0,y0,x1,y1, ... "
        if type(x) is not list:
            x = [x]; y = [y]
        assert len(x) == len(y)
        out = []
        for i in range(0,len(x)):
            out.append(x[i])
            out.append(y[i])
        return out


class logObject():
    " An object that configures a logging process and hosts multiprocessing\
    queues. "

    defaults = {'meas_rate':8,'max_data':1000,'max_lag':1,\
                'device':None,'ndump':100,'ndisplay':100}

    def __init__(self,**kwargs):
        for kw in self.defaults: self.__setattr__(kw,self.defaults[kw])
        for kw in kwargs: self.__setattr__(kw,kwargs[kw])
        self.readQ = Queue()
        self.writeQ = Queue()
        self.started = False
        

class dataLogCanvas(dataCanvas):
    " A modified canvas object that includes routines for adding data,\
    automatic rescaling and truncation. "

    defaults = {'range':[None,None],\
                'data':[],'data_color':[],'data_linewidth':[],'data_visible':[],
                'x_ticks':None,'y_ticks':None,'update_period':1}
    colors = ('blue','red','green','black')
    
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
        for kw in addtl_kwargs:
            self.__setattr__(kw,addtl_kwargs[kw])
        # overwrite with empty data arrays for each new instance
        self.data = []
        self.data_color = []
        self.data_linewidth = []
        self.data_visible = []
        self.trace_id = []
        # then add data properly, if any was given (not allowing for color
        # and line specs for now)
        if 'data' in kwargs:
            data = kwargs('data')
            assert type(data) is list and len(data) > 0
            data = data.copy()
            if type(data[0]) is list and len(data[0]) > 0:
                if type(data[0][0]) is list:
                    # multiple data sets are given
                    for dataset in data:
                        self.add_dataset(dataset)
                else:
                    # one dataset was given
                    self.add_dataset(data)
            else:
                # only y-data was given
                self.add_dataset(data)
        # initialize the canvas (background, circle, etc)
        if self.range == None: self.range = [None,None]
        self.initialize_canvas()
        self.draw_data()        
        self.log = []
        self.started=False
        this = logObject(meas_rate=64)
        this.device = i2c.LSM9DS1_MAG(addr=0x1e)
        this.device.config(OMxy=0b11,OMz=0b11,MD=0b00,FS=0b00,ODR=0b111)
        this.device.config_info()
        self.add_log(this)
        #this = logObject()
        #this.device = fake_device()
        #self.add_log(this)
        


    def add_log(self,log_obj):
        " Adds a log object. "
        self.log.append(log_obj)
        self.log[-1].data_idx = len(self.data)
        self.add_dataset([[],[]],autorange=True)        

    def start_log(self):
        " Creates and starts the measurement process for all defined log\
        objects. "
        if len(self.log) == 0:
            print("No logs defined!")
            return
        if self.started == True:
            print("Process already running!")
            return
        self.started = True
        for i in range(0,len(self.log)):
            self.log[i].started = True
            self.log[i].process = Process(target=meas_process,\
                                   args=(self.log[i].device,\
                                         self.log[i].writeQ,\
                                         self.log[i].readQ,\
                                         {'meas_rate':self.log[i].meas_rate,\
                                          'max_data':self.log[i].max_data,\
                                          'max_lag':self.log[i].max_lag}))
            
            self.log[i].process.start()
        self.after(int(1000*self.update_period),self.update_log)
        

    def update_log(self):
        " Updates the data for each log and redraws it. "
        for i in range(0,len(self.log)):
            idx = self.log[i].data_idx
            new_data = self.pull_data(idx=i)
            assert len(new_data)%2 == 0
            x = [new_data[2*i] for i in range(0,len(new_data)//2)]
            y = [new_data[2*i+1] for i in range(0,len(new_data)//2)]
            self.data[idx][0] = self.data[idx][0] + x
            self.data[idx][1] = self.data[idx][1] + y
            if len(self.data[idx][0]) > 4096:
                self.data[idx][0] = self.data[idx][0][-4096:]
                self.data[idx][1] = self.data[idx][1][-4096:]
        self.change_range([None,None])
        self.draw_data()
        if self.started:
            self.after(int(1000*self.update_period),self.update_log)

    def stop_log(self):
        " Requests data from all processes; then stops them. "
        for i in range(0,len(self.log)):
            self.log[i].writeQ.put("done")
        for i in range(0,len(self.log)):            
            # empty the queues discarting all contents
            while not self.log[i].readQ.empty():
                self.log[i].readQ.get()
            self.log[i].process.join()
            self.log[i].started = False
        self.started = False

    def pull_data(self,idx=0):
        if self.started == True:
            self.log[idx].writeQ.put("send")
            data = []
            received = False
            while not received:
                read = self.log[idx].readQ.get()
                if read == "Sending data.":
                    data = data + self.log[idx].readQ.get()
                    received = True
                elif read == "Max data reached!":
                    print(read)
                    data = data + self.log[idx].readQ.get()
                    received = False
                else:
                    print(read)
            return data
        else:
            #print("Process not started!")
            return []

    


class i2cApp(tk.Frame):
# a simple class descending from tk.Frame.
    UPDATE_PERIOD = 0.5
    MAX_N_DATA = 100
    
    
    def __init__(self, master=None): # creator
        # call creator for tk.Frame object, create in master
        tk.Frame.__init__(self, master)
        # register with the object handling system
        self.pack()
        # create and initialize widgets
        self.createWidgets()
        # initialize DAC, ADC and HIH
        #self.dac = i2c.DAC8574(addr=0x4d,Vref=2.49,Voff=0)
        #self.adc = i2c.ADS1015(addr=0x4b)
        #self.adc.DR = 0b101
        #self.adc.MUX = 0b010
        #self.adc.PGA = 0b010
        #self.adc.MODE = 0b0
        # initialize data fields
        #self.humidity = []
        #self.temperature = []
        #self.adcvalue = []
        #self.time = []
        #self.humTraceID = -1
        #self.tempTraceID = -1
        #self.adcTraceID = -1
        #print(self.dac)
        #print(self.adc)

    def btnSetDACCallback(self, obj):
        #self.dac.update_outputs()
        #self.dac.set_output(0,self.sldA.get()/1000,units='V')
        #self.dac.set_output(1,self.sldB.get()/1000,units='V')
        #self.dac.set_output(2,self.sldC.get()/1000,units='V')
        #self.dac.set_output(3,self.sldD.get()/1000,units='V')
        self.gerty.draw(emo='happy')

    def sldABCDCallback(self,obj,ch,value):
        " Slider callback, executes upon value change. "
        #self.dac.store_value(ch,obj.get()/1000,units='V')
        self.gerty.draw(emo='thinkleft')
        
     
    def createWidgets(self):
    # Creates and places all widgets in the application.
        
        # canvas for plotting
        self.frame = tk.Frame(self, width=600, height=200)
        self.frame.pack() 
        self.cnvLogChart = dataLogCanvas(self.frame, width=400, height=100,\
                                   x_tick_gen=5,\
                                   y_tick_gen=0.5)
        self.cnvLogChart.pack()
        self.lbl = tk.Label(self.frame,text='me')
        self.lbl.pack()
        
        # Meas_Start
        self.btnStart = tk.Button(self, text='Start')
        self.btnStart.config(command = self.cnvLogChart.start_log)
        # Meas_Stop
        self.btnStop = tk.Button(self, text='Stop')
        self.btnStop.config(command = self.cnvLogChart.stop_log)
        
        self.btnStart.pack()
        self.btnStop.pack()        

        self.gerty = gerty(self,width=100,height=70,linewidth=2)
        self.gerty.pack()        
        # Quit button
        self.btnQuit = tk.Button(self, text='Quit', command = self.kill)
        self.btnQuit.pack()

       
    def kill(self):
        self.quit()


# create a root window
root = tk.Tk()
# change resizability
root.resizable(width=False,height=False)
xpos = int(root.winfo_screenwidth()/2-50)
ypos = int(root.winfo_screenheight()/2-50)
root.geometry("700x300+{}+{}".format(int(root.winfo_screenwidth()/2-300),int(root.winfo_screenheight()/2-300)))
#print(geo)
#root.geometry(geo)
# create app in root window
app = i2cApp(master=root)
app.master.title('i2c control')
# start loop
app.mainloop()
# destroy app once mainloop was exited
root.destroy()

