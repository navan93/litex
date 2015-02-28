import sys, subprocess

from mibuild.generic_programmer import GenericProgrammer
from mibuild.xilinx import common

def _run_urjtag(cmds):
	with subprocess.Popen("jtag", stdin=subprocess.PIPE) as process:
		process.stdin.write(cmds.encode("ASCII"))
		process.communicate()

class UrJTAG(GenericProgrammer):
	needs_bitreverse = True

	def load_bitstream(self, bitstream_file):
		cmds = """cable milkymist
detect
pld load {bitstream}
quit
""".format(bitstream=bitstream_file)
		_run_urjtag(cmds)

	def flash(self, address, data_file):
		flash_proxy = self.find_flash_proxy()
		cmds = """cable milkymist
detect
pld load "{flash_proxy}"
initbus fjmem opcode=000010
frequency 6000000
detectflash 0
endian big
flashmem "{address}" "{data_file}" noverify
""".format(flash_proxy=flash_proxy, address=address, data_file=data_file)
		_run_urjtag(cmds)

class XC3SProg(GenericProgrammer):
	needs_bitreverse = False

	def __init__(self, cable, flash_proxy_basename=None):
		GenericProgrammer.__init__(self, flash_proxy_basename)
		self.cable = cable

	def load_bitstream(self, bitstream_file):
		subprocess.call(["xc3sprog", "-v", "-c", self.cable, bitstream_file])

	def flash(self, address, data_file):
		flash_proxy = self.find_flash_proxy()
		subprocess.call(["xc3sprog", "-v", "-c", self.cable, "-I"+flash_proxy, "{}:w:0x{:x}:BIN".format(data_file, address)])


class FpgaProg(GenericProgrammer):
	needs_bitreverse = False

	def __init__(self, flash_proxy_basename=None):
		GenericProgrammer.__init__(self, flash_proxy_basename)

	def load_bitstream(self, bitstream_file):
		subprocess.call(["fpgaprog", "-v", "-f", bitstream_file])

	def flash(self, address, data_file):
		if address != 0:
			raise ValueError("fpga prog needs a main bitstream at address 0")
		flash_proxy = self.find_flash_proxy()
		subprocess.call(["fpgaprog", "-v", "-sa", "-r", "-b", flash_proxy,
				   "-f", data_file])

def _source_vivado(vivado_path, ver=None):
	if sys.platform == "win32" or sys.platform == "cygwin":
		pass
	else:
		settings = common.settings(vivado_path, ver)
		subprocess.call(["source", settings])

def _run_vivado(cmds):
	with subprocess.Popen("vivado -mode tcl", stdin=subprocess.PIPE, shell=True) as process:
		process.stdin.write(cmds.encode("ASCII"))
		process.communicate()

class VivadoProgrammer(GenericProgrammer):
	needs_bitreverse = False
	def __init__(self, vivado_path="/opt/Xilinx/Vivado"):
		GenericProgrammer.__init__(self)
		_source_vivado(vivado_path)

	def load_bitstream(self, bitstream_file):
		cmds = """open_hw
connect_hw_server
open_hw_target [lindex [get_hw_targets -of_objects [get_hw_servers localhost]] 0]

set_property PROBES.FILE {{}} [lindex [get_hw_devices] 0]
set_property PROGRAM.FILE {{{bitstream}}} [lindex [get_hw_devices] 0]

program_hw_devices [lindex [get_hw_devices] 0]
refresh_hw_device [lindex [get_hw_devices] 0]

quit
""".format(bitstream=bitstream_file)
		_run_vivado(cmds)

	# XXX works to flash bitstream, adapt it to flash bios
	def flash(self, address, data_file):
		cmds = """open_hw
connect_hw_server
open_hw_target [lindex [get_hw_targets -of_objects [get_hw_servers localhost]] 0]
create_hw_cfgmem -hw_device [lindex [get_hw_devices] 0] -mem_dev  [lindex [get_cfgmem_parts {{n25q256-3.3v-spi-x1_x2_x4}}] 0]

set_property PROGRAM.BLANK_CHECK  0 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.ERASE  1 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.CFG_PROGRAM  1 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.VERIFY  1 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
refresh_hw_device [lindex [get_hw_devices] 0]

set_property PROGRAM.ADDRESS_RANGE  {{use_file}} [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.FILES [list "{data}" ] [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0]]
set_property PROGRAM.UNUSED_PIN_TERMINATION {{pull-none}} [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.BLANK_CHECK  0 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.ERASE  1 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.CFG_PROGRAM  1 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
set_property PROGRAM.VERIFY  1 [ get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]

startgroup
if {{![string equal [get_property PROGRAM.HW_CFGMEM_TYPE  [lindex [get_hw_devices] 0]] [get_property MEM_TYPE [get_property CFGMEM_PART [get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]]]] }}  {{ create_hw_bitstream -hw_device [lindex [get_hw_devices] 0] [get_property PROGRAM.HW_CFGMEM_BITFILE [ lindex [get_hw_devices] 0]]; program_hw_devices [lindex [get_hw_devices] 0]; }};
program_hw_cfgmem -hw_cfgmem [get_property PROGRAM.HW_CFGMEM [lindex [get_hw_devices] 0 ]]
endgroup

quit
""".format(data=data_file)
		_run_vivado(cmds)