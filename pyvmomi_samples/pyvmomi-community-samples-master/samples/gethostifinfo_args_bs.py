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

    print('Hosts is %s \n ' % (hosts))
    for host in hosts:
        print('Host is %s \n' % (host))

        print(' -------- Start of config stuff ---------- \n')
        #print('nw vnic test is %s \n' % (host.config.network.vnic))
        for v in host.config.network.vnic:
            print('vnic is %s \n' % (v))
            print('vnic spec is %s \n' % (v.spec))
            print('vnic device is %s \n' % (v.device))
            print('vnic description is %s \n' % (v.portgroup))
            print('vnic mac is %s \n' % (v.spec.mac))
            print('vnic mtu is %s \n' % (v.spec.mtu))
            if v.spec.ip:
                print('Address is %s \n' % (v.spec.ip.ipAddress))
        for p in host.config.network.pnic:
            print('pnic is %s \n' % (p))
            print('pnic device is %s \n' % (p.device))
            print('pnic mac is %s \n' % (p.mac))
            print('pnic spec is %s \n' % (p.spec))
            if p.spec.ip:
                print('pnic ip is %s \n' % (p.spec.ip))
                print('Address is %s \n' % (p.spec.ip.ipAddress))

            if p.linkSpeed:
                print('pnic linkSpeed is %s \n' % (p.linkSpeed))
                print('pnic linkSpeed speed is is %s \n' % (p.linkSpeed.speedMb))
                print('pnic linkSpeed duplex is is %s \n' % (p.linkSpeed.duplex))
        #print('nw pnic test is %s \n' % (host.config.network.pnic.spec))
        #print('nw pnic test is %s \n' % (host.config.network.pnic.mac))
        #print('nw pnic test is %s \n' % (host.config.network.pnic.device))
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
