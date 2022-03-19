import time
import smbus

SENSOR_I2C_ADDR = 0x18

# circuit: iis2dh.pdf, Figure 5

# referenced iis2dh_* functions: https://github.com/STMicroelectronics/iis2dh/blob/master/iis2dh_reg.c

REG_STATUS_REG_AUX = 0x07
REG_OUT_TEMP_L = 0x0C
REG_OUT_TEMP_H = 0x0D
REG_INT_COUNTER_REG = 0x0E
REG_WHO_AM_I = 0x0F
REG_TEMP_CFG_REG = 0x1F
REG_CTRL_REG1 = 0x20
REG_CTRL_REG2 = 0x21
REG_CTRL_REG3 = 0x22
REG_CTRL_REG4 = 0x23
REG_CTRL_REG5 = 0x24
REG_CTRL_REG6 = 0x25
REG_REFERENCE_DATACAPTURE = 0x26
REG_STATUS_REG = 0x27
REG_OUT_X_L = 0x28
REG_OUT_X_H = 0x29
REG_OUT_Y_L = 0x2A
REG_OUT_Y_H = 0x2B
REG_OUT_Z_L = 0x2C
REG_OUT_Z_H = 0x2D
REG_FIFO_CTRL_REG = 0x2E
REG_FIFO_SRC_REG = 0x2F
REG_INT1_CFG = 0x30
REG_INT1_SRC = 0x31
REG_INT1_THS = 0x32
REG_INT1_DURATION = 0x33
REG_INT2_CFG = 0x34
REG_INT2_SRC = 0x35
REG_INT2_THS = 0x36
REG_INT2_DURATION = 0x37
REG_CLICK_CFG = 0x38
REG_CLICK_SRC = 0x39
REG_CLICK_THS = 0x3A
REG_TIME_LIMIT = 0x3B
REG_TIME_LATENCY = 0x3C
REG_TIME_WINDOW = 0x3D
REG_Act_THS = 0x3E
REG_Act_DUR = 0x3F

IIS2DH_fs_bits = {2: 0b00, 4: 0b01, 8: 0b10, 16: 0b11}

IIS2DH_acceleration_factors = { # iis2dh_from_fs*_*_to_mg
	2: {'normal': 3.91, 'lp': 15.63, 'hr': 0.98},
	4: {'normal': 7.81, 'lp': 31.25, 'hr': 1.95},
	8: {'normal': 15.63, 'lp': 62.50, 'hr': 3.91},
	16: {'normal': 46.95, 'lp': 188.68, 'hr': 11.72},
}
IIS2DH_acceleration_mode_factors = {'normal': 64, 'lp': 256, 'hr': 16}


def twos_complement(value, bits):
	if(value & (1 << (bits - 1))) != 0:
		value = value - (1 << bits)
	return value

def read_value(register):
	value = bus.read_i2c_block_data(SENSOR_I2C_ADDR, register, 1)
	return value[0]

def read_value_double(register):
	value = [read_value(register), read_value(register + 1)] # read_i2c_block_data with length = 2 does not work correctly
	return (value[1] << 8) | value[0] # BLE in CTRL_REG4 has LSB at lower address as default

def write_value(register, value):
	bus.write_i2c_block_data(SENSOR_I2C_ADDR, register, [value])
	time.sleep(0.1)

def print_register(register):
	print(hex(register) + ": " + str(read_value(register)))


def convert_temperature(raw_value): # iis2dh_from_lsb_*_to_celsius
	return twos_complement(raw_value, 16) / 256 + 25

def convert_acceleration(raw_value): # iis2dh_from_fs*_*_to_mg
	return (twos_complement(raw_value, 16) / IIS2DH_acceleration_mode_factors[sensor_mode]) * IIS2DH_acceleration_factors[sensor_range][sensor_mode] / 1000



sensor_odr = 0b1001	# see Table 28 in data sheet
sensor_range = 2	# 2 | 4 | 8 | 16
sensor_mode = "normal"	# normal | lp | hr (low power, high resolution)


bus = smbus.SMBus(1)


if read_value(REG_WHO_AM_I) == 0b00110011:
	print("Sensor IIS2DH found")
else:
	print("Unknown sensor")
	exit()


# configure sensor

ctrl_reg1_value = 0b00000111 # enable all three axes
ctrl_reg1_value |= (sensor_odr << 4) # set ODR bits
if sensor_mode == "lp":
	ctrl_reg1_value |= (1 << 3) # set LPen bit
write_value(REG_CTRL_REG1, ctrl_reg1_value)

ctrl_reg4_value = 0b10000000 # BDU = 1
ctrl_reg4_value |= (IIS2DH_fs_bits[sensor_range] << 4) # set FS bits
if sensor_mode == "hr":
	ctrl_reg4_value |= (1 << 3) # set HR bit
write_value(REG_CTRL_REG4, ctrl_reg4_value)

write_value(REG_TEMP_CFG_REG, 0b11000000) # enable temperature sensor


# read values

while True:
	print("")
	print("T: " + "{:.2f}".format(convert_temperature(read_value_double(REG_OUT_TEMP_L))))
	print("x: " + "{:.4f}".format(convert_acceleration(read_value_double(REG_OUT_X_L))))
	print("y: " + "{:.4f}".format(convert_acceleration(read_value_double(REG_OUT_Y_L))))
	print("z: " + "{:.4f}".format(convert_acceleration(read_value_double(REG_OUT_Z_L))))
	time.sleep(1)
