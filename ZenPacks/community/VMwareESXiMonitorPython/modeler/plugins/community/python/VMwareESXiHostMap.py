################################################################################
#
# This program is part of the VMwareESXiMonitor Zenpack for Zenoss.
# Copyright (C) 2014 Eric Enns, Matthias Kittl.
# Totally rewritten by Jane Curyy, September 2015 to use the
#     pyvmomi API to gather info directly from the PythonCollectore modeler
#
# This program can be used under the GNU General Public License version 2
# You can find full information here: http://www.zenoss.com/oss
#
################################################################################

__doc__ = """VMwareESXiHostMap

VMwareESXiHostMap gathers ESXi Host information.

"""

from pyVmomi import vim
from twisted.internet.defer import returnValue, inlineCallbacks
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap
from ZenPacks.community.VMwareESXiMonitorPython.VMwareESXigetData import getData

class VMwareESXiHostMap(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zVSphereUsername',
        'zVSpherePassword'
    )

    @inlineCallbacks
    def collect(self, device, log):

        log.info('Getting VMware ESXi Host info for device %s' % device.id)
        username = getattr(device, 'zVSphereUsername', None)
        password = getattr(device, 'zVSpherePassword', None)
        if (not username or not password):
            returnValue(None)
        port = 443
        try:
            s = yield getData(device.id, username, password, port, log, [vim.HostSystem])
        except Exception, e:
            log.error(
                    "In collect exception %s: %s", device.id, e)
            returnValue(None)
        log.info('Response is %s \n' % (s))
        returnValue(s)

    def process(self, device, results, log):
        #log.debug(' Start of process - results is %s \n' % (results))
        maps = []

        for host in results:
            # Don't actually see there being more than one host.....
            hostDict = {}
            hostDict['setOSProductKey'] = host.summary.config.product.fullName
            hostDict['setHWProductKey'] = host.summary.hardware.model
            hostDict['cpuMhz'] = long(host.summary.hardware.cpuMhz)
            hostDict['cpuModel'] = host.summary.hardware.cpuModel
            hostDict['numCpuCores'] = int(host.summary.hardware.numCpuCores)
            hostDict['numCpuPkgs'] = int(host.summary.hardware.numCpuPkgs)
            hostDict['numCpuCoresPerPkgs'] = hostDict['numCpuCores'] / hostDict['numCpuPkgs']
            hostDict['numCpuThreads'] = int(host.summary.hardware.numCpuThreads)
            hostDict['numNics'] = int(host.summary.hardware.numNics)
            vmotionState = host.summary.config.vmotionEnabled
            if vmotionState == 0:
                hostDict['vmotionState'] = True
            else:
                hostDict['vmotionState'] = False

            log.debug(' hostDict is %s \n' % (hostDict))

        maps.append(ObjectMap({'totalMemory': host.summary.hardware.memorySize }, compname='hw'))
        maps.append(ObjectMap({'totalSwap': 0}, compname='os'))

        maps.append(ObjectMap(
            modname = 'ZenPacks.community.VMwareESXiMonitorPython.ESXiHost',
            data = hostDict ))

        return maps

