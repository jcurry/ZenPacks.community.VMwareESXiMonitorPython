################################################################################
#
# This program is part of the VMwareESXiMonitor Zenpack for Zenoss.
# Copyright (C) 2014 Eric Enns, Matthias Kittl.
#
# This program can be used under the GNU General Public License version 2
# You can find full information here: http://www.zenoss.com/oss
#
################################################################################

from Products.ZenModel import RRDDataSource
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenEvents.ZenEventClasses import Cmd_Fail
from Products.ZenUtils.Utils import executeStreamCommand
from Products.ZenModel.ZenPackPersistence import ZenPackPersistence
from Products.ZenWidgets import messaging
import cgi, time

#Templates for the command
vmwareDatastorePerfTemplate = ("/usr/bin/perl ${here/ZenPackManager/packs/ZenPacks.community.VMwareESXiMonitor/path}/libexec/esxi_monitor.pl --server ${dev/manageIp} --username ${dev/zVSphereUsername} --password '${dev/zVSpherePassword}' --options 'datastoreperf:${here/id}' | tail -n1")
vmwareGuestPerfTemplate = ("/usr/bin/perl ${here/ZenPackManager/packs/ZenPacks.community.VMwareESXiMonitor/path}/libexec/esxi_monitor.pl --server ${dev/manageIp} --username ${dev/zVSphereUsername} --password '${dev/zVSpherePassword}' --options 'guestperf:${here/id}' | tail -n1")
vmwareHostPerfTemplate = ("/usr/bin/perl ${here/ZenPackManager/packs/ZenPacks.community.VMwareESXiMonitor/path}/libexec/esxi_monitor.pl --server ${dev/manageIp} --username ${dev/zVSphereUsername} --password '${dev/zVSpherePassword}' --options 'hostperf:${dev/esxiHostName}' | tail -n1")

class VMwareDataSource(ZenPackPersistence, RRDDataSource.SimpleRRDDataSource):
    ZENPACKID = 'ZenPacks.community.VMwareESXiMonitor'

    sourcetypes = ('VMware',)

    sourcetype = 'VMware'
    eventClass = Cmd_Fail
    performanceSource = ''
    instance = ''

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
        return True

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

