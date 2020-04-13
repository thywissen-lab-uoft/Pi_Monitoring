# Datalogging with the raspberry pi and i2c devices -- ST 03/2017
#
#   Running on 2.7.9; everything but gpio functionality works in 3.5 as well.
#
import py2C as i2c
import RPi.GPIO as gpio
import numpy as np
import time
import datetime
import smbus
import os
import concurrent.futures
import threading
import queue

class DataLogger():
    """ A simple data-to-file logging class. """

    #Some defaults defined here, but may be overwritten upon object construction.
    _default = {\
        'meas_period':0.1,\
        'avg_period':5.0,\
        'save_period':60.0,\
        'trigger_pin':None,\
        'trigger_enable':False,\
        'trigger_timeout':10*1000,\
        'AC_pin':12,\
        'Heater_pin':26,\
        'path':"./",\
        'filemask_temp':"Datalog_Temp.txt",\
        'filemask_fast':"Datalog_Fast.txt",\
        'filemask_slow':"Datalog_Slow_{2:04}-{1:02}-{0:02}.txt",\
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
                   "Uknown keyword '{}!'".format(kw)
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
        results_list = [ ]
        #Add a short pause between reading devices.
        for device in self._devices:
            results_list.append(device.get())
            time.sleep(0.010)
        return results_list
        #return [device.get() for device in self._devices]

    def start_measurement_loop(self, queue_cool, queue_heat, event):
        " Starts the measurement loop for this DataLogger. "
        print('STARTING MEASUREMENT LOOP')
        # @@ cheap and dirty!!
        last_save = time.time();
        now = datetime.datetime.now()

        # Temperature control feedback loop initialization
        gpio.output(self.AC_pin,False)
        gpio.output(self.Heater_pin,False)
        T_Ref = 22.00
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
        Exp_Vec = [np.exp(-el / Tau) for el in range(0,Memory_Length)]

        while True:
            line_note = ""
            triggered = "0"
            # wait for trigger if triggered operation is selected
            if self.trigger_enable and self.trigger_pin != None:
                #res = gpio.wait_for_edge(self.trigger_pin,\
                #                        gpio.RISING,\
                #                         timeout=self.trigger_timeout)
                res = gpio.input(self.trigger_pin)
                if res == 0:
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
            avg = [(sum([data[i] for data in self._data]) / len(self._data)) for i in range(0,len(self._data[0]))]
            fast_data = avg[0:12]
            slow_data = avg[12::]
            #Hardcode some data filtering... bad?
            #Subtract bias from bipolar ADC channels.
            avg[0] = avg[0] - 1.72
            avg[1] = avg[1] - 1.72
            avg[2] = avg[2] - 1.72
            avg[3] = avg[3] - 1.72
            #Dirty filtering of outliers
            if max(avg) > 50: 
                continue
            # build filename with current date
            now = datetime.datetime.now()
            outfile_temp = self.path + self.filemask_temp
            outfile_fast = self.path + self.filemask_fast
            outfile_slow = self.path + self.filemask_slow.\
                      format(now.day,now.month,now.year)
            # build timestamp
            timestamp = "{:04} {:02} {:02} {:02}:{:02}:{:02}.{:03}".\
                        format(now.year,now.month,now.day,now.hour,now.minute,now.second,now.microsecond)
            # build line
            fast_line = ",".join(["{:.4f}".format(a) for a in avg])
            fast_line += "," + triggered
            # print to standard output
            print_line = " , ".join(["{:.4f}".format(a) for a in avg])
            print(outfile_temp + " < " + print_line + "   @ " \
                  + timestamp + "   " + line_note)
            # append to file
            with open(outfile_temp,'a') as f:
                f.write(timestamp + "," +fast_line+"\n")
            # Create another file for slow temperature/humidity logging, and copy contents of temporary fast log to another file
            if (time.time() - last_save) > self.save_period:
                slow_line = ",".join(["{:.4f}".format(sd) for sd in slow_data])
                slow_line += "," + triggered
                with open(outfile_slow,'a') as f:
                    #Average here?
                    f.write(timestamp + "," +slow_line+"\n")
                #os.remove(outfile_fast)
                with open(outfile_temp,'r') as f1:
                    with open(outfile_fast,'w') as f2:
                        #f2.seek(0)
                        for line in f1:
                            f2.write(line)
                        #f2.truncate()
                os.remove(outfile_temp)
                last_save = time.time()

            # Regulate damper valve position
            T = (slow_data[1] + slow_data[3] + slow_data[7])/3.0
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

    def Control_Valve_Cool(self, queue, event):
        Duty_Cycle = 0.0
        time.sleep(5)
        while not event.is_set():
            if not queue.empty():
                Duty_Cycle = queue.get()
            print('Cooling')
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
            print('Heating')
            gpio.output(self.Heater_pin,True)
            time.sleep(Duty_Cycle * 1.0)
            gpio.output(self.Heater_pin,False)
            time.sleep((1.0 - Duty_Cycle) * 1.0)
            
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
    #tca.set_channels([0,0,0,0,0,0,0,0]) 
    # HIH8121: array of temp/humidity measurements
    #Currently: #2 - Near MOT (Upper), #3 - Test Table, #4 - High Power Lasers,
    #5 - Laser Table (Under Lids, Near TAs), #6 - Laser Table (Above Masters)
    hih_channels = [1,2,3,4,5,6]
    hih = [i2c.HIH8121(addr=0x27,cycle=[0,1],\
                       group={'me':ch,'channels':hih_channels,\
                              'switch':tca})\
           for ch in hih_channels]
    # ADCs (why does cycle appear to be off by 1?? 0b100 -> AIN3 - gnd??)
    adc1 = i2c.ADS1015(addr=0x48,cycle=[0b101,0b110,0b111,0b100])
    adc2 = i2c.ADS1115(addr=0x49,cycle=[0b101,0b110,0b111,0b100])
    adc3 = i2c.ADS1115(addr=0x4a,cycle=[0b101,0b110,0b111,0b100])
    
    # create a datalogger object for the devices
    log = DataLogger(filemask_temp="Datalog_Temp.txt",\
                     filemask_fast="Datalog_Fast.txt",\
                     filemask_slow="Datalog_Slow_{2:04}-{1:02}-{0:02}.txt",\
                     path="/home/pi/YDrive/share/Pi_Monitoring/Logs/",\
                     AC_pin=12,\
                     Heater_pin=26,\
                     devices=[adc1,adc1,adc1,adc1,adc2,adc2,adc2,adc2,adc3,adc3,adc3,adc3,
                              hih[0],hih[0],hih[1],hih[1],hih[2],hih[2],hih[3],hih[3],hih[4],hih[4],hih[5],hih[5]],\
                     meas_period=0.1,\
                     avg_period=0.1,\
                     save_period=120.0,\
                     trigger_pin=16,\
                     trigger_enable=True,\
                     trigger_timeout=0.1*1000)
    
    #Start the measurement loop
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

