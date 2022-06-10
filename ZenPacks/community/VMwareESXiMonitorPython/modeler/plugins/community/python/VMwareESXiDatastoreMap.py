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

__doc__ = """VMwareESXiDatastoreMap

VMwareESXiDatastoreMap gathers ESXi Datastore information.

"""

from pyVmomi import vim
from twisted.internet.defer import returnValue, inlineCallbacks
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from ZenPacks.community.VMwareESXiMonitorPython.VMwareESXigetData import getData


class VMwareESXiDatastoreMap(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zVSphereUsername',
        'zVSpherePassword'
    )

    @inlineCallbacks
    def collect(self, device, log):

        log.info('Getting VMware ESXi Datastore info for device %s' % device.id)
        username = getattr(device, 'zVSphereUsername', None)
        password = getattr(device, 'zVSpherePassword', None)
        if (not username or not password):
            returnValue(None)
        port = 443
        try:
            s = yield getData(device.id, username, password, port, log, [vim.Datastore])
        except Exception, e:
            log.error(
                    "In collect exception %s: %s", device.id, e)
            returnValue(None)
        log.info('Response is %s \n' % (s))
        returnValue(s)

    def process(self, device, results, log):
        log.debug(' Start of process - results is %s \n' % (results))
        maps = []
        datastores = []

        for datastore in results:
            datastoreDict = {}
            datastoreDict['id'] = self.prepId(datastore.summary.name)
            datastoreDict['title'] = datastore.summary.name
            datastoreDict['type'] = datastore.summary.type
            datastoreDict['capacity'] = long(datastore.summary.capacity)
            #datastoreDict['accessible'] = datastore.summary.accessible
            if not int(datastore.summary.accessible) == 1:
                log.warning('Datastore %s of device %s is not accessible' % (datastoreDict['id'], device.id))
                continue

            datastores.append(ObjectMap(data=datastoreDict))
            log.debug(' datastoreDict is %s \n' % (datastoreDict))
            log.debug('VM Datastore is %s \n' % (datastoreDict['id']))

            maps.append(RelationshipMap(
                relname = 'esxiDatastore',
                modname = 'ZenPacks.community.VMwareESXiMonitorPython.ESXiDatastore',
                objmaps = datastores ))

        return maps

