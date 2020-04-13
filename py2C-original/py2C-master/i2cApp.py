#Playing around with tkinter and multiprocessing
import tkinter as tk # developing with 8.6
import numpy as np
from functools import partial # to link callback functions with arguments
from multiprocessing import Process, Queue
import time
import i2c_v2 as i2c


def buildTrace(x,y,scale=1.0,offset=0,width=400,height=200):
    out = []
    assert len(x) == len(y)
    for i in range(0,len(x)):
        out.append((x[i]-min(x))/(max(x)-min(x))*width)
        out.append(height - y[i]*scale)
    return(out)
    


class i2cApp(tk.Frame):
# a simple class descending from tk.Frame.
    UPDATE_PERIOD = 10
    MAX_N_DATA = 500
    
    
    def __init__(self, master=None): # creator
        # call creator for tk.Frame object, create in master
        tk.Frame.__init__(self, master)
        # register with the object handling system
        self.pack()
        # create and initialize widgets
        self.createWidgets()
        # initialize DAC, ADC and HIH
        self.dac = i2c.DAC8574(addr=0x4d,Vref=2.49,Voff=0.02)
        self.adc = i2c.ADS1015(addr=0x4b)
        self.adc.MUX = 0b110
        self.adc.PGA = 0b010
        self.adc.MODE = 0b1
        # initialize data fields
        self.humidity = []
        self.temperature = []
        self.adcvalue = []
        self.time = []
        self.humTraceID = -1
        self.tempTraceID = -1
        self.adcTraceID = -1
        print(self.dac)
        print(self.adc)
        # start measurements
        self.continuousMeasure()
        

    def continuousMeasure(self):
        data = [0,0] # self.hih.get_data()
        value = self.adc.get_conversion()
        self.lblStatus1['text']= "Humidity: {0:.4f} %".format(data[0]) + ", Temperature: {0:.4f} oC".format(data[1])
        self.lblStatus2['text']= "ADC reading: {0:.4f} V".format(value)
        self.humidity.append(data[0])
        self.temperature.append(data[1])
        self.adcvalue.append(value)
        if len(self.time) == 0:
            self.time = [0]
        else:
            self.time.append(max(self.time)+1)
        if len(self.time) > self.MAX_N_DATA:
            self.time = self.time[1:]
            self.humidity = self.humidity[1:]
            self.temperature = self.temperature[1:]
            self.adcvalue = self.adcvalue[1:]
            


        if self.humTraceID > 0:
            self.cnvChart.delete(self.humTraceID)
            self.cnvChart.delete(self.tempTraceID)
            self.cnvChart.delete(self.adcTraceID)
            
        if len(self.time) > 1:
            self.humTrace = buildTrace(self.time,self.humidity,scale=2)
            self.tempTrace = buildTrace(self.time,self.temperature,scale=4)
            self.adcTrace = buildTrace(self.time,self.adcvalue,scale=100)            
            self.humTraceID = self.cnvChart.create_line(self.humTrace,fill='blue')
            self.tempTraceID = self.cnvChart.create_line(self.tempTrace,fill='red')
            self.adcTraceID = self.cnvChart.create_line(self.adcTrace,fill='green')
        
        # request next update after DRAW_UPDATE_PERIOD seconds
        self.after(int(1000*self.UPDATE_PERIOD),self.continuousMeasure)
        
               
    def btnSetDACCallback(self, obj):
        self.dac.set_output(0,self.sldA.get()/1000,units='V')
        self.dac.set_output(1,self.sldB.get()/1000,units='V')
        self.dac.set_output(2,self.sldC.get()/1000,units='V')
        self.dac.set_output(3,self.sldD.get()/1000,units='V')
        
     
    def createWidgets(self):
    # Creates and places all widgets in the application.
        
        # ch A slider scale
        self.sldA = tk.Scale(self, from_=0, to=2000, tickinterval=0, orient=tk.HORIZONTAL, length =450)
        self.sldA.set(0)
        self.sldA.pack()
        # ch B slider scale
        self.sldB = tk.Scale(self, from_=0, to=2000, tickinterval=0, orient=tk.HORIZONTAL, length =450)
        self.sldB.set(0)
        self.sldB.pack()
        # ch C slider scale
        self.sldC = tk.Scale(self, from_=0, to=2000, tickinterval=0, orient=tk.HORIZONTAL, length =450)
        self.sldC.set(0)
        self.sldC.pack()
        # ch D slider scale
        self.sldD = tk.Scale(self, from_=0, to=2000, tickinterval=0, orient=tk.HORIZONTAL, length =450)
        self.sldD.set(0)
        self.sldD.pack()
        # Start/Stop button
        self.btnSetDAC = tk.Button(self, text='Set DAC')
        self.btnSetDAC.config(command = partial(self.btnSetDACCallback, self.btnSetDAC))
        self.btnSetDAC.pack()
        # Quit button
        self.btnQuit = tk.Button(self, text='Quit', command = self.kill)
        self.btnQuit.pack()
        # canvas for plotting
        self.cnvChart = tk.Canvas(self, width=400, height=200)  
        self.cnvChart.pack()
        # labels
        self.lblStatus1 = tk.Label(self,text="{} kt".format(0))
        self.lblStatus1.pack()
        self.lblStatus2 = tk.Label(self,text="{} deg".format(0))
        self.lblStatus2.pack()
        
    def kill(self):
        self.dac.power_down(-1,0)
        self.quit()


# create a root window
root = tk.Tk()
# change resizability
root.resizable(width=False,height=False)
xpos = int(root.winfo_screenwidth()/2-50)
ypos = int(root.winfo_screenheight()/2-50)
root.geometry("600x600+{}+{}".format(int(root.winfo_screenwidth()/2-300),int(root.winfo_screenheight()/2-300)))
#print(geo)
#root.geometry(geo)
# create app in root window
app = i2cApp(master=root)
app.master.title('i2c control')
# start loop
app.mainloop()
# destroy app once mainloop was exited
root.destroy()

