import time
import smbus

def array2bin(array):
    " Takes an array of ones and zeros and interprets the contents \
    as a binary number. Returns the corresponding integer."
    # There may be better, predefined ways of doing this.
    out = 0                             # initialize output
    for a in array:
        assert a==0 or a==1             # check input
        out = (out<<1) + a              # shift one bit left and add new LSB
    return(out)

def int2MSbLSb(num):
    " Splits a sixteen-bit integer into two 8-bit values (most and least \
    significant bytes. "
    # There may be better, predefined ways of doing this.
    MSb = 0
    LSb = 0
    # Build MSb
    for a in range(0,8):
        Bit = num//(2**(15-a))
        MSb = (MSb<<1) + Bit
        num -= Bit*(2**(15-a))
    # Build LSb
    for a in range(0,8):
        Bit = num//(2**(7-a))
        LSb = (LSb<<1) + Bit
        num -= Bit*(2**(7-a))
    assert num == 0
    return(MSb,LSb)

def byte2bits(num,n=8):
    " Gives back an array of 1 and 0, representing the individual bits \
    of the binary representing num. n specifies the length of the character \
    array."
    # There may be better, predefined ways of doing this.
    string = bin(num).split('b')[1]
    while (len(string) < n):
        string = '0'+string
    # convert to array of numbers
    out = []
    for i in range(0,len(string)):
        out.append(int(string[i]))
    return(out)

class I2c_device:
    " API for generic i2c devices; provides routines for setting \
    class parameters, reading and writing to the device and setting \
    the address."

    TYPE = "generic i2c device"
    VALID_ADDR = list(range(0,0b1111111))
    DEFAULT = {'bus':smbus.SMBus(1),\
               'addr':0x00,\
               'addr_pin':[0,0,0,0,0,0,0],\
               'addr_mask':"gfedcba"}
        
    def __init__(self,**kwargs):
        self.setpar(self.DEFAULT)
        self.setpar(**kwargs)

    def __str__(self):
        return self.TYPE + " at 0x{0:02X}".format(self.addr)

    def setpar(self, *arg, **kwargs):
        " Savely set parameters. Function only sets parameters defined\
        in self.DEFAULT. Value checks are done here. "
        if len(arg) > 0:
            if type(arg[0]) is dict: kwargs = arg[0]
            else: raise ValueError("argument must be a dictionary")
        for kw in kwargs:
            if kw in self.DEFAULT:
                if kw == "addr":
                    assert kwargs[kw] in self.VALID_ADDR
                self.__setattr__(kw,kwargs[kw])
            else:
                raise KeyError(self.TYPE + " does not support attribute {}".format(kw))

    def write(self,data=None,ctrl=None):
        "Generic API for writing data to an i2c device. Uses the \
        functinons provided by the smbus package. Individual devices \
        may require different commands here -- consult datasheet. \
        Bytes for data and ctrl should are given as 8-bit integers."
        if ctrl is None:
            if data is None:
                # write a zero byte -- used to request a measurement
                # from some devices 
                self.bus.write_byte(self.chip_addr,0x00)    
            else:
                assert type(data) is int and data >= 0 and data < 2**8
                # write data to a device without specifying a control
                # byte, register pointer, or else
                self.bus.write_byte(self.chip_addr,data)
        else:
            assert type(ctrl) is int and ctrl >= 0 and ctrl < 2**8
            if data is None:
                # write only a control byte to the device
                self.bus.write_byte(self.addr,ctrl)
            else:
                # write control byte followed by data byte(s)
                if type(data) is list:
                    assert type(data) is int and data >= 0 and data < 2**8
                    self.bus.write_i2c_block_data(self.addr,ctrl,data)
                else:
                    for x in data:
                        assert type(x) is int and x >= 0 and x < 2**8    
                    self.bus.write_i2c_block_data(self.addr,ctrl,[data])

    def read(self,ctrl=None,nbytes=1):
        "Generic API for reading data from an i2c device. Uses the \
        functinons provided by the smbus package. Individual devices \
        may require different commands here -- consult datasheet. \
        Bytes for data and ctrl should are given as 8-bit integers."        
        nbytes = int(nbytes)
        assert nbytes > 0
        if nbytes > 1:
            if ctrl is None: ctrl = 0x00
            assert type(ctrl) is int and ctrl >= 0 and ctrl < 2**8
            # read nbytes bytes from device
            data = self.bus.read_i2c_block_data(self.addr,ctrl,nbytes)
        else:
            if ctrl is None:
                # read a single byte without sending a control byte
                data = self.bus.read_byte(self.addr)
            else:
                # read a single byte in same way as multiple bytes
                data = self.bus.read_i2c_block_data(self.addr,ctrl,nbytes)
        return data

    def set_address(self,addr=None,addr_pin=None):
        " Sets the device address eithre directly via addr or using\
        a pin configuration and self.addr_mask."
        if addr_pin:
            if type(addr_pin) is not list: addr_pin = [addr_pin]
            addr_str = self.addr_mask
            # build address from pin configuration
            for i in range(0,len(addr_pin)):
                j = addr_str.find(chr(97+i))
                if j > -1: addr_str = addr_str[0:j] + str(addr_pin[i]) + addr_str[(j+1)::]
            addr = 0
            for s in addr_str: addr = (addr<<1) + int(s)
            self.set_address(addr=addr)
        if addr:
            assert addr in self.VALID_ADDR
            self.addr = addr
            # update pin configuration to match address
            addr = str(bin(addr))
            for i in range(0,len(self.addr_mask)):
                s = self.addr_mask[i]
                if s == '0' or s == '1': pass
                else:
                    j = ord(s)-97
                    self.addr_pin[j] = int(addr[2+i])



# Four-channel i2c switch
class TCA9545A(I2c_device):
    " This class provides i2c interface functions to a four-channel \
    I2C switch chip (ti TCA9545A) with reset and interrupts. \
    Currently, the functions arepurely i2c based, i.e. communication \
    onloy happens through SDA and SCL channels. Reset & Interrup need \
    to be implemented with additional GPIO channels. (ST-2016-09) \
    Chip also supports interrupts -- not implemented here."

    TYPE = 'TCA9545A'
    DEFAULT = {'bus':smbus.SMBus(1), \
               'addr':0x70, \
               'addr_mask': "xxxxxxx"}

    def __init__(self,**kwargs):
        self.setpar(self.DEFAULT)
        self.setpar(**kwargs)

    def set_channels(self,settings):
        " Enables/disables channels according to bit xi=1/0 in \
        settings = [x0,x1,x2,x3]."
        assert type(settings) is lis and len(settings) == 4
        ctrl_byte = 240 + settings[0] + settings[1]*2 + settings[2]*4 + settings[3]*8
        # DEBUG! cannot set [1,0,1,0] -- missing acknowledge from slave
        # (hardware issue?)
        self.write(ctrl=ctrl_byte)

    def get_settings(self):
        " Returns the current channel settings [x0,x1,x2,x3]."
        data = byte2bits(self.read())
        # only return the channel settings (4 LSB), discard interrupts (4 MSB)
        # mind the order: xxxx3210
        return [data[7],data[6],data[5],data[4]]
    
    def enable(self, channels):
        " Enables one or more channels."
        if type(channels) is not list: channels = [channels]
        assert max(channels) <= 3; assert min(channels) >= 0
        settings = self.get_settings()
        for ch in channels: settings[ch] = 1
        self.set_channels(settings)

    def disable(self, channels):
        " Disables one or more channels."
        if type(channels) is not list: channels = [channels]
        assert max(channels) <= 3; assert min(channels) >= 0
        settings = self.get_settings()
        for ch in channels: settings[ch] = 0
        self.set_channels(settings)

    def enable_all(self):
        " Enables all channels."
        self.set_channels([1,1,1,1])

    def disable_all(self):
        " Disables all channels."
        self.set_channels([0,0,0,0])    



class DAC8574(I2c_device):
    " This class provides the i2c interface to a DAC8574 chip. Consult \
    datasheet for details on ratings and programming. (ST-2016-09)"
    # mind offsets and non-linearities for sensitive applications!

    BIT_DEPTH = 16
    TYPE = 'DAC8574'
    DEFAULT = {'bus':smbus.SMBus(1), \
               'addr_pin':[0,0,0,0], \
               'addr':0x4c, \
               'Vref':2.486, \
               'Voff':0.019}

    def __init__(self,**kwargs):
        # first initialize with default attribute, then update
        # with kwargs
        self.setpar(self.DEFAULT)
        self.setpar(**kwargs)

    def set_output(self,ch,value,units=None):
        " Sets the output of channel ch (0-3 = A-D) to value*Vref. "
        assert ch >= 0 and ch < 4
        ch = [ch%2, ch//2]
        # convert to volts if units are set
        if units == "V": value = (value-self.Voff)/(self.Vref-self.Voff)
        # now value is in relative units 0..1
        assert value >=0 and value <= 1
        value = int(value * (2**self.BIT_DEPTH - 1))
        # build control byte and mos/least significant data bytes
        ctrl_byte = [self.pin_A[3],self.pin_A[2],0,1,0,ch[1],ch[0],0]
        ctrl_byte = array2bin(ctrl_byte)
        MS_byte, LS_byte = int2MSbLSb(value)
        # write to device
        self.write(ctrl=ctrl_byte,data=[MS_byte,LS_byte])

    def power_down(self,ch,*arg):
        " Powers down DAC channel ch (0-3 = A-D) with selected mode. \
        0: High-Z out; 1: 1kOhm to gnd; 2: 100kOhm to gnd; 3: High-Z (?) \
        Default: mode = 0."
        # The syntax is similar to the one described in self.set_output.
        # check mode argument; if none given, set default to mode = 0
        assert len(arg) <= 1
        if len(arg) == 0: mode = 0
        else: mode = arg[0]
        
        if ch == -1:
            # ch=-1: all channels are powered down
            for i in range(0,4): self.power_down(i,mode)
        else:
            # check and modify channel & mode input
            assert ch >= 0 and ch < 4
            ch = [ch%2, ch//2]
            assert mode >= 0 and mode < 4
            mode = [mode%2, mode//2]            
            # build control byte
            ctrl_byte = [self.pin_A[3],self.pin_A[2],0,1,0,ch[1],ch[0],1]
            ctrl_byte = array2bin(ctrl_byte)
            # build MSb (power down command); LSb is 0.
            # The power-down mode is controlled with the first two bits
            MS_byte = ((mode[1]<<1) + mode[0])<<6
            # write to device
            self.write(ctrl=ctrl_byte,data=[MS_byte,0])

    def set_address(self,A):
        " Sets the chip address based on the configuration A of the \
        four addressing pins A0-3; function is automatically called \
        when setting self.pin_A. Input A must be of form [A0,A1,A2,A3] \
        with all values being either 0 or 1."
        # the i2c address is a 7bit integer; for the Ti DAC8574,
        # the first five bit are factory preset to 10011, and the next
        # two following bits are determined (in this order) by the pins
        # A1 and A0. Setting A1=LO and A0=HI gives 0b1001101 = 77 = 0x4d

        assert len(A) == 4                          # check input
        for a in A: assert a==0 or a==1             # check input
        address = ((0b10011<<1) + A[1] <<1) + A[0]  # build address
        super().__setattr__('addr',address)         # set address            

    def __setattr__(self,name,value):
        " Modified to match pin_A configuratyion and address "
        # catch changes to attributes to avoid inconsistencies
        if name == 'pin_A':
            # automatically set chip_addr according to pin_A
            self.set_address(value)                 # calc and set chip_addr
            super().__setattr__(name,value)         # set pin_A   
        elif name == 'addr':
            # validate chip address and update pins A0 and A1
            assert value > 75                       # check input
            assert value < 80                       # check input
            A = self.pin_A                          # get values of A2 and A3
            A[0] = (value-76)%2                     # calc A0
            A[1] = (value-76)//2                    # calc A1
            self.pin_A = A                          # set pin_A (recursive)
        else:
            super().__setattr__(name,value)

        

class ADS1115:
    " This class provides the i2c interface to a ADS1115 chip. Consult \
    datasheet for details on ratings and programming. (ST-2016-06)"
    # mind offsets and non-linearities for sensitive applications!

    BIT_DEPTH = 16
    TYPE = 'ADS1115'
    VALID_ADDRESS = [0x48,0x49,0x4a,0x4b]
    DEFAULT = {'bus':smbus.SMBus(1), \
               'addr':0x48, \
               'PGA': 0b010, \
               'MUX': 0b000, \
               'DR': 0b100, \
               'MODE': 0b1, \
               'OS': 0b1, \
               'Vref':2.048, \
               'Voff':0, \
               'is_config':False}
    FULL_SCALE = [6.144,4.096,2.048,1.024,0.512,0.256,0.256,0.256]
    MUX_SETTINGS = ["AIN0-AIN1","AIN0-AIN3","AIN1-AIN3","AIN2-AIN3",\
                    "AIN0-GND","AIN1-GND","AIN2-GND","AIN3-GND"]
    DATA_RATE = [8,16,32,64,128,250,475,860]
    
    def __init__(self,**kwargs):
        self.setpar(self.DEFAULT)
        self.setpar(**kwargs)

    def get_conversion(self):
        " Reads the conversion register of the chip "
        # update config if it has been changed.
        if self.is_config == False:
            self.set_config()
        # if MODE == 1: single-shot conversion; request conversion and wait
        # for it to be finished
        if self.MODE == 1:
            self.request()
            config = self.get_config()
            while(config['OS'] == 0):
                config = self.get_config()
        data = self.read(ctrl=0b0000000,nbytes=2)
       # convert to voltage based on PGA settings; delta = FS/2**15
        FS = self.FULL_SCALE[self.PGA]
        value = (data[0] << 8) + data[1]
        if value < 0x8000:  # positive values: 0 to FS-delta = 0x0000 to 0x7FFF
            value = FS/(2**15)*value
        else:               # negative values: -FS to -delta = 0x8000 to 0xFFFF
            value = -FS + FS/(2**15)*(value - 0x8000)

        return(value)
    

    def request(self):
        " Triggers a single-shot conversion by setting OS to 1 and sending the \
        new config to the ADC."
        OS = self.OS
        self.OS = 0b1
        self.set_config()
        self.OS = OS
    
    def list_settings(self):
        " Lists the possible configurations; for look-up and debugging."
        print("MUX Settings (3-bit): ")
        for i in range(0,8):
            print("  #{} {}: {}".format(i, bin(i), self.MUX_SETTINGS[i]))
        print("PGA Settings in terms of full scale (3-bit):")
        for i in range(0,8):
            print("  #{} {}: +/-{}V".format(i, bin(i), self.FULL_SCALE[i]))
        print("DR Settings (3-bit):")
        for i in range(0,8):
            print("  #{} {}: {}SPS".format(i, bin(i), self.DATA_RATE[i]))
        print("OS (1-bit): serves as single-conversion start when set to 1.")
        print("OS (1-bit) when reading config:")
        print("  #0 0b0: currently performing conversion")
        print("  #1 0b1: not currently performing conversion")
        print("MODE (1-bit):")
        print("  #0 0b0: continuous conversion")
        print("  #1 0b1: single shot mode (triggered by setting OS)")
    
    def set_config(self):
        " Applies configuration changes to the ADC. "
        ctrl_byte = 0b00000001                # register pointer 0b01 -> config
        # build MS_byte: [OS, MUX(3), PGA(3), MODE]
        MS_byte = (((self.OS << 3) + self.MUX << 3) + self.PGA << 1) + self.MODE
        # build LS_byte: [DR(3), COM_MODE, COMP_POL, COMP_LAT, COMP_QUE(2)]
        LS_byte = (self.DR << 5) + 0b11
        # write to i2c bus using the smbus package
        self.write(ctrl=ctrl_byte,data=[MS_byte,LS_byte])
        self.is_config = True

    def get_config(self):
        " Reads current cofiguration from the ADC. Hands back a dictionary \
        with the decoded configuration values. "
        data = self.read(ctrl=0b00000001,nbytes=2)
        MSB = byte2bits(data[0])
        LSB = byte2bits(data[1])
        out = {'OS':MSB[0],'MUX':array2bin(MSB[1:4]), \
               'PGA':array2bin(MSB[4:7]), 'MODE':MSB[7], \
               'DR':array2bin(LSB[0:3]), 'COMP_MODE':LSB[3], \
               'COMP_POL':LSB[4], 'COMP_LAT': LSB[5], \
               'COMP_QUE':array2bin(LSB[6:])}
        return(out)

    def set_address(self,addr_str):
        " Sets the chip address based on the string addr_str. This can be \
        either GND, Vdd, SDA or SCL (case insensitive), and reflects which \
        pin the address pin is connected to."
        # the i2c address is a 7bit integer; for the Ti ADC115,
        # the first five bit are factory preset to 10010, and the next
        # two following bits are determined by the connection of the address
        # pin: GND=0b00, Vdd=0b01, SDA=0b10, SCL=0b11.
        addr = {'gnd':0b1001000, 'vdd':0b1001001, 'sda':0b1001010, 'scl':0b1001011}
        assert addr_str.lower() in addr                   # check input
        if not self.chip_addr == addr[addr_str.lower()]:
            self.is_config = False
        self.addr = addr[addr_str.lower()]    # set address


class ADS1015(ADS1115):
    " The ADS1015 (12-bit version of the ADS1115) is controlled in the \
    same way as the ADS1115. Since the transmitted dataformat is 16-bit, \
    with the last four LSBs set to zero, the same conversion as in the \
    16-bit case can be used. (ST-2016-07)"
    # nothing to be changed. Should just work exactly the same.
    


class HIH8121:
    " This class provides the i2c interface to a Honeywell HIH8182 humidity \
    and temperature sensor. Consult datasheet for details on ratings and \
    programming. (ST-2016-07)"

    BIT_DEPTH = 14
    TYPE = 'HIH8121'
    DEFAULT = {'bus':smbus.SMBus(1), \
               'chip_addr':0x27, \
               'hum_range':100, \
               'hum_offset':0, \
               'temp_range':165 ,\
               'temp_offset':-40}    

    def __init__(self,**kwargs):
        # first initialize with default attribute, then update
        # with kwargs
        self.setParameters(self.DEFAULT)
        self.setParameters(**kwargs)


    def setParameters(self, *arg, **kwargs):
        # set parameters only if defined in DEFAULT
        if len(arg) > 0:
            if type(arg[0]) is dict:
                kwargs = arg[0]
            else:
                raise ValueError("setParameters *arg not a dictionary")
        for kw in kwargs:
            if kw in self.DEFAULT:
                self.__setattr__(kw,kwargs[kw])
            else:
                raise KeyError("class HIH8182 does not support attribute {}".format(kw))


    def request(self):
        " Requests a measurement. "
        # only need to send the address with the write-bit to initiate
        # measurement. This is accomplished with the line below
        self.bus.write_byte(self.chip_addr,0x00)
        

    def get_data(self):
        " Read humidity and temperature data from the chip. "
        # read from the i2c bus, calling the respective address.
        # setting the command byte to 0x00 seems to neglect it (at least no
        # command byte is listed in the communication protocol for this transaction
        # -- see datasheet / application note -- and manually sending an address
        # byte plus high R/iW bit followed by 0x00 causes an IOError). Final
        # argument is the number of bytes to read.
        data = self.bus.read_i2c_block_data(self.chip_addr,0x00,4)
        
        # first two bits give the chip's status 0b00 for normal; 0b01 for stale data
        status = data[0]>>6 
        # next 6+8 bits are the humidity data
        hum_raw = ((data[0]-(status<<6)) << 8) + data[1]
        humidity = self.hum_range*hum_raw/(2**self.BIT_DEPTH-2) \
                   + self.hum_offset
        
        # next 8+6 bits are the temperature data; last two bits do not matter
        temp_raw = (data[2] << 8)+data[3] >> 2
        temperature = self.temp_range*temp_raw/(2**self.BIT_DEPTH-2) \
                      + self.temp_offset

        return(humidity,temperature,status)


    def __setattr__(self,name,value):
        # catch changes to attributes to avoid inconsistencies
        if name == 'chip_addr':
            # validate chip address (HIH8128 has a single address: 0x27)
            # different hardware adresses are available upon request, but not
            # standard
            assert value == 0x27                    # check input
            super().__setattr__(name,value)
        else:
            super().__setattr__(name,value)        



# main process for testing:
#tca.set_channels([1,0,1,0])
#tca.set_channels([0,0,0,1])
#print(tca.get_settings())

dev = I2c_device(addr_mask = "110ac1",addr_pin=[0,1,0,1])
print(dev, dev.addr_pin)
dev.set_address(addr_pin=[1,1,1,1])
print(dev, dev.addr_pin)
dev.set_address(addr=0b110011)
print(dev, dev.addr_pin)

