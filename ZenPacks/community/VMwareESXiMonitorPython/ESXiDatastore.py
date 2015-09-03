################################################################################
#
# This program is part of the VMwareESXiMonitor Zenpack for Zenoss.
# Copyright (C) 2014 Eric Enns, Matthias Kittl.
# Updated and modified by Jane Curry August 2015
#	To work with zenpacklib
#
# This program can be used under the GNU General Public License version 2
# You can find full information here: http://www.zenoss.com/oss
#
################################################################################

from . import schema
import logging
LOG = logging.getLogger('zen.ESXiDatastore')


from math import isnan

# Need to define some methods for the ESXiDatastore component

class ESXiDatastore(schema.ESXiDatastore):

    def usedSpace(self):
        capacity = self.capacity
        free = self.freeSpace()
        if capacity is not None and free is not None:
            return capacity - free
        return None

    def freeSpace(self, default = None):
        free = self.cacheRRDValue('diskFreeSpace', default)
        if free is not None and free != 'Unknown' and not isnan(free):
            return long(free)
        return None

    def usedPercent(self):
        capacity = self.capacity
        used = self.usedSpace()
        if capacity is not None and used is not None:
            return round(100.0 * used / capacity)
        return 'Unknown'

