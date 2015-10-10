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

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
from twisted.internet.defer import returnValue, inlineCallbacks
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap

def getData(host, username, password, port, log):

    log.debug('In getData. host is %s, username is %s, password is %s, port is %s \n' % (host, username, password, port))
    serviceInstance = SmartConnect(host=host,
                                   user=username,
                                   pwd=password,
                                   port=port)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    hosts = [host for host in host_view.view]
    log.debug(' in getData - hosts is %s \n' % (hosts))
    host_view.Destroy()

    return hosts


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
            s = yield getData(device.manageIp, username, password, port, log)
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

