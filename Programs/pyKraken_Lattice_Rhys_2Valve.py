# Datalogging with the raspberry pi and i2c devices -- ST 03/2017
#
#   Running on 2.7.9; everything but gpio functionality works in 3.5 as well.
#
import py2C as i2c
import RPi.GPIO as gpio
import numpy as np
import time
import smbus
import concurrent.futures
import threading
import queue
import math
#from plotting2fig import Plotobject                           # self-defined class for plotting

class DataLogger():
    """ A simple data-to-file logging class. """

    _default = {\
        'meas_period':0.50,\
        'avg_period':5.0,\
        'trigger_pin':None,\
        'trigger_enable':False,\
        'trigger_timeout':10*1000,\
        'AC_pin':12,\
        'Heater_pin':26,\
        'path':"./",\
        'filemask':"DataLog_3_{2:04}-{1:02}-{0:02}.txt",\
        }
    
    def __init__(self,**kwargs):
        # pick out device specifications and add devices
        self._devices = []
        if 'devices' in kwargs:
            devices = kwargs.pop('devices')
            for d in devices:
                assert isinstance(d,i2c.I2c_device),\
                       "Expecting instance of I2c_device!"
                assert d.dev_class in (i2c.DEV_MEAS,i2c.DEV_ADC,),\
                       "Unsupported device class for device '{}'!"\
                       .format(d.dev_type)
                ## @@ check for device class as well.
                self._devices.append(d)
        else:
            devices = []
        # first set defaults, then overwrite with possible user input
        for kw in self._default:
            setattr(self,kw,self._default[kw])
        for kw in kwargs:
            assert kw in self._default,\
                   "Unknown keyword '{}!'".format(kw)
            setattr(self,kw,kwargs[kw])
        # initialize data list
        self._data = []

    def add_device(self,device):
        """ Append a new device to the end of the devices list. Note, that
        using the same device multiple times prompts a new measurement every
        time. Use cycling to access different 'channels' in one device. """
        assert isinstance(device,i2c.I2c_device),\
               "Expecting instance of I2c_device!"
        assert d.dev_class in (i2c.DEV_MEAS,i2c.DEV_ADC,),\
               "Unsupported device class for device '{}'!"\
               .format(d.dev_type)
        # append
        self._devices.append(device)

    def get_measurements(self):
        """ Returns the list of measurement values obatained by each device's
        get() method. """
        return [device.get() for device in self._devices]

    def start_measurement_loop(self, queue_cool, queue_heat, event):
        " Starts the measurement loop for this DataLogger. "
        # start plotting
        #plotobj = Plotobject()

        # Temperature control feedback loop initialization
        gpio.output(self.AC_pin,False)
        gpio.output(self.Heater_pin,False)
        T_Ref = 22.75
        Err_Old = 0.0
        Err = 0.0
        Err_Tot = 0.0
        Err_P = 0.0
        Err_I = 0.0
        Err_D = 0.0
        K_C = 1.5
        K_H = 1.0
        K_D = 3.0
        K_I = 0.0
        
        T_D = 3.0
        Tau = 5

        # New transfer function
        Save_Period = 5
        Memory_Length = 20
        Derivative_Time = 4
        Err_Vec = [0] * Memory_Length
        t_Vec = np.array([el for el in range(0,Memory_Length)])
        Exp_Vec = [math.exp(-el / Tau) for el in range(0,Memory_Length)]
        
        # @@ cheap and dirty!!
        Count = 0
        while not event.is_set():
            line_note = ""
            triggered = "0"
            # wait for trigger if triggered operation is selected
            if self.trigger_enable and self.trigger_pin != None:
                res = gpio.wait_for_edge(self.trigger_pin,\
                                         gpio.RISING,\
                                         timeout=self.trigger_timeout)
                if res == None:
                    line_note = "timeout"
                else:
                    line_note = "TR({})".format(res)
                    triggered = "1"
            # initialize empty data list
            ## @@ verify that there is no memory leak here (used .clear()
            ## @@ before, which is not supported in 2.7.9)
            self._data = []
            last_avg = time.time()
            while (time.time() - last_avg) < self.avg_period:
                # get a measurement
                last = time.time()
                self._data.append(self.get_measurements())
                # wait for next measurement
                while (time.time() - last) < self.meas_period:
                    pass
            #First few measurements bad (~125) for some reason.
            #print(self._data)
            #print("")
            avg = [sum([data[i] for data in self._data[2:]])\
                   /(len(self._data) - 2) \
                   for i in range(0,len(self._data[0]))]
            # build filename with current date
            now = time.localtime()
            outfile = self.path + self.filemask.\
                      format(now.tm_mday,now.tm_mon,now.tm_year)
            # build timestamp
            timestamp = "{:02}:{:02}:{:02}".\
                        format(now.tm_hour,now.tm_min,now.tm_sec)
            # build line
            line = ",".join(["{:.4f}".format(a) for a in avg])
            line += "," + triggered
            # print to stdandard output
            print_line = " , ".join(["{:.4f}".format(a) for a in avg])
            print(outfile + " < " + print_line + "   @ " \
                  + timestamp + "   " + line_note)
            # append to file and add to plot every 20th iteration
            if not (Count % Save_Period):
                with open(outfile,'a') as f:
                    f.write(timestamp + "," +line+"\n")
                # pass data for plotting
                #plotobj.add_plot_data(now, avg, triggered)

            # Regulate damper valve position
            T = (avg[9] + avg[5])/2.0
            Err_Old = Err
            Err = (T - T_Ref)
            if Err < 0:
                K = K_H
            else:
                K = K_C
                
            Err_P = K * Err

            #Prepend to error vec. Most recent error first.
            Err_Vec.insert(0,Err)
            Err_Vec.pop()
            #print(Err_Vec)
            Err_I = K_I / Tau * sum([Exp_Vec[el] * Err_Vec[el] for el in range(Memory_Length)])
            #Err_I = Err_I + K / T_I * Err

            Fit = np.polyfit(t_Vec[0:Derivative_Time],np.array(Err_Vec[0:Derivative_Time]),1)
            print(Err_Vec[0:Derivative_Time])
            Err_D = K_D * T_D * (-Fit[0]) #Negative sign because array is time-reversed...
            #Err_D = K * T_D * (Err - Err_Old)
            
            Err_Tot = Err_P + Err_I + Err_D
            Scaled_Err = np.tanh(Err_Tot)
            Duty_Cycle_Cool = np.maximum(Scaled_Err,0.0)
            Duty_Cycle_Heat = 0.20 + 0.80 * np.maximum(-Scaled_Err,0.0)
            print("")
            print("Temp: ",T, "Prop Err: ", Err_P, "Int Err: ", Err_I, "Der Err: ",
                  Err_D, "Tot Err: ", Err_Tot, "Scaled Err: ", Scaled_Err,
                  "Duty Cycle Cool: ", Duty_Cycle_Cool, "Duty Cycle Heat: ", Duty_Cycle_Heat)
            print("")
            queue_cool.put(Duty_Cycle_Cool)
            queue_heat.put(Duty_Cycle_Heat)
##            Draw = rnd.uniform(-1,1)
##            if Draw < Scaled_Err:
##                gpio.output(self.AC_pin,True)
##            else:
##                gpio.output(self.AC_pin,False)

            Count = Count + 1

    def Control_Valve_Cool(self, queue, event):
        Duty_Cycle = 0.0
        time.sleep(5)
        while not event.is_set():
            if not queue.empty():
                Duty_Cycle = queue.get()
            gpio.output(self.AC_pin,True)
            time.sleep(Duty_Cycle * 1.0)
            gpio.output(self.AC_pin,False)
            time.sleep((1.0 - Duty_Cycle) * 1.0)

    def Control_Valve_Heat(self, queue, event):
        Duty_Cycle = 0.0
        time.sleep(5)
        while not event.is_set():
            if not queue.empty():
                Duty_Cycle = queue.get()
            gpio.output(self.Heater_pin,True)
            time.sleep(Duty_Cycle * 1.0)
            gpio.output(self.Heater_pin,False)
            time.sleep((1.0 - Duty_Cycle) * 1.0)

def triggered_trace(trigger_pin,devices,timeout=-1,tmax=None,nmax=10,\
                    dt=None):
    """ Performs a triggered measurement, accumulating samples either until
    'nmax' samples are reached or until theloop has run for time 'tmax'.
    Optionally can force time intervals of measurements to 'dt'.
    The loop starts after a rising flank has been detected on 'trigger_pin',
    or once the 'timeout' time is elapsed. """
    # reshape and validate input
    if type(devices) not in (tuple,list,):
        devices = [devices]
    assert nmax != 0 or tmax != 0,"Missing break condition!"
    # initialize empty data array
    data = []
    # start by waiting for the trigger
    gpio.wait_for_edge(trigger_pin,gpio.RISING,timeout=timeout)
    print('Go!')
    start=time.clock()
    # based on choices: slightly different loops
    if dt == None:
        if tmax == None:
            # continuous loop until nmax reached
            while len(data) < nmax:
                data.append([time.clock()-start]\
                            +[d.get() for d in devices])
        else:
            # continuous loop until nmax or tmax reached
            while (len(data) < nmax) and (time.clock()-start < tmax):
                data.append([time.clock()-start]\
                            +[d.get() for d in devices])
    else:
        if tmax == None:
            # continuous loop until nmax reached, waiting for dt
            while len(data) < nmax:
                data.append([time.clock()-start]\
                            +[d.get() for d in devices])
                while (time.clock()-start < dt*len(data)):
                    pass
            # continuous loop until nmax or tmax reached, waiting for dt
            while (len(data) < nmax) and (time.clock()-start < tmax):
                data.append([time.clock()-start]\
                            +[d.get() for d in devices])
                while (time.clock()-start < dt*len(data)):
                    pass
    # hand back the measurement result
    return data

            
if __name__ == "__main__":       
    print('RELEASE THE KRAKEN!!!')
    # setup a trigger pin
    # (BCM indexing; pins on break-out board are 12, 16, 26)
    gpio.setmode(gpio.BCM)
    gpio.setup(16,gpio.IN)
    gpio.setup(12,gpio.OUT) #cooling
    gpio.setup(26,gpio.OUT) #heating

    # setup i2c devices of interest
    # 8-channel i2c bus expander
    tca = i2c.TCA9548A(addr=0x70)
    tca.disable_all()
    # initially enable channels with devices
    tca.set_channels([1,1,1,1,1,1,0,1]) 
    # HIH8121: array of temp/humidity measurements
    #Currently: #1 - Far Side of Test Table #2 - Near MOT (Upper), #3 - Middle of Test Table, #4 - High Power Lasers,
    #5 - Laser Table (Under Lids, Near TAs), #7 - Near Side of Test Table,
    #7 - Above Kraken: Disabled
    hih_channels = [1,2,3,4,5,7]
    hih = [i2c.HIH8121(addr=0x27,cycle=[0,1],\
                       group={'me':ch,'channels':hih_channels,\
                              'switch':tca})\
           for ch in hih_channels]
    # ADS1015: 4-channel ADC (currently disabled)
    adc = i2c.ADS1015(addr=0x48,cycle=[0b100,0b101,0b110,0b111])

    ## Some triggered trace taking ...
    #print('Waiting for trigger ...')
    #tt = triggered_trace(16,[adc,adc,adc,adc],\
    #                     dt=0.004,tmax=2.0,nmax=100000)
    #with open("test_trace.txt",'w') as f:
    #    for t in tt:
    #        f.write(",".join(["{}".format(val) for val in t])+"\n")
    
    # create a datalogger object for the devices
    log = DataLogger(filemask="DataLog_Triggered-QPD_{2:04}-{1:02}-{0:02}.txt",\
                     path="/home/pi/Documents/Data Log/Triggered-QPD/",\
                     devices=[adc,adc,adc,adc,hih[0],hih[0],hih[1],hih[1],hih[2],hih[2],hih[3],hih[3],hih[4],hih[4],hih[5],hih[5]],\
                     trigger_pin=16,\
                     trigger_enable=True,
                     trigger_timeout=1*1000,
                     AC_pin=12)
    # start the measurement loop
    try:
        print('Press CTRL-C to exit loop.')
        #log.start_measurement_loop()
        pipeline_cool = queue.Queue(maxsize=1)
        pipeline_heat = queue.Queue(maxsize=1)
        event = threading.Event()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            executor.submit(log.start_measurement_loop, pipeline_cool, pipeline_heat, event)
            executor.submit(log.Control_Valve_Cool, pipeline_cool, event)
            executor.submit(log.Control_Valve_Heat, pipeline_heat, event)
    except KeyboardInterrupt:
        print('Goodbye!')
        event.set()
    finally:
        gpio.cleanup()

