#!/usr/bin/python
# coding=utf-8

"""
RawReader

by Martin Matysiak
  mail@martin-matysiak.de
  www.martin-matysiak.de
"""

__version__ = "2.0"

import sys
import os
from optparse import OptionParser

# some pseudoconstant values
# the header which identifies a nofs
NOFS_HEAD = "k621.de"

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
        
        May throw exceptions in the following cases:
        *tbd*
        
        """
        pass
    
    def get_contents():
        """Returns the contents of the device or file until either
        
        * 0x03 is read on valid NoFS device
        * 0x00 or 0xFF is read on a non-NoFS device
        * EOF is reached
        
        Simultaneously, stores the number of read sectors in the
        public attribute 'sectors_read'.
        
        """
        pass
        
    def erase(complete = False):
        """Erases the device or file.
        
        Parameters:
        complete - If set, the whole file will be overwritten with 0xFF,
        otherwise only until the first occurence of NOFS_TERMINAL

        Returns True if erase procedure succeeded, otherwise False (e.g. if 
        no valid NoFS was detected and force set to False). No writing 
        writing operations have been performed if this method returns False!
        
        """
        pass
        
    def initialize_nofs():
        """Initializes a NoFS on the given device or file.
        
        Will only work if the device object has been initialized with force
        set to True.
        
        Returns true if initialization succeeded, otherwise False.
        
        """
        pass

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

def initialize_nofs(device_handle):
    # open the device with writing permissions, write the header and erase
    # the rest of the first sector
    try:
        erase_sectors(device_handle, 2)
        device_handle.seek(0)
        first_sector = NOFS_HEAD
        first_sector += NOFS_TERMINAL
        first_sector += (NOFS_SECTOR_SIZE - len(NOFS_HEAD) - len(NOFS_TERMINAL)) * chr(0xFF)
        device_handle.write(first_sector)
        device_handle.flush()
    except IOError as ex:
        print "\nERROR: Device could not be initialized. Details: %s\n" % str(ex)

def erase_sectors(device_handle, sector_count = None):
    device_handle.seek(0)
    eof = False
    while not eof:
        try:
            device_handle.write(NOFS_SECTOR_SIZE * chr(0xFF))
            if sector_count != None:
                sector_count -= 1
                eof = sector_count == 0
        except IOError:
            eof = True

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
            handle = open(device, "r")
            if (handle.read(len(NOFS_HEAD)) == NOFS_HEAD):
                handle.close()
                return device
            handle.close()
        except IOError:
            pass
    
    # if the program reaches this point, no device could be found
    print "ERROR: No NoFS device could be found"
    sys.exit(3)

# main program
def main():
    # check arguments
    parser = OptionParser(version="\nRawRead %s\n  by Martin Matysiak\
                          \n  www.martin-matysiak.de\n" % VERSION)
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
            handle = open(devices[0], "rb+")
            initialize_nofs(handle)
            handle.close()
            print "> Device initialized successfully!"
        
        sys.exit(0)

    # otherwise proceed as following:

    # select input device
    input_handle = None
    device = None
    valid_nofs = False

    if options.input_device:
        device = options.input_device
    else:
        device = get_nofs_device()
        valid_nofs = True

    try:
        input_handle = open(device, "rb+")
        if not valid_nofs:
            # quick check if valid nofs is given
            valid_nofs = input_handle.read(len(NOFS_HEAD)) == NOFS_HEAD
            input_handle.seek(0)
    except IOError:
        parser.error("INPUT could not be read (root permissions may be necessary)")
        sys.exit(3)

    # read input device and write to output
    output_handle = None

    if options.output_file:
        output_handle = open(options.output_file, "wb")
    else:
        output_handle = sys.stdout
        
    # -> read sector after sector and check for NOFS_TERMINAL
    eof = False
    sectors_read = 0
    
    # read the first few bytes so that the nofs header won't get
    # into the output file. seek() won't work on windows, that's
    # why I use read()
    if valid_nofs:
        input_handle.read(len(NOFS_HEAD))
    
    while not eof:
        sector = input_handle.read(NOFS_SECTOR_SIZE)        
        eof = (len(sector) != NOFS_SECTOR_SIZE) or (NOFS_TERMINAL in sector)
        # ignore everything after and including NOFS_TERMINAL
        if NOFS_TERMINAL in sector:
            sector = sector[:sector.find(NOFS_TERMINAL)]
        output_handle.write(sector)
        sectors_read += 1
    
    # check if output file was given, otherwise stdout would be closed
    if options.output_file:
        output_handle.close()

    # erase input device (if set)
    if options.erase_disk or options.full_erase:
        if (valid_nofs or options.force):    
            erase_sectors(input_handle, sectors_read if options.erase_disk else None)
            initialize_nofs(input_handle)
        else:
            print "\nERROR: Can't erase device. Override with -f (careful!)\n"
    
    input_handle.close()

main()
