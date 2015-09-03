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

import commands, re, os
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import sys
import datetime

import Globals
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap

class VMwareESXiHostMap(PythonPlugin):
    maptype = "VMwareESXiHostMap"
    compname = ""
    deviceProperties = PythonPlugin.deviceProperties + (
        'zVSphereUsername',
        'zVSpherePassword'
    )

    def collect(self, device, log):

        def GetVMHosts(content):
            print("Getting all ESX hosts ...")
            host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                                [vim.HostSystem],
                                                                True)
            obj = [host for host in host_view.view]
            host_view.Destroy()
            return obj

        def StatCheck(perf_dict, counter_name):
            counter_key = perf_dict[counter_name]
            return counter_key

        def BuildQuery(perfManager, vchtime, counterId, instance, host, interval):
            #perfManager = content.perfManager
            metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)
            #print(' counterId is %s and host is %s  and metricId is %s \n' % (counterId, host, metricId))

            startTime = vchtime - datetime.timedelta(minutes=(interval + 1))
            endTime = vchtime - datetime.timedelta(minutes=1)

            print('starttime is %s, endtime is %s, interval is %s \n' % (startTime, endTime, interval))

            if interval != 0:
                query = vim.PerformanceManager.QuerySpec(intervalId=interval, entity=host, metricId=[metricId], startTime=startTime, endTime=endTime)
            else:
                startTime = datetime.datetime.now() - datetime.timedelta(minutes=1)
                endTime = datetime.datetime.now()
                query = vim.PerformanceManager.QuerySpec(entity=host, metricId=[metricId], startTime=startTime, endTime=endTime)
            perfResults = perfManager.QueryPerf(querySpec=[query])
            if perfResults:
                return perfResults
            else:
                print('ERROR: Performance results empty.  TIP: Check time drift on source and vCenter server')
                print('Troubleshooting info:')
                print('vCenter/host date and time: {}'.format(vchtime))
                print('Start perf counter time   :  {}'.format(startTime))
                print('End perf counter time     :  {}'.format(endTime))
                print(query)
                exit()



        log.info('Getting VMware ESXi host info for device %s' % device.id)
        global content, hosts
        username = getattr(device, 'zVSphereUsername', None)
        password = getattr(device, 'zVSpherePassword', None)
        if (not username or not password):
            return None
        
        serviceInstance = SmartConnect(host=device.id,
                                       user=username,
                                       pwd=password,
                                       port=443)
        atexit.register(Disconnect, serviceInstance)
        content = serviceInstance.RetrieveContent()
        hosts = GetVMHosts(content)
        perfManager = content.perfManager
        vchtime = serviceInstance.CurrentTime()

       # Get all the performance counters
        perf_dict = {}
        perfList = content.perfManager.perfCounter
        for counter in perfList:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
            perf_dict[counter_full] = counter.key
        #print( 'perf_dict is %s \n\n' % (perf_dict))
        #print('-------perf Dict --------')
        #pprint.pprint(perf_dict)

        interval = 20

        for host in hosts:
            print('Host is %s \n' % (host))

            statInt = interval * 3  # There are 3 20s samples in each minute

            print(' -------- Start of config stuff ---------- \n')
            print('osVendor is %s \n' % (host.summary.config.product.vendor))
            print('osProduct is %s \n' % (host.summary.config.product.fullName))
            print('hwVendor is %s \n' % (host.summary.hardware.vendor))
            print('hwProduct is %s \n' % (host.summary.hardware.model))
            print('memorySize is %s \n' % (host.summary.hardware.memorySize))
            print('cpuMhz is %s \n' % (host.summary.hardware.cpuMhz))
            print('cpuModel is %s \n' % (host.summary.hardware.cpuModel))
            print('numCpuCores is %s \n' % (host.summary.hardware.numCpuCores))
            print('numCpuPkgs is %s \n' % (host.summary.hardware.numCpuPkgs))
            print('numCpuThreads is %s \n' % (host.summary.hardware.numCpuThreads))
            print('numNics is %s \n' % (host.summary.hardware.numNics))
            print('esxiHostName is %s \n' % (host.summary.config.name))
            print('vmotionState is %s \n' % (host.summary.config.vmotionEnabled))
            print(' -------- End of config stuff ---------- \n')






        (stat, results) = commands.getstatusoutput( "/usr/bin/perl %s --server %s --username %s --password '%s'" % (cmd, device.id, username, password))
        if (stat != 0):
            return None
        else:
            return results

    def process(self, device, results, log):
        log.info('Processing VMware ESXi host info for device %s' % device.id)
        rlines = results.split("\n")
        for line in rlines:
            if line.startswith("Warning:"):
                log.warning('%s' % line)
            elif re.search(';', line):
                maps = []
                osVendor, osProduct, hwVendor, hwProduct, memorySize, cpuMhz, cpuModel, numCpuCores, numCpuPkgs, numCpuThreads, numNics, esxiHostName, vmotionState = line.split(';')
                maps.append(ObjectMap({'totalMemory': memorySize}, compname='hw'))
                maps.append(ObjectMap({'totalSwap': 0}, compname='os'))
                om = self.objectMap()
                om.setOSProductKey = osProduct
                om.setHWProductKey = hwProduct
                om.cpuMhz = long(cpuMhz)
                om.cpuModel = cpuModel
                om.numCpuCores = int(numCpuCores)
                om.numCpuPkgs = int(numCpuPkgs)
                om.numCpuCoresPerPkgs = int(numCpuCores) / int(numCpuPkgs)
                om.numCpuThreads = int(numCpuThreads)
                om.numNics = int(numNics)
                om.esxiHostName = esxiHostName
                if int(vmotionState) == 0:
                    om.vmotionState = True
                else:
                    om.vmotionState = False
                maps.append(om)

        return maps

