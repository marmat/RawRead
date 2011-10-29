#!/usr/bin/python
# coding=utf-8

"""
RawReader

by Martin Matysiak
  mail@martin-matysiak.de
  www.martin-matysiak.de
"""

__version__ = "2.2a1"

import sys
import os
from optparse import OptionParser

# some pseudoconstant values
# the part of the header which identifies a nofs
NOFS_SIGNATURE = "k621.de"

# the full filesystem header
NOFS_HEADER = NOFS_SIGNATURE + "\0\0\0\0"

# the terminal symbol which identifies the end of a nofs
NOFS_TERMINAL = chr(0x03)

# the sector size which is used for the nofs
NOFS_SECTOR_SIZE = 512

# the maximum amount of devices that should be scanned (starting from ..0/..a)
MAX_DEVICES = 16

# a more object-oriented approach to the problem
class Device:
    """A class representing an input device"""
    
    valid_nofs = False
    sectors_read = None
    
    _force_operations = False
    _device_handle = None
    
    def __init__(self, path, force = False, permissions = "r"):
        """Class constructor. 
        
        Parameters:
        path - the path at which the device or input file is located
        permissions - the permissions which shall be used when accessing 
        the device. See the python file-object for possible options.
        force - If specified, erase operations _will_ perform writing
        operations, even if no valid NoFS is detected.
        
        May throw IOError if the device doesn't exist or can't be accessed
        """
        # check if the device exists at all
        if not os.path.exists(path):
            raise IOError("Given device doesn't exist")
        
        # try to access the device with the given permissions
        self._device_handle = file(path, permissions)
        
        # read the first few bytes to assure there is a nofs on it
        self.valid_nofs = self._device_handle.read(len(NOFS_SIGNATURE)) == NOFS_SIGNATURE
        self._device_handle.seek(0)
        
        # remember parameters
        self._force_operations = force   
    
    def __del__(self):
        """Class destructor. Closes the file handle on the device if it
        was opened"""
        if self._device_handle != None:
            self._device_handle.close()   
    
    def get_contents(self):
        """Returns the contents of the device or file until either
        
        * 0x03 is read on valid NoFS device
        * 0x00 or 0xFF is read on a non-NoFS device
        * EOF is reached
        
        Simultaneously, stores the number of read sectors in the
        public attribute 'sectors_read'.
        
        """
        self._device_handle.seek(0)
        self.sectors_read = 0

        # If we have a valid NoFS, ignore the first few bytes so that
        # they don't show up in the returned content
        # Furthermore, set up which symbols will end the content getting
        terminal = chr(0x00)
        if self.valid_nofs:
            self._device_handle.read(len(NOFS_HEADER))
            terminal = NOFS_TERMINAL
        
        # Start reading
        eof = False
        result = ""
        while not eof:
            try:
                sector = self._device_handle.read(NOFS_SECTOR_SIZE)
            except IOError:
                eof = True
                break

            eof = (len(sector) != NOFS_SECTOR_SIZE) or (terminal in sector)
            # Ignore everything after and including terminal
            if terminal in sector:
                sector = sector[:sector.find(terminal)]
            
            result += sector
            self.sectors_read += 1
        
        return result

        
    def erase(self, complete = False):
        """Erases the device or file.
        
        Parameters:
        complete - If set, the whole file will be overwritten with empty
        sectors, otherwise only until the first occurence of NOFS_TERMINAL

        Returns True if erase procedure succeeded, otherwise False (e.g. if 
        no valid NoFS was detected and force set to False). No writing 
        writing operations have been performed if this method returns False!
        
        """
        if not (self.valid_nofs or self._force_operations):
            return False

        # If only a partial erase is wished and the count of sectors
        # hasn't been determined, sweep through the contents
        if self.sectors_read == None and not complete:
            self.get_contents()
            
        result = self._erase_sectors(self.sectors_read if not complete else -1)

        if result and self.valid_nofs:
            self._write_header()
        
        return result
        
    def initialize_nofs(self):
        """Initializes a NoFS on the given device or file.
        
        Will only work if the device object has been initialized with force
        set to True and the device hasn't been initialized already.
        
        Returns true if initialization succeeded, otherwise False.
        
        """
        if self.valid_nofs:
            print "ERROR: the device already contains a valid NoFS. Initialization aborted"
            return False

        if not self._force_operations:
            return False
        
        # erase the first few sectors and write header
        self._erase_sectors(4,1)
        self._write_header()
        return True
    
    def _write_header(self):
        """Internal method which writes the NOFS_HEADER into the very
        first sector"""
        self._device_handle.seek(0)

        # remember: we can only write a whole sector at a time
        first_sector = NOFS_HEADER
        first_sector += NOFS_TERMINAL
        first_sector += (NOFS_SECTOR_SIZE - len(NOFS_HEADER) - len(NOFS_TERMINAL)) * chr(0xFF)
        
        # write it onto the device
        self._device_handle.write(first_sector)
        self._device_handle.flush()

    
    def _erase_sectors(self, count = 0, start = 0):
        """Internal method for erasing a specific count of sectors on
        the device. A sector is called erased when the very first byte
        is a NOFS_TERMINAL and the rest 0xFF. The NOFS_TERMINAL serves
        the purpose that, if the device should somehow not be able to
        write a terminal, it'll still find another one.
        
        Paramters:
        count - The number of sectors to be removed. When set to -1, all
        sectors until EOF will be removed
        start - The sector from which erasing should be started
        
        returns True if everything went fine, False otherwise
        """
        self._device_handle.seek(start * NOFS_SECTOR_SIZE)
        eof = False
        
        while not eof:
            try:    
                self._device_handle.write(NOFS_TERMINAL)
                self._device_handle.write(chr(0xFF) * (NOFS_SECTOR_SIZE - 1))
                if count >= 0:
                    count -= 1
                    eof = count == 0
            except IOError:
                eof = True
        
        # If we got an exception before count was less than or equal zero,
        # something went wrong
        return count <= 0

# returns a list of possible device names, depending on the running os
def get_possible_devices():
    possible_devices = []
    if sys.platform.startswith("win32"):
        for i in range(MAX_DEVICES):
            possible_devices.append("\\\\.\\PhysicalDrive%d" % (i+1))
    elif sys.platform.startswith("linux"):
        for i in range(MAX_DEVICES):
            possible_devices.append("/dev/sd%c" % chr(97 + i))
    elif sys.platform.startswith("darwin"):
        for i in range(MAX_DEVICES):
            possible_devices.append("/dev/disk%d" % (i+1))

    return possible_devices

def get_removable_devices(opts):
    # detect the correct device by letting the user eject and insert the device
    raw_input("> Please eject the device if inserted and press enter...")
    
    # scan through a list of possible devices and remember the available ones
    available_devices = []
    
    for device in get_possible_devices():
        try:
            handle = open(device, "rb")
            handle.read(1)
            available_devices.append(device)
            handle.close()
        except IOError:
            pass
    
    if len(available_devices) == 0:
        print "\nERROR: Available devices could not be determined. Root\
              \npermissions may be necessary to perform this task. No action\
              \nwill be performed.\n"
        sys.exit(1)
    
    
    raw_input("> Please insert the device now and press enter...")
    
    # scan again, remeber the differences
    additional_devices = []
    
    # create a list of devices with possible candidates
    left_devices = get_possible_devices()
    for device in available_devices:
        left_devices.remove(device)
    
    # scan those devices again and check if something has changed    
    for device in left_devices:
        try:
            handle = open(device, "rb")
            handle.read(1)
            additional_devices.append(device)
            handle.close()
        except IOError:
            pass
    
    return additional_devices
    
def get_nofs_device():
    # scan through possible devices and check for nofs header
    for device in get_possible_devices():
        try:
            dev = Device(device)
        except IOError:
            pass
    
    # if the program reaches this point, no device could be found
    print "ERROR: No NoFS device could be found"
    sys.exit(3)

# main program
def main():
    # check arguments
    parser = OptionParser(version="\nRawRead %s\n  by Martin Matysiak\
                          \n  www.martin-matysiak.de\n" % __version__)
    parser.add_option("-i", "--input", dest="input_device", help="read data "
                      "from the device located at INPUT. if not set, rawread "
                      "will try to determine the device automatically", 
                      metavar="INPUT")
    parser.add_option("-c", "--create", action="store_true", dest="create_disk",
                      default=False, help="initialize a device by creating a "
                      "NoFS on it")
    parser.add_option("-e", "--erase", action="store_true", dest="erase_disk",
                      default=False, help="erase disk. will only be performed "
                      "if device contains valid NoFS or -f is set. If used in "
                      "combination with -o, the device will be read out first "
                      "and erased afterwards")
    parser.add_option("-E", "--full-erase", action="store_true", dest="full_erase",
                      default=False, help="disk will be completely overwritten. "
                      "May take a long time depending on the size of the device "
                      "specified by INPUT. will only be performed if device "
                      "contains valid NoFS or -f is set. If used in combination "
                      "with -o, the device will be read out first and erased "
                      "afterwards.")
    parser.add_option("-f", "--force", action="store_true", dest="force",
                      default=False, help="force actions, no matter if the "
                      "input device contains a NoFS or not. DANGEROUS!")
    parser.add_option("-o", "--output", dest="output_file",
                      help="write data to OUTPUT. defaults to stdout or none "
                      "if -c, -e or -E is set.", 
                      metavar="OUTPUT")

    (options, args) = parser.parse_args()
    
    # handle trivial parameter errors
    if options.erase_disk and options.full_erase:
        parser.error("can't use -e and -E at the same time!")
        
    if options.create_disk and options.output_file:
        parser.error("can't use -c and specify an output file at the same time!")
        
    if options.create_disk and (options.erase_disk or options.full_erase):
        parser.error("can't use -c and -e or -E at the same time!")
        
    if options.create_disk and options.input_device and not options.force:
        parser.error("can't use -c and -i unless -f is set (are you SURE you want to do this?)")

    # if -c is set, perform a special creation routine:
    if options.create_disk:
        # check if device is given or if it shall be determined automatically
        devices = []
        if options.input_device:
            if options.force:
                devices = [options.input_device]
            else:
                parser.error("Can't create NoFS on INPUT unless -f is set")
        else:
            devices = get_removable_devices(options)
        
        if len(devices) == 0:
            print "\nERROR: No suitable device could be found.\n"
        elif len(devices) >= 2:
            print "\nWARNING: More than one suitable device has been detected. No\
                  \naction will be performed. Please run the program again, using\
                  \nthe -i parameter to select one of the following devices and -f\
                  \nto enforce your selection (dangerous!):\n"
            print devices
        else:
            # create a nofs on the device
            print "> Initializing NoFS on %s..." % devices[0]
            if (Device(devices[0], True, "rb+").initialize_nofs()):
                print "> Device initialized successfully!"    
            else:
                print "> Device initialization failed!"            
        
        sys.exit(0)

    # otherwise proceed as following:

    # select input device
    input_handle = None
    device = None
    permissions = "rb+" if options.erase_disk or options.full_erase else "rb"
    valid_nofs = False

    if options.input_device:
        device = Device(options.input_device, options.force, permissions)
    else:
        # search for a nofs device
        for device_path in get_possible_devices():
            try:
                device = Device(device_path, options.force, permissions)
            except IOError as ex:
                # ignore this device and turn to the next one
                print "WARNING (%s): %s" % (device_path, str(ex))
                continue

            if device.valid_nofs:
                break
        
        if device == None or not device.valid_nofs:        
            print "ERROR: No valid NoFS device found"
            sys.exit(0)

    # read input device
    device_contents = device.get_contents()

    # open output stream
    output_handle = None

    if options.output_file:
        output_handle = open(options.output_file, "wb")
    else:
        output_handle = sys.stdout

    # check if it should be erased
    if options.erase_disk or options.full_erase:
        if not device.erase(options.full_erase):
            print "ERROR: Couldn't erase device"
        # if device-erase has been set, write only if output is not stdout
        if options.output_file:
            output_handle.write(device_contents)
    else:
        output_handle.write(device_contents)

    # check if output file was given, otherwise stdout would be closed
    if options.output_file:
        output_handle.close()

    del device

if __name__=='__main__':
  main()