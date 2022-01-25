################################################################################
#
# This program is part of the VMwareESXiMonitor Zenpack for Zenoss.
# Copyright (C) 2014 Eric Enns, Matthias Kittl.
# rewritten by Jane Curyy, August 2015 to:
#    1) Use PythonCollector rather than zencommand
#    2) Use pyvmomi Python API to access vSphere rather than the vSphere SDK for Perl
#
# This program can be used under the GNU General Public License version 2
# You can find full information here: http://www.zenoss.com/oss
#
################################################################################


from twisted.internet.defer import inlineCallbacks, returnValue
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.form import schema
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.template import RRDDataSourceInfo
from Products.Zuul.interfaces import IRRDDataSourceInfo
from Products.Zuul.utils import ZuulMessageFactory as _t

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import operator
from datetime import timedelta


# Setup logging
import logging
log = logging.getLogger('zen.VMwareESXiMonitorPython')

# PythonCollector Imports
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSource, PythonDataSourcePlugin

class VMwareDataSource(PythonDataSource):
    """ Description here
    """
    ZENPACKID = 'ZenPacks.community.VMwareESXiMonitorPython'

    # Friendly name for your data source type in the drop-down selection
    #sourcetypes = ('VMwareDataSource',)
    sourcetypes = ('VMware',)
    sourcetype = sourcetypes[0]
    eventClass = '/Status/VMware'
    component = '${here/id}'

    # Custom fields in the datasource - with default values
    # (which can be overriden in template )
    # cycletime defaults to 300
    cycletime = 300

    # Collection plugin for this type. Defined below in this file.
    plugin_classname = ZENPACKID + '.datasources.VMwareDataSource.VMwareDataSourcePlugin'

class IVMwareDataSourceInfo(IRRDDataSourceInfo):
    """Interface that creates the web form for this data source type."""

    cycletime = schema.TextLine(
        title = _t(u'Cycle Time'),
        group = _t('cycletime - think hard before you change this!')
    )

class VMwareDataSourceInfo(RRDDataSourceInfo):
    """ Adapter between IVMwareDataSourceInfo and VMwareDataSource """
    implements(IVMwareDataSourceInfo)
    adapts(VMwareDataSource)

    cycletime = ProxyProperty('cycletime')

    # Doesn't seem to run in the GUI if you activate the test button
    testable = False

class VMwareDataSourcePlugin(PythonDataSourcePlugin):
    """ Data source plugin for VMwareDataSource
    """

    # List of device attributes you might need to do collection.
    proxy_attributes = (
        'zVSphereUsername',
        'zVSpherePassword',
        )

    @classmethod
    def config_key(cls, datasource, context):
        return (
            context.device().id,
            datasource.getCycleTime(context),
            'VMwareDataSource',
        )

    @classmethod
    def params(cls, datasource, context):
        """
        Return params dictionary needed for this plugin.
        This is a classmethod that is executed in zenhub. The datasource and
        context parameters are the full objects.
        You have access to the dmd object database here and any attributes
        and methods for the context (either device or component).
        You can omit this method from your implementation if you don't require
        any additional information on each of the datasources of the config
        parameter to the collect method below. If you only need extra
        information at the device level it is easier to just use
        proxy_attributes as mentioned above.
        """

        # context is the object in question - device or component - component in this case
        params = {}

        params['isMonitored'] = context.monitor
        params['deviceName'] = context.getDeviceName()
        log.debug(' params is %s \n' % (params))
        return params

    @inlineCallbacks
    def collect(self, config):

        def getData(host, user, password, port, log):
        # make a connection
            try:
                conn = SmartConnect(host=host, user=user, pwd=password, port=port)
                if not conn:
                    log.warn('Could not connect to host %s \n' % (host))
                else:
                    content = conn.RetrieveContent()
                    vchtime = conn.CurrentTime()
                    # Get VMs
                    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                                      [vim.VirtualMachine],
                                                                      True)
                    vms = [vm for vm in vm_view.view]
                    log.debug(' in getData - vms is %s \n' % (vms))
                    vm_view.Destroy()

                    # Get datastores
                    datastore_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                                        [vim.Datastore],
                                                                        True)
                    datastores = [datastore for datastore in datastore_view.view]
                    log.debug(' in getData - datastores is %s \n' % (datastores))
                    datastore_view.Destroy()

                    # Get hosts
                    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                                        [vim.HostSystem],
                                                                        True)
                    hosts = [host for host in host_view.view]
                    log.debug(' in getData - hosts is %s \n' % (hosts))
                    host_view.Destroy()

                    perfManager = content.perfManager

                    vpm = vim.PerformanceManager

                    return vchtime, hosts, vms, datastores, perfManager, vpm
            except:
                log.warn('Failed to get data from host %s\n' % (host))

            # Note: from daemons use a shutdown hook to do this, not the atexit
            atexit.register(Disconnect, conn)

        ds0 = config.datasources[0]

        if not ds0.zVSphereUsername:
            log.warn(' No zVSphereUsername set - cannot collect data')
            returnValue(None)
        if not ds0.zVSpherePassword:
            log.warn(' No zVSpherePassword set - cannot collect data')
            returnValue(None)
        port = 443
        try:
            vchtime, hosts, vms, datastores, perfManager, vpm  = yield getData(ds0.manageIp, ds0.zVSphereUsername, ds0.zVSpherePassword, port, log)
        except Exception, e:
            log.error('%s: %s', ds0.device, e)
            returnValue(None)
        returnValue({'vchtime': vchtime, 'hosts':hosts, 'vms':vms, 'datastores':datastores, 'perfManager':perfManager, 'vpm': vpm})

    def onResult(self, result, config):
        """
        Called first for success and error.
        You can omit this method if you want the result of the collect method
        to be used without further processing.
        """

        #log.debug( 'result is %s ' % (result))
        return result

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        You should return a data structure with zero or more events, values
        and maps.
        Note that values is a dictionary and events and maps are lists.

        return {
            'events': [{
                'summary': 'successful collection',
                'eventKey': 'myPlugin_result',
                'severity': 0,
                },{
                'summary': 'first event summary',
                'eventKey': 'myPlugin_result',
                'severity': 2,
                },{
                'summary': 'second event summary',
                'eventKey': 'myPlugin_result',
                'severity': 3,
                }],

            'values': {
                None: { # datapoints for the device (no component)
                'datapoint1': 123.4,
                'datapoint2': 5.678,
                },
                'cpu1': {
                'user': 12.1,
                nsystem': 1.21,
                'io': 23,
                }
                },

            'maps': [
                ObjectMap(...),
                RelationshipMap(..),
                ]
            }
        """

        #log.debug( 'In success - result is %s and config is %s ' % (result, config))
        vchtime = result['vchtime']
        vms = result['vms']
        hosts = result['hosts']
        datastores = result['datastores']
        perfManager = result['perfManager']
        vpm = result['vpm']

        def buildQuery(perfManager, perf_dict, vchtime, counterName, instance, entity, interval):
            # Note that vim.PerformanceManager.QuerySpec returns a list - albeit of 1 sample
            counterId = perf_dict.get(counterName)
            if not counterId:
                log.error('Invalid counter name: %s \n' % (counterName))
                return
            metricId = vpm.MetricId(counterId=counterId, instance=instance)
            startTime = vchtime - timedelta(seconds=60)
            endTime = vchtime - timedelta(seconds=40)
            query = vpm.QuerySpec(intervalId=interval, entity=entity, metricId=[metricId], startTime=startTime, endTime=endTime)
            perfResults = perfManager.QueryPerf(querySpec=[query])
            if perfResults:
                # Note that QueryPerf will return a list so need to use sum function
                return float(sum(perfResults[0].value[0].value))
            else:
                log.error('Performance results empty. TIP: Check time drift on source and vCenter server')
                log.error('Troubleshooting info: Entity is %s and counter name is %s \n' % (entity.name, counterName))
                return

        def calculateValue(perfValue, opType, factor):
            # Operators
            ops = {
                "+": operator.add,
                "-": operator.sub,
                "*": operator.mul,
                "/": operator.div
            }
            if opType and factor:
                opFunction = ops[opType]
                perfValue = opFunction(perfValue, float(factor))
            return perfValue

        def componentPerfData(ds, dataEntities, data):
            if ds.params['isMonitored']:
                for entity, entityData in dataEntities.iteritems():
                    if entity == ds.component:
                        for datapoint_id in (x.id for x in ds.points):
                            if not entityData.has_key(datapoint_id):
                                continue
                            try:
                                value = entityData[datapoint_id]
                            except Exception, e:
                                log.error('Failed to get value datapoint for ESXi component %s, error is %s' % (entity, e))
                                continue
                            dpname = '_'.join((ds.datasource, datapoint_id))
                            data['values'][ds.component][dpname] = (value, 'N')
            return data

        # Get all the performance counters
        perf_dict = {}
        for counter in perfManager.perfCounter:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
            perf_dict[counter_full] = counter.key
        #print('-------perf Dict --------')
        #import pprint
        #pprint.pprint(perf_dict)

        interval = 20    # this is in seconds

        # Get values for required datapoints into a dictionary
        # Hosts
        hostDataPoints = {
            'sysUpTime': {'counterName': 'sys.uptime.latest', 'opType': '', 'factor': ''},
            'memUsage': {'counterName': 'mem.usage.minimum', 'opType': '/', 'factor': '100'},
            'memSwapused': {'counterName': 'mem.swapused.maximum', 'opType': '*', 'factor': '1024'},
            'memGranted': {'counterName': 'mem.granted.maximum', 'opType': '*', 'factor': '1024'},
            'memActive': {'counterName': 'mem.active.maximum', 'opType': '*', 'factor': '1024'},
            'diskUsage': {'counterName': 'disk.usage.average', 'opType': '*', 'factor': '1024'},
            'cpuUsageMin': {'counterName': 'cpu.usage.minimum', 'opType': '/', 'factor': '100'},
            'cpuUsageMax': {'counterName': 'cpu.usage.maximum', 'opType': '/', 'factor': '100'},
            'cpuUsageAvg': {'counterName': 'cpu.usage.average', 'opType': '/', 'factor': '100'},
            'cpuUsage': {'counterName': 'cpu.usagemhz.average', 'opType': '*', 'factor': '1000000'},
            'cpuReservedcapacity': {'counterName': 'cpu.reservedCapacity.average', 'opType': '*', 'factor': '1000000'},
            'netReceived': {'counterName': 'net.received.average', 'opType': '*', 'factor': '8192'},
            'netTransmitted': {'counterName': 'net.transmitted.average', 'opType': '*', 'factor': '8192'},
            'netPacketsRx': {'counterName': 'net.packetsRx.summation', 'opType': '', 'factor': ''},
            'netPacketsTx': {'counterName': 'net.packetsTx.summation', 'opType': '', 'factor': ''},
            'netDroppedRx': {'counterName': 'net.droppedRx.summation', 'opType': '', 'factor': ''},
            'netDroppedTx': {'counterName': 'net.droppedTx.summation', 'opType': '', 'factor': ''}
        }

        dataHosts = {}
        dataInterfaces = {}
        for host in hosts:
            log.debug('Host is %s name is %s \n' % (host, host.name))
            for dataPoint, dataPointData in hostDataPoints.iteritems():
                perfValue = buildQuery(perfManager, perf_dict, vchtime, dataPointData['counterName'], "", host, interval)
                if perfValue:
                    dataHosts[dataPoint] = calculateValue(perfValue, dataPointData['opType'], dataPointData['factor'])

            for interface in host.config.network.pnic:
                dataInterface = {}
                if interface.linkSpeed:
                    dataInterface['operStatus'] = 1
                else:
                    dataInterface['operStatus'] = 2
                dataInterfaces[interface.device] = dataInterface

        # Guest VMs
        guestDataPoints = {
            'memUsage': {'counterName': 'mem.usage.minimum', 'opType': '/', 'factor': '100'},
            'memOverhead': {'counterName': 'mem.overhead.minimum', 'opType': '*', 'factor': '1024'},
            'memConsumed': {'counterName': 'mem.consumed.minimum', 'opType': '*', 'factor': '1024'},
            'diskUsage': {'counterName': 'disk.usage.average', 'opType': '*', 'factor': '1024'},
            'cpuUsageMin': {'counterName': 'cpu.usage.minimum', 'opType': '/', 'factor': '100'},
            'cpuUsageMax': {'counterName': 'cpu.usage.maximum', 'opType': '/', 'factor': '100'},
            'cpuUsageAvg': {'counterName': 'cpu.usage.average', 'opType': '/', 'factor': '100'},
            'cpuUsage': {'counterName': 'cpu.usagemhz.average', 'opType': '*', 'factor': '1000000'}
        }

        dataGuests = {}
        for vm in vms:
            log.debug('vm is %s name is %s \n' % (vm, vm.name))
            dataGuest = {}
            try:
                powerState = vm.runtime.powerState
            except:
                continue    # go to next VM
            if powerState != 'poweredOn':
                adminStatus = 0
                if powerState == 'poweredOff':
                    adminStatus = 2
                elif powerState == 'suspended':
                    adminStatus = 3
                dataGuest['adminStatus'] = adminStatus
                dataGuest['operStatus'] = 0
            else:
                for dataPoint, dataPointData in guestDataPoints.iteritems():
                    perfValue = buildQuery(perfManager, perf_dict, vchtime, dataPointData['counterName'], "", vm, interval)
                    if perfValue:
                        dataGuest[dataPoint] = calculateValue(perfValue, dataPointData['opType'], dataPointData['factor'])

                overallStatus = vm.summary.overallStatus
                operStatus = 0
                if overallStatus == 'green':
                    operStatus = 1
                elif overallStatus == 'red':
                    operStatus = 2
                elif overallStatus == 'yellow':
                    operStatus = 3
                dataGuest['adminStatus'] = 1
                dataGuest['operStatus'] = operStatus
            dataGuests[vm.name] = dataGuest

        # Datastores
        dataDatastores = {}
        for datastore in datastores:
            log.debug('datastore is %s name is %s \n' % (datastore, datastore.summary.name))
            dataDatastore = {}
            if datastore.summary.accessible:
                dataDatastore['diskFreeSpace'] = datastore.summary.freeSpace
                dataDatastore['connectionStatus'] = 1
            else:    
                dataDatastore['diskFreeSpace'] = None
                dataDatastore['connectionStatus'] = 2
            dataDatastores[datastore.summary.name] = dataDatastore

        log.debug(' dataHosts is %s \n' % (dataHosts))
        log.debug(' dataGuests is %s \n' % (dataGuests))
        log.debug(' dataInterfaces is %s \n' % (dataInterfaces))
        log.debug(' dataDatastores is %s \n' % (dataDatastores))

        data = self.new_data()
        for ds in config.datasources:
            #log.debug('ds is %s and hosts is %s and vms is %s and datastores is %s \n' % (ds, hosts, vms, datastores))
            #log.debug(' Datasource is %s and datasource.component is %s and datasource.template is %s and params is %s and plugin is %s \n' % (ds.datasource, ds.component, ds.template, ds.params, ds.plugin_classname))

            if ds.datasource == 'VMwareHost':
                if ds.params['isMonitored']:
                    for datapoint_id in (x.id for x in ds.points):
                        if not dataHosts.has_key(datapoint_id):
                            continue
                        try:
                            value = dataHosts[datapoint_id]
                        except Exception, e:
                            log.error('Failed to get value datapoint for ESXi Host, error is %s' % (e))
                            continue
                        dpname = '_'.join((ds.datasource, datapoint_id))
                        data['values'][ds.component][dpname] = (value, 'N')

            elif ds.datasource == 'VMwareGuest':
                data = componentPerfData(ds, dataGuests, data)

            elif ds.datasource == 'VMwareDatastore':
                data = componentPerfData(ds, dataDatastores, data)

            elif ds.datasource == 'VMwareInterface':
                data = componentPerfData(ds, dataInterfaces, data)

            else:
                log.error('Unknown data source: %s' % (ds.datasource))
        return data


    def onError(self, result, config):
        """
        Called only on error. After onResult, before onComplete.
        You can omit this method if you want the error result of the collect
        method to be used without further processing. It recommended to
        implement this method to capture errors.
        """
        log.debug( 'In OnError - result is %s and config is %s ' % (result, config))
        return {
            'events': [{
                'summary': 'Error getting ESXi with zenpython: %s' % result,
                'eventKey': 'VMware ESXi',
                'severity': 4,
                }],
            }

    def onComplete(self, result, config):
        """
        Called last for success and error.
        You can omit this method if you want the result of either the
        onSuccess or onError method to be used without further processing.
        """
        return result
