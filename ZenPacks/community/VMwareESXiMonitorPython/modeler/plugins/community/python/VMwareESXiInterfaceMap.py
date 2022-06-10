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

__doc__ = """VMwareESXiInterfaceMap

VMwareESXiInterfaceMap gathers ESXi Interface information.

"""

from pyVmomi import vim
from twisted.internet.defer import returnValue, inlineCallbacks
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from ZenPacks.community.VMwareESXiMonitorPython.VMwareESXigetData import getData

class VMwareESXiInterfaceMap(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zVSphereUsername',
        'zVSpherePassword'
    )

    @inlineCallbacks
    def collect(self, device, log):

        log.info('Getting VMware ESXi Interface info for device %s' % device.id)
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
        log.debug(' Start of process - results is %s \n' % (results))
        #rm = self.relMap()
        maps = []
        interfaces = []

        interfaceDict = {}
        for host in results:
            # Get physical interfaces
            for interface in host.config.network.pnic:
                #om = self.objectMap()
                name = interface.device
                interfaceDict['id'] = self.prepId(name)
                interfaceDict['interfaceName'] = name
                interfaceDict['ifindex'] = name
                interfaceDict['macaddress'] = interface.mac
                interfaceDict['type'] = "Physical Adapter"
                interfaceDict['description'] = ""
                interfaceDict['mtu'] = 0
                if interface.spec.ip:
                    if interface.spec.ip.ipAddress:
                        interfaceDict['setIpAddresses'] = interface.spec.ip.ipAddress
                    else:
                        interfaceDict['setIpAddresses'] = []
                if interface.linkSpeed:
                    interfaceDict['speed'] = long(interface.linkSpeed.speedMb)
                    interfaceDict['duplex'] = int(interface.linkSpeed.duplex)
                    interfaceDict['adminStatus'] = 1
                    interfaceDict['operStatus'] = 1
                else:
                    interfaceDict['speed'] = 0
                    interfaceDict['duplex'] = 0
                    interfaceDict['adminStatus'] = 2
                    interfaceDict['operStatus'] = 2
                interfaces.append(ObjectMap(data=interfaceDict))
                log.debug(' interfaceDict is %s \n' % (interfaceDict))
            # Get virtual interfaces
            for interface in host.config.network.vnic:
                name = interface.device
                interfaceDict['id'] = self.prepId(name)
                interfaceDict['interfaceName'] = name
                interfaceDict['ifindex'] = name
                interfaceDict['macaddress'] = interface.spec.mac
                interfaceDict['type'] = "Virtual Adapter"
                interfaceDict['description'] = interface.portgroup
                interfaceDict['mtu'] = int(interface.spec.mtu)
                if interface.spec.ip:
                    if interface.spec.ip.ipAddress:
                        interfaceDict['setIpAddresses'] = interface.spec.ip.ipAddress
                    else:
                        interfaceDict['setIpAddresses'] = []
                interfaceDict['speed'] = 0
                interfaceDict['duplex'] = 0
                interfaceDict['operStatus'] = 1
                interfaceDict['adminStatus'] = 1
                interfaces.append(ObjectMap(data=interfaceDict))
                log.debug(' interfaceDict is %s \n' % (interfaceDict))

        maps.append(RelationshipMap(
            relname = 'interfaces',
            modname = 'Products.ZenModel.IpInterface',
            compname = 'os',
            objmaps = interfaces ))

        return maps

