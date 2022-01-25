#!/usr/bin/env python
#
# cpaggen - May 16 2015 - Proof of Concept (little to no error checks)
#  - rudimentary args parser
#  - GetHostsPortgroups() is quite slow; there is probably a better way
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import sys
from datetime import timedelta, datetime
#import datetime

import pprint


def GetVMHosts(content):
    print("Getting all ESX hosts ...")
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj


def GetVMs(content):
    print("Getting all VMs ...")
    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return obj

def GetDatastores(content):
    print("Getting all Datastoress ...")
    datastore_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.Datastore],
                                                      True)
    obj = [datastore for datastore in datastore_view.view]
    datastore_view.Destroy()
    return obj

def GetArgs():
    if len(sys.argv) != 4:
        host = raw_input("vCenter IP: ")
        user = raw_input("Username: ")
        password = raw_input("Password: ")
    else:
        host, user, password = sys.argv[1:]
    return host, user, password

def StatCheck(perf_dict, counter_name):
    counter_key = perf_dict[counter_name]
    return counter_key

def BuildQueryMaxSample(perfManager, counterId, instance, host, interval):
    # Note that vim.PerformanceManager.QuerySpec returns a list - albeit of 1 sample with maxSample=1

    metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)
    #print(' counterId is %s and host is %s  and metricId is %s \n' % (counterId, host, metricId))


    query = vim.PerformanceManager.QuerySpec(intervalId=interval, entity=host, metricId=[metricId], maxSample=1)
    perfResults = perfManager.QueryPerf(querySpec=[query])
    if perfResults:
        return perfResults
    else:
        print('ERROR: Performance results empty.  TIP: Check time drift on source and vCenter server')
        print('Troubleshooting info:')
        print(query)
        #exit()
        return

def BuildQueryVchtime(perfManager, vchtime, counterId, instance, host, interval):
    # Note that vim.PerformanceManager.QuerySpec returns a list - albeit of 1 sample with maxSample=1

    metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)
    #print(' counterId is %s and host is %s  and metricId is %s \n' % (counterId, host, metricId))
    startTime = vchtime - timedelta(seconds=60)
    endTime = vchtime - timedelta(seconds=40)

    #query = vim.PerformanceManager.QuerySpec(intervalId=interval, entity=host, metricId=[metricId], maxSample=1)
    query = vim.PerformanceManager.QuerySpec(intervalId=interval, entity=host, metricId=[metricId], startTime=startTime, endTime=endTime)
    perfResults = perfManager.QueryPerf(querySpec=[query])
    if perfResults:
        return perfResults
    else:
        print('ERROR: Performance results empty.  TIP: Check time drift on source and vCenter server')
        print('Troubleshooting info:')
        print(query)
        #exit()
        return

def main():
    global content, hosts, hostPgDict
    host, user, password = GetArgs()
    #host = '10.0.0.125'
    #user = 'jane'
    #password = 'notthis'
    serviceInstance = SmartConnect(host=host,
                                   user=user,
                                   pwd=password,
                                   port=443)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()
    vchtime = serviceInstance.CurrentTime()

    hosts = GetVMHosts(content)
    perfManager = content.perfManager
    #print(' ------------ End of perfManager--------------')
    perfCounters = perfManager.perfCounter
    #print(' perfCounter is %s \n' % (perfCounters))

   # Get all the performance counters
    perf_dict = {}
    perfList = perfManager.perfCounter
    for counter in perfList:
        counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
        perf_dict[counter_full] = counter.key
    #print( 'perf_dict is %s \n\n' % (perf_dict))
    #print('-------perf Dict --------')
    #pprint.pprint(perf_dict)

    interval = 20
    print('Hosts is %s \n ' % (hosts))
    for host in hosts:
        #if host.name == 'swiesxi6.steinwall.lan':
	    #print('Host Perf provide summary is %s \n' % (perfManager.QueryPerfProviderSummary(host)))
	    print('Host is %s name is %s \n' % (host, host.name))
	    # Note that BuildQuery will return a list so need to use sum function
	    statSysUpTimeMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'sys.uptime.latest')), "", host, interval)
	    statSysUpTimeVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'sys.uptime.latest')), "", host, interval)
	    if statSysUpTimeMaxSample and statSysUpTimeVchtime:
		#print('statSysUpTime is %s \n' % (statSysUpTime))
		sysUpTimeMaxSample = float(sum(statSysUpTimeMaxSample[0].value[0].value))
		sysUpTimeVchtime = float(sum(statSysUpTimeVchtime[0].value[0].value))
		print(' sysUpTimeMaxSample is %s  and sysUpTimeVchtime is %s \n' % (sysUpTimeMaxSample, sysUpTimeVchtime))
	    statCpuUsageVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'cpu.usage.average')), "", host, interval)
	    statCpuUsageMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'cpu.usage.average')), "", host, interval)
	    if statCpuUsageMaxSample and statCpuUsageVchtime:
		cpuUsageMaxSample = (float(sum(statCpuUsageMaxSample[0].value[0].value))  / 100)
		cpuUsageVchtime = (float(sum(statCpuUsageVchtime[0].value[0].value))  / 100)
		print(' cpuUsageMaxSample is %s and cpuUsageVchtime is %s \n' % (cpuUsageMaxSample, cpuUsageVchtime))
	    statMemoryActiveVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'mem.active.maximum')), "", host, interval)
	    statMemoryActiveMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'mem.active.maximum')), "", host, interval)
	    if statMemoryActiveMaxSample and statMemoryActiveVchtime:
		MemoryActiveMaxSample = (float(sum(statMemoryActiveMaxSample[0].value[0].value)) * 1024)
		MemoryActiveVchtime = (float(sum(statMemoryActiveVchtime[0].value[0].value)) * 1024)
		print(' MemoryActiveMaxSample is %s and MemoryActiveVchtime is %s  \n' % (MemoryActiveMaxSample, MemoryActiveVchtime))
		

    vms = GetVMs(content)

    print(' ---------Virtual Machines-----------')
    for vm in vms:
        #print('VM is %s name is %s \n' % (vm, vm.name))
        #print('VM runtime.powerState is %s \n' % (vm.runtime.powerState))
        #print('VM summary.overallStatus is %s \n' % (vm.summary.overallStatus))
        #print('VM Perf provide summary is %s \n' % (perfManager.QueryPerfProviderSummary(vm)))
        #if vm.runtime.powerState == 'poweredOn' and  vm.name == 'SWIDVM33':
        if vm.runtime.powerState == 'poweredOn' and 'centos' in vm.name:
            print('VM is %s name is %s \n' % (vm, vm.name))
            print('VM runtime.powerState is %s \n' % (vm.runtime.powerState))
            print('VM summary.overallStatus is %s \n' % (vm.summary.overallStatus))
            statSysUpTimeVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'sys.uptime.latest')), "", vm, interval)
            statSysUpTimeMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'sys.uptime.latest')), "", vm, interval)
            if statSysUpTimeMaxSample and statSysUpTimeVchtime:
                sysUpTimeMaxSample = float(sum(statSysUpTimeMaxSample[0].value[0].value))
                sysUpTimeVchtime = float(sum(statSysUpTimeVchtime[0].value[0].value))
                print(' sysUpTimeMaxSample is %s and sysUpTimeVchtime is %s \n' % (sysUpTimeMaxSample, sysUpTimeVchtime))

            statCpuUsageVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'cpu.usagemhz.average')), "", vm, interval)
            statCpuUsageMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'cpu.usagemhz.average')), "", vm, interval)
            if statCpuUsageMaxSample and statCpuUsageVchtime:
                cpuUsageMaxSample = (float(sum(statCpuUsageMaxSample[0].value[0].value))  * 1000000)
                cpuUsageVchtime = (float(sum(statCpuUsageVchtime[0].value[0].value))  * 1000000)
                print(' cpuUsageMaxSample is %s and cpuUsagVchtime is %s \n' % (cpuUsageMaxSample, cpuUsageVchtime))

            statCpuUsageAvgVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'cpu.usage.average')), "", vm, interval)
            statCpuUsageAvgMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'cpu.usage.average')), "", vm, interval)
            if statCpuUsageAvgMaxSample and statCpuUsageAvgVchtime:
                cpuUsageAvgMaxSample = (float(sum(statCpuUsageAvgMaxSample[0].value[0].value))  / 100)
                cpuUsageAvgVchtime = (float(sum(statCpuUsageAvgVchtime[0].value[0].value))  / 100)
                print(' cpuUsageAvgMaxSample is %s  and cpuUsageAvgVchtime is %s \n' % (cpuUsageAvgMaxSample, cpuUsageAvgVchtime))

            statMemUsageVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'mem.usage.minimum')), "", vm, interval)
            statMemUsageMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'mem.usage.minimum')), "", vm, interval)
            if statMemUsageMaxSample and statMemUsageVchtime:
                #print(' statMemUsage is %s \n' % (statMemUsage))
                memUsageMaxSample = (float(sum(statMemUsageMaxSample[0].value[0].value)) / 100)
                memUsageVchtime = (float(sum(statMemUsageVchtime[0].value[0].value)) / 100)
                print(' memUsageMaxSample is %s and memUsageVchtime is %s \n' % (memUsageMaxSample, memUsageVchtime))

            statMemConsumedVchtime = BuildQueryVchtime(perfManager, vchtime, (StatCheck(perf_dict, 'mem.consumed.minimum')), "", vm, interval)
            statMemConsumedMaxSample = BuildQueryMaxSample(perfManager, (StatCheck(perf_dict, 'mem.consumed.minimum')), "", vm, interval)
            if statMemConsumedMaxSample and statMemConsumedVchtime:
                memConsumedMaxSample = (float(sum(statMemConsumedMaxSample[0].value[0].value)) * 1024)
                memConsumedVchtime = (float(sum(statMemConsumedVchtime[0].value[0].value)) * 1024)
                print(' memConsumedMaxSample is %s and memConsumedVchtime is %s \n' % (memConsumedMaxSample, memConsumedVchtime))
                
    datastores = GetDatastores(content)

    """
    print(' ---------Datastores -----------')
    for datastore in datastores:
        print('Datastore is %s name is %s \n' % (datastore, datastore.name))
        print('Datastore accessible is  %s  \n' % (datastore.summary.accessible))
        print('Datastore diskFreeSpace is  %s  \n' % (datastore.summary.freeSpace))
    """

# Main section
if __name__ == "__main__":
    sys.exit(main())
