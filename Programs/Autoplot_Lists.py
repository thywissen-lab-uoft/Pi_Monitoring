import matplotlib.pyplot as plt
from collections import deque
import datetime
import time
import matplotlib.dates as mdates


class Plotobject():
    _plotframe = int(24*60*60/120)                            # saves every minute for 1 hour(s) (plot time frame for long time plot)
    _short_t = int(3*60*60/120)                               # plot time frame for short time plot
    _cycle_t = int(1.25*60/0.25)                               # plot one cycle
    _data_deque = deque(maxlen=_plotframe)                    # holding measurement data
    _time_deque = deque(maxlen=_plotframe)                    # holding time data
    _cycle_data_deque = deque(maxlen=_cycle_t)
    _cycle_time_deque = deque(maxlen=_cycle_t)
    _fig1, _ax1 = plt.subplots(2, 1)                          # long time plot figure, _ax1 array of axis
    _fig2, _ax2 = plt.subplots(2, 1)                          # short time plot figure
    _fig3, _ax3 = plt.subplots(1, 1)                          # cycle plot figure
#    _figtext = _ax2[2].text(0.05, 0.05, " ", verticalalignment='bottom', transform=_ax1[2].transAxes) # figure text to indicate whether beam alignment measurement is on/off
    
    def __init__(self):
        print("The figure layout will normalise after two measurements have been received. The use of \
matplotlib.pyplot.pause() will cause the warning 'MatplotlibDeprecationWarning: Using default event loop \
until function specific to this GUI is implemented'. It seems there is no need for concern. For a discussion \
confer https://github.com/matplotlib/matplotlib/pull/8185/commits/872675ce6d015b80e809c36aad60d4a52004d0a8 ;\
https://github.com/matplotlib/matplotlib/pull/8185")
        plt.ion()                                             # switch to interactive mode to be able to go back and forth between class and script calling class
        plt.show()                                            # display figure

    # Funtion to clear the figures. Needed to remove old points from plot.
    def clear_fig(self):
        for axis in range(len(self._ax1)):
            self._ax1[axis].clear()
            self._ax2[axis].clear()
        self._ax3.clear()

    # Fumction to determine the number of leading voltage values and pairs of temperature-humidity pairs
    # data:            type: list, contains voltages and alternating temperature and humidity values
    def find_valtype(self, data):
        nb_voltval = sum([el<4.0 for el in data])
        nb_temphumpair = int((len(data)-nb_voltval)/2)        # number of temp/humidity value pairs
        if nb_temphumpair == 0:
                print("Data contains non-matching number of columns")  # code requires temp/hum pairs
        return [nb_voltval, nb_temphumpair]

    # Function to produce plotable data from deque.
    # valtype_nbs:    type: list, elements: 0 = number of voltage values, 1 number of temp/hum value pairs
    def extract_data(self, valtype_nbs):
        value_list, volt_list = [[], []], []                  # default one column for temperature, humidity, voltage. latter for now seperated
        ############ set-up list sizes with sublist per 'device' ################
        for voltval in range(valtype_nbs[0]):
            volt_list.append([])
        for columns in value_list:
            for nb in range(valtype_nbs[1]):                  # add a sublist for each device
                columns.append([])
        ############ Sort data from deque into respective list ##################
        for measurement in self._data_deque:                  # single measurement data
            colcount = 0
            for column in value_list:
                subcolcount = 0                               # use col- and subcolcount to match value in measurement
                for subcol in column:
                    subcol.append(measurement[colcount+2*subcolcount+valtype_nbs[0]])
                    subcolcount +=1                           # every second column has the same data type
                colcount += 1
            voltcount = 0
            for voltcol in volt_list:                         # append leading voltage values
                voltcol.append(measurement[voltcount])
                voltcount += 1
        value_list.append(volt_list)                          # merge data sets
        return value_list                                     # value list does not need to stored longer than an add_plot_data function call

    def timelists(self):
        time_list_short = []
        if len(self._time_deque) > self._short_t:
            for i in range(self._short_t, 0, -1):
                time_list_short.append(self._time_deque[-i])
        else:
            for i in range(len(self._time_deque), 0, -1):
                time_list_short.append(self._time_deque[-i])
        return time_list_short

    # Function that contains the actual plot commands as well as the figure adaptations.
    # valtype_nbs:    type: list, elements: 0 = number of voltage values, 1 number of temp/hum value pairs
    # new_date:       type: time.localtime objec
    # trigger:        type: string, 0: measurement off - baseline voltage, 1: measurement on
    def plot_data(self, valtype_nbs, new_date, received_trigger): 
        plottable_data = self.extract_data(valtype_nbs)       # deque data is not readily plotable. Produce list
        style = ['b-', 'r-', 'g-', 'c-', 'm-',  'y-', 'k-', 'b-.', 'r-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        style2 = ['b-.', 'r-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        time_list_short = self.timelists()                           # time data for short time plots
        ### plotting humidity data ###
        self._ax1[0].set_ylabel("Humidity in %")
        self._ax2[0].set_ylabel("Humidity in %")
        #self._ax3[0].set_ylabel("Humidity in %")
        self._ax1[0].set_ylim([35,45])
        self._ax2[0].set_ylim([35,45])
        device_nb = 0                                         # used to match label and plotstyle for temperature and humidity of same device
        for subcol in plottable_data[0]:
            self._ax1[0].plot(self._time_deque, subcol, style[device_nb], label='Humidity{}'.format(device_nb+1))
            self._ax2[0].plot(time_list_short, subcol[-self._short_t:], style[device_nb], label='Humidity{}'.format(device_nb+1))
        #    if received_trigger:
        #        self._ax3[0].plot(time_list_cycle, subcol[-self._cycle_t:], style[device_nb], label='Humidity{}'.format(device_nb+1))
            device_nb += 1
        #self._ax3[0].legend(loc='upper left', fontsize = 'x-small')
        ### plotting temperature data ####
        self._ax1[1].set_ylabel("Temperature in Deg C")
        self._ax2[1].set_ylabel("Temperature in Deg C")
        #self._ax3[1].set_ylabel("Temperature in Deg C")
        self._ax1[1].set_ylim([21.5,24.5])
        self._ax2[1].set_ylim([21.5,24.5])
        device_nb = 0                                         # used to match label and plotstyle for temperature and humidity of same device
        for subbcol in plottable_data[1]:
            self._ax1[1].plot(self._time_deque, subbcol, style[device_nb], label='Temperature{}'.format(device_nb+1))
            self._ax2[1].plot(time_list_short, subbcol[-self._short_t:], style[device_nb], label='Temperature{}'.format(device_nb+1))
        #    if received_trigger:
        #        self._ax3[1].plot(time_list_cycle, subbcol[-self._cycle_t:], style[device_nb], label='Temperature{}'.format(device_nb+1))
            device_nb += 1
        #self._ax3[1].legend(loc='upper left', fontsize = 'x-small')
        ### plotting voltage data ###
        #self._ax1[2].set_ylabel("$V_{ADC}$ in V")
        #self._ax2[2].set_ylabel("$V_{ADC}$ in V")
        self._ax3.set_ylabel("$V_{ADC}$ in V")
        device_nb = 0                                         # used to match label and plotstyle for temperature and humidity of same device
        for subbcol in range(0,12):
        #    self._ax1[2].plot(self._time_deque, subbcol, style[device_nb], label='Voltage{}'.format(device_nb+1))
        #    self._ax2[2].plot(time_list_short, subbcol[-self._short_t:], style[device_nb], label='Voltage{}'.format(device_nb+1))
            if received_trigger:
                data = [self._cycle_data_deque[row][subbcol] for row in range(0,len(self._cycle_time_deque))]
                self._ax3.plot(self._cycle_time_deque, data, style[device_nb], label='Voltage{}'.format(device_nb+1))
            device_nb += 1
        self._ax3.legend(loc='upper left', fontsize = 'x-small')
        #_figtext.remove()
##        if trigger == "0":
##            self._figtext = self._ax2[2].text(0.05, 0.05, "off", verticalalignment='bottom', transform=self._ax1[2].transAxes)
##        else:
##            self._figtext = self._ax2[2].text(0.05, 0.05, "on", verticalalignment='bottom', transform=self._ax1[2].transAxes)
        ### Formatting time axis ticks and set date as title ###
        for ax in range(len(self._ax1)):
            self._ax1[ax].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self._ax2[ax].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self._ax1[ax].xaxis.set_tick_params(rotation = 45)
            self._ax2[ax].xaxis.set_tick_params(rotation = 45)
        self._ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self._ax3.xaxis.set_tick_params(rotation = 45)
##        self._fig1.suptitle("{1:02}-{0:02}-{2:04}".format(new_date.tm_mday, new_date.tm_mon, new_date.tm_year))
##        self._fig2.suptitle("{1:02}-{0:02}-{2:04}".format(new_date.tm_mday, new_date.tm_mon, new_date.tm_year))
##        self._fig3.suptitle("{1:02}-{0:02}-{2:04}".format(new_date.tm_mday, new_date.tm_mon, new_date.tm_year))
        plt.pause(0.000000001)                               # figure should be updated after plt commands. plt.show()/plt.draw() do not work, plt.pause() does
    
    # Main function of class.
    # new_datetime:    type: list of datetime objects
    # data:            type: list of lists, contains voltages and alternating temperature and humidity values
    # trigger:         type: list of strings, 0: measurement off - baseline voltage, 1: measurement on
    def add_plot_data(self, received_trigger, new_datetime_fast, new_data_fast, triggers_fast,
                      new_datetime_slow, new_data_slow, triggers_slow):
        self.clear_fig()
        self._data_deque.extend(new_data_slow) # saves data to deque for efficient storage of limited number of measurements
        self._time_deque.extend(new_datetime_slow)
        if(received_trigger):
            self._cycle_data_deque.extend(new_data_fast)
            self._cycle_time_deque.extend(new_datetime_fast)
        #valtype_nbs = self.find_valtype(new_data_slow[0][:])# find the numbers for value types 
        valtype_nbs = [0, 6]
        self.plot_data(valtype_nbs, time.localtime(), received_trigger)
        
