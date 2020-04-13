import time
from Autoplot_Lists import Plotobject
import pandas as pd
import RPi.GPIO as gpio

class Plotter():
    
    _default = {\
        'path':"/home/pi/YDrive/share/Pi_Monitoring/Logs/",\
        'filemask_fast':"DataLog_Fast.txt",\
        'filemask_slow':"DataLog_Slow_{2:04}-{1:02}-{0:02}.txt",\
        'trigger_pin':16,\
        'trigger_enable':True,\
        'plot_period':120*1000,\
        }

    def __init__(self,**kwargs):
        # first set defaults, then overwrite with possible user input
        for kw in self._default:
            setattr(self,kw,self._default[kw])
        for kw in kwargs:
            assert kw in self._default,\
                   "Unknown keyword '{}!'".format(kw)
            setattr(self,kw,kwargs[kw])

    def Start_Plotting(self):
        plotobj = Plotobject()
        previous_index = 0
        previous_time = time.localtime()
        received_trigger = False
        while True:
            if self.trigger_enable:
                res = gpio.wait_for_edge(self.trigger_pin,\
                                         gpio.RISING,\
                                         timeout=self.plot_period)
                if res == None:
                    received_trigger = False
                else:
                    received_trigger = True
            else:
                time.sleep(self.plot_period)
                received_trigger = False
                
            now = time.localtime()
            #Reconsider this indexing stuff. For 'fast' datafiles, read the whole file.
            if now.tm_mday != previous_time.tm_mday:
                previous_index = 0
                
            outfile_fast = self.path + self.filemask_fast.\
                format(now.tm_mday,now.tm_mon,now.tm_year)
            outfile_slow = self.path + self.filemask_slow.\
                format(now.tm_mday,now.tm_mon,now.tm_year)
            try:
                data_fast = pd.read_csv(outfile_fast,
                                        header = None)
                data_slow = pd.read_csv(outfile_slow,
                                        header = None)
                
                #Is splitting into 3 really necessary? Could this be two lines?
                times_fast = pd.to_datetime(data_fast.iloc[:,0]).tolist()
                times_slow = pd.to_datetime(data_slow.iloc[previous_index::,0]).tolist()
                measurements_fast = data_fast.iloc[:,1:-1].values.tolist()
                measurements_slow = data_slow.iloc[previous_index::,1:-1].values.tolist()
                triggers_fast = data_fast.iloc[:,-1].values.tolist()
                triggers_slow = data_fast.iloc[previous_index::,-1].values.tolist()
                
                previous_index = previous_index + len(times_slow)
                previous_time = now

                # This is fine. Just add the data, have the deques sort out what to plot. 
                # For the 'slow' data, append to the deque.
                # For the 'fast' data, only plot if triggered?
                plotobj.add_plot_data(received_trigger, times_fast, measurements_fast, triggers_fast,\
                                      times_slow, measurements_slow, triggers_slow)
            except:
                continue
                #Do nothing
        
if __name__ == "__main__":
    gpio.setmode(gpio.BCM)
    gpio.setup(16,gpio.IN)
    Plot_Instance = Plotter()
    Plot_Instance.Start_Plotting()
