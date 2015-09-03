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
from twisted.web.client import getPage
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
import json

#Templates for the command
vmwareDatastorePerfTemplate = ("/usr/bin/perl ${here/ZenPackManager/packs/ZenPacks.community.VMwareESXiMonitor/path}/libexec/esxi_monitor.pl --server ${dev/manageIp} --username ${dev/zVSphereUsername} --password '${dev/zVSpherePassword}' --options 'datastoreperf:${here/id}' | tail -n1")
vmwareGuestPerfTemplate = ("/usr/bin/perl ${here/ZenPackManager/packs/ZenPacks.community.VMwareESXiMonitor/path}/libexec/esxi_monitor.pl --server ${dev/manageIp} --username ${dev/zVSphereUsername} --password '${dev/zVSpherePassword}' --options 'guestperf:${here/id}' | tail -n1")
vmwareHostPerfTemplate = ("/usr/bin/perl ${here/ZenPackManager/packs/ZenPacks.community.VMwareESXiMonitor/path}/libexec/esxi_monitor.pl --server ${dev/manageIp} --username ${dev/zVSphereUsername} --password '${dev/zVSpherePassword}' --options 'hostperf:${dev/esxiHostName}' | tail -n1")

# Setup logging
import logging
log = logging.getLogger('zen.VMwareESXiMonitorPython')

# PythonCollector Imports
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSource, PythonDataSourcePlugin

class VMwareDataSource(PythonDataSource):
    """ Description here
    """
    ZENPACKID = 'ZenPacks.community.VMwareESXiMonitorPython'

    #sourcetypes = ('VMwareDataSource',)
    sourcetypes = ('VMware',)
    sourcetype = sourcetypes[0]
    eventClass = '/Status/VMware'
    component = '${here/id}'

    # Custom fields in the datasource - with default values
    # (which can be overriden in template )

    performanceSource = ''
    instance = ''
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
        group = _t('performanceSource'))

    instance = schema.TextLine(
        title = _t(u'Instance'),
        group = _t('instance'))

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
    # Do we need context.id???

        return (
        context.device().id,
        datasource.getCycleTime(context),
        datasource.rrdTemplate().id,
        datasource.id,
        context.id,
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
        #params['CoreName'] = context.coreName
       
        ps = datasource.talesEval(datasource.performanceSource, context)
        #Original ZP has ONE datasource for both device (ESXiHost) and components (ESXiDatasource & ESXiVM)
        # performanceSource designates device/component type - VMwareHost, VMwareDatasource, VMwareGuest
        if ps != 'VMwareHost':
            deviceName = context.device().titleOrId()
        else:
            deviceName = context.titleOrId()

        params['performanceSource'] = ps
        params['instance'] = datasource.talesEval(datasource.instance, context)
        #url = 'http://' + deviceName + ':8080/solr/' + context.coreName + '/admin/mbeans?stats=true&cat=' + params['SolrCat'] + '&key=' + params['SolrKey'] + '&ident=true&wt=json'
        #params['url'] = url
        log.debug(' params is %s \n' % (params))
        return params

    @inlineCallbacks
    def collect(self, config):

        def getData(host, user, password, port, request, log):
        # make a connection
            try:
                conn = connect.SmartConnect(host=host, user=user, pwd=password, port=443)
                if not conn:
                    log.warn('Could not connect to host %s \n' % (host))
                else:
                    response = conn.RetrieveContent()
                    #response = json.loads(response)
                    return response
            except:
                log.warn('Failed to get data from host %s\n' % (host))
                
            # Note: from daemons use a shutdown hook to do this, not the atexit
            #atexit.register(connect.Disconnect, si)

        ds0 = config.datasources[0]

        if not ds0.zVSphereUsername:
            log.warn(' No zVSphereUsername set - cannot collect data')
        if not ds0.zVSpherePassword:
            log.warn(' No zVSpherePassword set - cannot collect data')
        request = ''
        try:
            s = yield getData(ds0.manageIp, ds0.zVSphereUsername, ds0.zVSpherePassword, 443, request, log)
        except Exception, e:
            log.error( "%s: %s", ds0.device, e)
        #continue
        returnValue(s)

    def onResult(self, result, config):
        """
        Called first for success and error.
        You can omit this method if you want the result of the collect method
        to be used without further processing.
        """

        log.debug( 'result is %s ' % (result))
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

        log.debug( 'In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()
        ds0 = config.datasources[0]
        for ds in config.datasources:
            log.debug('test')
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
                'summary': 'Error getting Solrdata with zenpython: %s' % result,
                'eventKey': 'Solr',
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


"""

    #properties which are used in the edit datasource
    _properties = RRDDataSource.RRDDataSource._properties + (
        {'id':'performanceSource', 'type':'string', 'mode':'w'},
        {'id':'instance', 'type':'string', 'mode':'w'},
    )

    _relations = RRDDataSource.RRDDataSource._relations + (
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view': 'editVMwareDataSource',
            'actions': (
                {
                    'id': 'edit',
                    'name': 'Data Source',
                    'action': 'editVMwareDataSource',
                    'permissions': ('View',)
                },
            )
        },
    )

    security = ClassSecurityInfo()

    def getDescription(self):
        return self.instance

    #this tells zenoss that the datasource uses zencommand to collect the data
    def useZenCommand(self):
        #return True
        return False

    #this method add's datapoints depending on what the the datasource's name is
    #not necessarily needed but I like to be lazy
    def addDataPoints(self):
        datastore = ['diskFreeSpace','connectionStatus']
        guest = ['memUsage','memOverhead','memConsumed','diskUsage','cpuUsageMin','cpuUsageMax','cpuUsageAvg','cpuUsage','adminStatus','operStatus']
        host = ['sysUpTime','memUsage','memSwapused','memGranted','memActive','diskUsage','cpuUsageMin','cpuUsageMax','cpuUsageAvg','cpuUsage','cpuReservedcapacity','netReceived','netTransmitted','netPacketsRx','netPacketsTx','netDroppedRx','netDroppedTx']

        if self.id == "VMwareDatastore":
            self.performanceSource = "VMwareDatastore"
            for dp in datastore:
                dpid = self.prepId(dp)
                if not self.datapoints._getOb(dpid, None):
                    self.datapoints.manage_addRRDDataPoint(dpid)
        elif self.id == "VMwareGuest":
            self.performanceSource = "VMwareGuest"
            for dp in guest:
                dpid = self.prepId(dp)
                if not self.datapoints._getOb(dpid, None):
                    self.datapoints.manage_addRRDDataPoint(dpid)
        elif self.id == "VMwareHost":
            self.performanceSource = "VMwareHost"
            for dp in host:
                dpid = self.prepId(dp)
                if not self.datapoints._getOb(dpid, None):
                    self.datapoints.manage_addRRDDataPoint(dpid)

    #this method is called after the datasource is created and also when you click edit
    #datasource I believe
    def zmanage_editProperties(self, REQUEST=None):
        'add some validation'
        if REQUEST:
            self.performanceSource = REQUEST.get('performanceSource', '')
            self.instance = REQUEST.get('instance', '')
        return RRDDataSource.SimpleRRDDataSource.zmanage_editProperties(self, REQUEST)

        self.addDataPoints()

        if REQUEST and self.dataPoints():
            datapoints = self.dataPoints()
            for datapoint in datapoints:
                if REQUEST.has_key('rrdtype'):
                    if REQUEST['rrdtype'] in datapoint.rrdtypes:
                        datapoint.rrdtype = REQUEST['rrdtype']
                    else:
                        messaging.IMessageSender(self).sendToBrowser(
                            'Error',
                            "%s is an invalid Type" % rrdtype,
                            priority=messaging.WARNING
                        )
                        return self.callZenScreen(REQUEST)

                if REQUEST.has_key('rrdmin'):
                    value = REQUEST['rrdmin']
                    if value != '':
                        try:
                            value = long(value)
                        except ValueError:
                            messaging.IMessageSender(self).sendToBrowser(
                                'Error',
                                "%s is an invalid RRD Min" % value,
                                priority=messaging.WARNING
                            )
                            return self.callZenScreen(REQUEST)
                    datapoint.rrdmin = value

                if REQUEST.has_key('rrdmax'):
                    value = REQUEST['rrdmax']
                    if value != '':
                        try:
                            value = long(value)
                        except ValueError:
                            messaging.IMessageSender(self).sendToBrowser(
                                'Error',
                                "%s is an invalid RRD Max" % value,
                                priority=messaging.WARNING
                            )
                            return self.callZenScreen(REQUEST)
                    datapoint.rrdmax = value

                if REQUEST.has_key('createCmd'):
                    datapoint.createCmd = REQUEST['createCmd']

    #this method gets the command that will be run with zencommand    
    def getCommand(self, context):
        if self.performanceSource == "VMwareDatastore":
            cmd = vmwareDatastorePerfTemplate
        elif self.performanceSource == "VMwareGuest":
            cmd = vmwareGuestPerfTemplate
        elif self.performanceSource == "VMwareHost":
            cmd = vmwareHostPerfTemplate
        cmd = RRDDataSource.RRDDataSource.getCommand(self, context, cmd)
        return cmd

    #this method is used to test the datasource in the edit datasource window
    def testDataSourceAgainstDevice(self, testDevice, REQUEST, write, errorLog):
        out = REQUEST.RESPONSE
        # Determine which device to execute against
        device = None
        if testDevice:
            # Try to get specified device
            device = self.findDevice(testDevice)
            if not device:
                errorLog(
                    'No device found',
                    'Cannot find device matching %s' % testDevice,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        elif hasattr(self, 'device'):
            # ds defined on a device, use that device
            device = self.device()
        elif hasattr(self, 'getSubDevicesGen'):
            # ds defined on a device class, use any device from the class
            try:
                device = self.getSubDevicesGen().next()
            except StopIteration:
                # No devices in this class, bail out
                pass
        if not device:
            errorLog(
                'No Testable Device',
                'Cannot determine a device to test against.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        header = ''
        footer = ''
        # Render
        if REQUEST.get('renderTemplate',True):
            header, footer = self.commandTestOutput().split('OUTPUT_TOKEN')

        out.write(str(header))

        # Get the command to run
        command = None
        if self.sourcetype=='VMware':
            command = self.getCommand(device)
        else:
            errorLog(
                'Test Failure',
                'Unable to test %s datasources' % self.sourcetype,
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        if not command:
            errorLog(
                'Test Failure',
                'Unable to create test command.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        write('Executing command %s against %s' %(command, device.id))
        write('')
        start = time.time()
        try:
            executeStreamCommand(command, write)
        except:
            import sys
            write('exception while executing command')
            write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
        write('')
        write('')
        write('DONE in %s seconds' % long(time.time() - start))
        out.write(str(footer))

    security.declareProtected('Change Device', 'manage_testDataSource')

    def manage_testDataSource(self, testDevice, REQUEST):
        ''' Test the datasource by executing the command and outputting the
        non-quiet results.
        '''
        # set up the output method for our test
        out = REQUEST.RESPONSE
        def write(lines):
            ''' Output (maybe partial) result text.
            '''
            # Looks like firefox renders progressive output more smoothly
            # if each line is stuck into a table row.
            startLine = '<tr><td class="tablevalues">'
            endLine = '</td></tr>\n'
            if out:
                if not isinstance(lines, list):
                    lines = [lines]
                for l in lines:
                    if not isinstance(l, str):
                        l = str(l)
                    l = l.strip()
                    l = cgi.escape(l)
                    l = l.replace('\n', endLine + startLine)
                    out.write(startLine + l + endLine)

        errorLog = messaging.IMessageSender(self).sendToBrowser
        return self.testDataSourceAgainstDevice(testDevice, REQUEST, write, errorLog)
"""
