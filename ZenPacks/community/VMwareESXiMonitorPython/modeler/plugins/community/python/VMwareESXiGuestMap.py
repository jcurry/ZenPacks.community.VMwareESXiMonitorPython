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

__doc__ = """VMwareESXiGuestMap

VMwareESXiGuestMap gathers ESXi Guest VM information.

"""

from pyVmomi import vim
from twisted.internet.defer import returnValue, inlineCallbacks
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from ZenPacks.community.VMwareESXiMonitorPython.VMwareESXigetData import getData


class VMwareESXiGuestMap(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zVSphereUsername',
        'zVSpherePassword'
    )

    @inlineCallbacks
    def collect(self, device, log):

        log.info('Getting VMware ESXi Guest info for device %s' % device.id)
        username = getattr(device, 'zVSphereUsername', None)
        password = getattr(device, 'zVSpherePassword', None)
        if (not username or not password):
            returnValue(None)
        port = 443
        try:
            s = yield getData(device.id, username, password, port, log, [vim.VirtualMachine])
        except Exception, e:
            log.error(
                    "In collect exception %s: %s", device.id, e)
            returnValue(None)
        log.info('Response is %s \n' % (s))
        returnValue(s)

    def process(self, device, results, log):
        log.debug(' Start of process - results is %s \n' % (results))
        maps = []
        vms = []

        for vm in results:
            vmDict = {}
            vmDict['id'] = self.prepId(vm.name)
            vmDict['title'] = vm.name
            vmDict['memory'] = int(vm.config.hardware.memoryMB) * 1024 * 1024
            vmDict['osType'] = vm.config.guestFullName
            vms.append(ObjectMap(data=vmDict))

            log.debug(' vmDict is %s \n' % (vmDict))

            log.debug('VM Guest is %s \n' % ( vmDict['id']))

        maps.append(RelationshipMap(
            relname = 'esxiVm',
            modname = 'ZenPacks.community.VMwareESXiMonitorPython.ESXiVM',
            objmaps = vms ))

        return maps

