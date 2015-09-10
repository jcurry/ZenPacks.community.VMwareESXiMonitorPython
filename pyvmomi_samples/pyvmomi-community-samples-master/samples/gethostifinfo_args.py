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
#from datetime import timedelta, datetime
import datetime

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

def main():
    global content, hosts, hostPgDict
    host, user, password = GetArgs()
    serviceInstance = SmartConnect(host=host,
                                   user=user,
                                   pwd=password,
                                   port=443)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()
    #Disconnect(serviceInstance)
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
    print('Hosts is %s \n ' % (hosts))
    for host in hosts:
        print('Host is %s \n' % (host))



        """
        statInt = interval * 3  # There are 3 20s samples in each minute
        statSysUpTime = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'sys.uptime.latest')), "", host, interval)
        #statSysUpTime = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'sys.uptime.latest')), "", host, 0)
        sysUpTime = (float(sum(statSysUpTime[0].value[0].value)) / statInt) 
        #sysUpTime = float(sum(statSysUpTime[0].value[0].value))
        print(' sysUpTime is %s \n' % (sysUpTime))

        statCpuUsage = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'cpu.usage.average')), "", host, interval)
        cpuUsage = ((float(sum(statCpuUsage[0].value[0].value)) / statInt) / 100)
        print(' cpuUsage is %s \n' % (cpuUsage))

        statMemoryActive = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'mem.active.average')), "", host, interval)
        MemoryActive = ((float(sum(statMemoryActive[0].value[0].value)) / statInt) / 100)
        print(' MemoryActive is %s \n' % (MemoryActive))
        
        """

        print(' -------- Start of config stuff ---------- \n')
        #print('nw vnic test is %s \n' % (host.config.network.vnic))
        for v in host.config.network.vnic:
            print('vnic is %s \n' % (v))
            print('vnic device is %s \n' % (v.device))
            print('vnic mac is %s \n' % (v.mac))
            print('vnic mtu is %s \n' % (v.spec.mtu))
        for p in host.config.network.pnic:
            print('pnic is %s \n' % (p))
            print('pnic device is %s \n' % (p.device))
            print('pnic mac is %s \n' % (p.mac))
            #print('pnic ipAddress is %s \n' % (p.spec.ip.ipAddress))
            print('pnic spec is %s \n' % (p.spec))
            if p.spec.ip:
                print('pnic ip is %s \n' % (p.spec.ip))
                print('Address is %s \n' % (p.spec.ip.ipAddress))

            print('pnic linkSpeed is %s \n' % (p.linkSpeed))
        #print('nw pnic test is %s \n' % (host.config.network.pnic.spec))
        #print('nw pnic test is %s \n' % (host.config.network.pnic.mac))
        #print('nw pnic test is %s \n' % (host.config.network.pnic.device))
        #print('osVendor is %s \n' % (host.summary.config.product.vendor))
        #print('osProduct is %s \n' % (host.summary.config.product.fullName))
        #print('hwVendor is %s \n' % (host.summary.hardware.vendor))
        #print('hwProduct is %s \n' % (host.summary.hardware.model))
        #print('memorySize is %s \n' % (host.summary.hardware.memorySize))
        #print('cpuMhz is %s \n' % (host.summary.hardware.cpuMhz))
        #print('cpuModel is %s \n' % (host.summary.hardware.cpuModel))
        #print('numCpuCores is %s \n' % (host.summary.hardware.numCpuCores))
        #print('numCpuPkgs is %s \n' % (host.summary.hardware.numCpuPkgs))
        #print('numCpuThreads is %s \n' % (host.summary.hardware.numCpuThreads))
        #print('numNics is %s \n' % (host.summary.hardware.numNics))
        #print('esxiHostName is %s \n' % (host.summary.config.name))
        #print('vmotionState is %s \n' % (host.summary.config.vmotionEnabled))
        print(' -------- End of config stuff ---------- \n')
        

    vms = GetVMs(content)

    """
    for vm in vms:
        print('VM is %s \n' % (vm))
        statInt = interval * 3  # There are 3 20s samples in each minute
        statSysUpTime = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'sys.uptime.latest')), "", vm, interval)
        #statSysUpTime = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'sys.uptime.latest')), "", vm, 0)
        sysUpTime = (float(sum(statSysUpTime[0].value[0].value)) / statInt) 
        #sysUpTime = float(sum(statSysUpTime[0].value[0].value))
        print(' sysUpTime is %s \n' % (sysUpTime))

        statCpuUsage = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'cpu.usage.average')), "", vm, interval)
        cpuUsage = ((float(sum(statCpuUsage[0].value[0].value)) / statInt) / 100)
        print(' cpuUsage is %s \n' % (cpuUsage))

        statMemoryActive = BuildQuery(perfManager, vchtime, (StatCheck(perf_dict, 'mem.active.average')), "", vm, interval)
        MemoryActive = ((float(sum(statMemoryActive[0].value[0].value)) / statInt) / 100)
        print(' MemoryActive is %s \n' % (MemoryActive))
        

    """    
# Main section
if __name__ == "__main__":
    sys.exit(main())
