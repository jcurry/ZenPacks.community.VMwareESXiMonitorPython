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

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
import atexit

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
    sourcetypes = ('VMware',)
    sourcetype = sourcetypes[0]
    eventClass = '/Status/VMware'
    component = '${here/id}'

    # Custom fields in the datasource - with default values
    # (which can be overriden in template )

    performanceSource = 'VMwareHost'
    instance = ''
    # cycletime defaults to 300
    cycletime = 300

    properties = PythonDataSource._properties + (
    {'id': 'performanceSource', 'type': 'string', 'mode': 'w'},
    {'id': 'instance', 'type': 'string', 'mode': 'w'},
    )

    # Collection plugin for this type. Defined below in this file.
    plugin_classname = ZENPACKID + '.datasources.VMwareDataSource.VMwareDataSourcePlugin'

class IVMwareDataSourceInfo(IRRDDataSourceInfo):
    """Interface that creates the web form for this data source type."""

    performanceSource = schema.TextLine(
        title = _t(u'Performance Source'),
        group = _t('VMware parameters'))

    instance = schema.TextLine(
        title = _t(u'Instance'),
        group = _t('VMware parameters'))

    cycletime = schema.TextLine(
        title = _t(u'Cycle Time'),
        group = _t('cycletime - think hard before you change this!'))

class VMwareDataSourceInfo(RRDDataSourceInfo):
    """ Adapter between IVMwareDataSourceInfo and VMwareDataSource """
    implements(IVMwareDataSourceInfo)
    adapts(VMwareDataSource)

    performanceSource = ProxyProperty('performanceSource')
    instance = ProxyProperty('instance')
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

        #return (
        #context.device().id,
        #datasource.getCycleTime(context),
        #datasource.rrdTemplate().id,
        #datasource.id,
        #context.id,
        #'VMwareDataSource',
        #)
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
       
        ps = datasource.talesEval(datasource.performanceSource, context)
        #Original ZP has ONE datasource for both device (ESXiHost) and components (ESXiDatasource & ESXiVM)
        # performanceSource designates device/component type - VMwareHost, VMwareDatasource, VMwareGuest
        if ps != 'VMwareHost':
            deviceName = context.device().titleOrId()
        else:
            deviceName = context.titleOrId()

        params['performanceSource'] = ps
        params['instance'] = datasource.talesEval(datasource.instance, context)
        params['isMonitored'] = context.monitor
        params['deviceName'] = deviceName
        log.debug(' params is %s \n' % (params))
        return params

    @inlineCallbacks
    def collect(self, config):

        def getData(host, user, password, port, log):
        # make a connection
            try:
                conn = connect.SmartConnect(host=host, user=user, pwd=password, port=port)
                if not conn:
                    log.warn('Could not connect to host %s \n' % (host))
                else:
                    content = conn.RetrieveContent()
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

                    return hosts, vms, datastores, perfManager, vpm
            except:
                log.warn('Failed to get data from host %s\n' % (host))
                
            # Note: from daemons use a shutdown hook to do this, not the atexit
            atexit.register(connect.Disconnect, conn)

        ds0 = config.datasources[0]

        if not ds0.zVSphereUsername:
            log.warn(' No zVSphereUsername set - cannot collect data')
            returnValue(None)
        if not ds0.zVSpherePassword:
            log.warn(' No zVSpherePassword set - cannot collect data')
            returnValue(None)
        port = 443
        try:
            hosts, vms, datastores, perfManager, vpm  = yield getData(ds0.manageIp, ds0.zVSphereUsername, ds0.zVSpherePassword, port, log)
        except Exception, e:
            log.error( "%s: %s", ds0.device, e)
            returnValue(None)
        returnValue({'hosts':hosts, 'vms':vms, 'datastores':datastores, 'perfManager':perfManager, 'vpm': vpm})

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
        vms = result['vms']
        hosts = result['hosts']
        datastores = result['datastores']
        perfManager = result['perfManager']
        vpm = result['vpm']

        def StatCheck(perf_dict, counter_name):
            counter_key = perf_dict[counter_name]
            return counter_key

        def lookupCounterName(perf_dict, counter_key):
            for k, v in perf_dict.items():
                if v == counter_key:
                    return k
            return 

        def BuildQuery(perfManager, counterId, instance, host, interval):
            # Note that vim.PerformanceManager.QuerySpec returns a list - albeit of 1 sample with maxSample=1
            metricId = vpm.MetricId(counterId=counterId, instance=instance)
            #log.debug(' counterId is %s and host is %s  and metricId is %s \n' % (counterId, host, metricId))
            query = vpm.QuerySpec(intervalId=interval, entity=host, metricId=[metricId], maxSample=1)
            perfResults = perfManager.QueryPerf(querySpec=[query])
            if perfResults:
                return perfResults
            else:
                log.info('ERROR: Performance results empty.  TIP: Check time drift on source and vCenter server')
                counter_name = lookupCounterName(perf_dict, counterId)
                log.info('Troubleshooting info: host is %s and counter name is %s \n' % (host.name, counter_name))
                return

        # Get all the performance counters
        perf_dict = {}
        perfList = perfManager.perfCounter
        for counter in perfList:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
            perf_dict[counter_full] = counter.key
        #print('-------perf Dict --------')
        #import pprint
        #pprint.pprint(perf_dict)

        interval = 20

        # Get values for required datapoints into a dictionary
        # Hosts
        dataHosts = {}
        for host in hosts:
            log.debug('Host is %s name is %s \n' % (host, host.name))
            # Note that BuildQuery will return a list so need to use sum function
            statSysUpTime = BuildQuery(perfManager, (StatCheck(perf_dict, 'sys.uptime.latest')), "", host, interval)
            if statSysUpTime:
                sysUpTime = float(sum(statSysUpTime[0].value[0].value))
                dataHosts['sysUpTime'] = sysUpTime
            statMemUsage = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.usage.minimum')), "", host, interval)
            if statMemUsage:
                memUsage = (float(sum(statMemUsage[0].value[0].value)) / 100)
                dataHosts['memUsage'] = memUsage
            statMemSwapused = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.swapused.maximum')), "", host, interval)
            if statMemSwapused:
                memSwapused = (float(sum(statMemSwapused[0].value[0].value)) * 1024)
                dataHosts['memSwapused'] = memSwapused
            statMemGranted = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.granted.maximum')), "", host, interval)
            if statMemGranted:
                memGranted = (float(sum(statMemGranted[0].value[0].value)) * 1024)
                dataHosts['memGranted'] = memGranted
            statMemActive = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.active.maximum')), "", host, interval)
            if statMemActive:
                memActive = (float(sum(statMemActive[0].value[0].value)) * 1024)
                dataHosts['memActive'] = memActive
            statDiskUsage = BuildQuery(perfManager, (StatCheck(perf_dict, 'disk.usage.average')), "", host, interval)
            if statDiskUsage:
                diskUsage = (float(sum(statDiskUsage[0].value[0].value)) * 1024)
                dataHosts['diskUsage'] = diskUsage
            statCpuUsageMin = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usage.minimum')), "", host, interval)
            if statCpuUsageMin:
                cpuUsageMin = (float(sum(statCpuUsageMin[0].value[0].value))  / 100)
                dataHosts['cpuUsageMin'] = cpuUsageMin
            statCpuUsageMax = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usage.maximum')), "", host, interval)
            if statCpuUsageMax:
                cpuUsageMax = (float(sum(statCpuUsageMax[0].value[0].value))  / 100)
                dataHosts['cpuUsageMax'] = cpuUsageMax
            statCpuUsageAvg = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usage.average')), "", host, interval)
            if statCpuUsageAvg:
                cpuUsageAvg = (float(sum(statCpuUsageAvg[0].value[0].value))  / 100)
                dataHosts['cpuUsageAvg'] = cpuUsageAvg
            statCpuUsage = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usagemhz.average')), "", host, interval)
            if statCpuUsage:
                cpuUsage = (float(sum(statCpuUsage[0].value[0].value))  * 1000000)
                dataHosts['cpuUsage'] = cpuUsage
            statCpuReservedcapacity = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.reservedCapacity.average')), "", host, interval)
            if statCpuReservedcapacity:
                cpuReservedcapacity = (float(sum(statCpuReservedcapacity[0].value[0].value))  * 1000000)
                dataHosts['cpuReservedcapacity'] = cpuReservedcapacity

        # Guest VMs
        dataGuests = {}
        for vm in vms:
            log.debug('vm is %s name is %s \n' % (vm, vm.name))
            # Note that BuildQuery will return a list so need to use sum function
            dataGuest = {}
            try:
                powerState = vm.runtime.powerState
            except:
                dataGuest['powerState'] = 'poweredOff'
                continue                # go to next VM
            dataGuest['powerState'] = powerState
            if powerState != 'poweredOn':
                dataGuest['adminStatus'] = 0
                dataGuest['operStatus'] = 0
                if powerState == 'poweredOff':
                    dataGuest['adminStatus'] = 2
                elif powerState == 'suspended':
                    dataGuest['adminStatus'] = 3
            else:        
                statMemUsage = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.usage.minimum')), "", vm, interval)
                if statMemUsage:
                    memUsage = (float(sum(statMemUsage[0].value[0].value)) / 100 )
                    dataGuest['memUsage'] = memUsage
                statMemOverhead = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.overhead.minimum')), "", vm, interval)
                if statMemOverhead:
                    memOverhead = (float(sum(statMemOverhead[0].value[0].value)) * 1024 )
                    dataGuest['memOverhead'] = memOverhead
                statMemConsumed = BuildQuery(perfManager, (StatCheck(perf_dict, 'mem.consumed.minimum')), "", vm, interval)
                if statMemConsumed:
                    memConsumed = (float(sum(statMemConsumed[0].value[0].value)) * 1024 )
                    dataGuest['memConsumed'] = memConsumed
                statDiskUsage = BuildQuery(perfManager, (StatCheck(perf_dict, 'disk.usage.average')), "", vm, interval)
                if statDiskUsage:
                    diskUsage = (float(sum(statDiskUsage[0].value[0].value)) * 1024 )
                    dataGuest['diskUsage'] = diskUsage
                statCpuUsageMin = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usage.minimum')), "", vm, interval)
                if statCpuUsageMin:
                    cpuUsageMin = (float(sum(statCpuUsageMin[0].value[0].value)) / 100 )
                    dataGuest['cpuUsageMin'] = cpuUsageMin
                statCpuUsageMax = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usage.maximum')), "", vm, interval)
                if statCpuUsageMax:
                    cpuUsageMax = (float(sum(statCpuUsageMax[0].value[0].value)) / 100 )
                    dataGuest['cpuUsageMax'] = cpuUsageMax
                statCpuUsageAvg = BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usage.average')), "", vm, interval)
                if statCpuUsageAvg:
                    cpuUsageAvg = (float(sum(statCpuUsageAvg[0].value[0].value)) / 100 )
                    dataGuest['cpuUsageAvg'] = cpuUsageAvg
                statCpuUsage= BuildQuery(perfManager, (StatCheck(perf_dict, 'cpu.usagemhz.average')), "", vm, interval)
                if statCpuUsage:
                    cpuUsage = (float(sum(statCpuUsage[0].value[0].value)) * 1000000 )
                    dataGuest['cpuUsage'] = cpuUsage
                overallStatus = vm.summary.overallStatus
                operStatus = 0
                if overallStatus == 'green':
                    operStatus = 1
                elif overallStatus == 'red':
                    operStatus = 2
                elif overallStatus == 'yellow':
                    operStatus = 3
                elif overallStatus == 'gray':
                    operStatus = 4
                dataGuest['overallStatus'] = overallStatus
                dataGuest['operStatus'] = operStatus
                dataGuest['adminStatus'] = 1
            dataGuests[vm.name] = dataGuest    

        # Datastores
        dataDatastores = {}
        for datastore in datastores:
            log.debug('datastore is %s name is %s \n' % (datastore, datastore.name))
            # Note that BuildQuery will return a list so need to use sum function
            dataDatastore = {}
            if datastore.summary.accessible:
                dataDatastore['diskFreeSpace'] = datastore.summary.freeSpace
                dataDatastore['connectionStatus'] = 1
            else:    
                dataDatastore['diskFreeSpace'] = None
                dataDatastore['connectionStatus'] = 2
            dataDatastores[datastore.name] = dataDatastore

        #log.debug(' dataHosts is %s \n' % (dataHosts))
        #log.debug(' dataGuests is %s \n' % (dataGuests))
        #log.debug(' dataDatastores is %s \n' % (dataDatastores))

        data = self.new_data()
        ds0 = config.datasources[0]
        for ds in config.datasources:
            #log.debug('ds is %s and hosts is %s and vms is %s and datastores is %s \n' % (ds, hosts, vms, datastores))
            #log.debug(' Datasource is %s and datasource.component is %s and datasource.template is %s and params is %s and plugin is %s \n' % (ds.datasource, ds.component, ds.template, ds.params, ds.plugin_classname))
            if ds.params['performanceSource'] == 'VMwareHost':

                for datapoint_id in (x.id for x in ds.points):
                    if not dataHosts.has_key(datapoint_id):
                        continue
                    try:
                        value = dataHosts[datapoint_id]
                    except Exception, e:
                        log.error('Failed to get value datapoint for ESXi host, error is %s' % (e))
                        continue
                    dpname = '_'.join((ds.datasource, datapoint_id))
                    data['values'][ds.component][dpname] = (value, 'N')

            elif ds.params['performanceSource'] == 'VMwareGuest':
                if ds.params['isMonitored']:
                    for vm, vmdata in dataGuests.iteritems():
                        if vm == ds.component:
                            for datapoint_id in (x.id for x in ds.points):
                                if not vmdata.has_key(datapoint_id):
                                    continue
                                try:
                                    value = vmdata[datapoint_id]
                                except Exception, e:
                                    log.error('Failed to get value datapoint for ESXi guest, error is %s' % (e))
                                    continue
                                dpname = '_'.join((ds.datasource, datapoint_id))
                                data['values'][ds.component][dpname] = (value, 'N')


            elif ds.params['performanceSource'] == 'VMwareDatastore':
                if ds.params['isMonitored']:
                    for datastore, datastoredata in dataDatastores.iteritems():
                        if datastore == ds.component:
                            for datapoint_id in (x.id for x in ds.points):
                                if not datastoredata.has_key(datapoint_id):
                                    continue
                                try:
                                    value = datastoredata[datapoint_id]
                                except Exception, e:
                                    log.error('Failed to get value datapoint for ESXi datastore, error is %s' % (e))
                                    continue
                                dpname = '_'.join((ds.datasource, datapoint_id))
                                data['values'][ds.component][dpname] = (value, 'N')
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


