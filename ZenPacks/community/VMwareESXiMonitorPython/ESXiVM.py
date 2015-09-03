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
LOG = logging.getLogger('zen.ESXiVM')


from math import isnan

# Need to define some methods for the ESXiVM component

class ESXiVM(schema.ESXiVM):

    def adminStatus(self, default = None):
        status = self.cacheRRDValue('adminStatus', default)
        if status is not None and status != 'Unknown' and not isnan(status):
            return int(status)
        return None

    def operStatus(self, default = None):
        status = self.cacheRRDValue('operStatus', default)
        if status is not None and status != 'Unknown' and not isnan(status):
            return int(status)
        return None

