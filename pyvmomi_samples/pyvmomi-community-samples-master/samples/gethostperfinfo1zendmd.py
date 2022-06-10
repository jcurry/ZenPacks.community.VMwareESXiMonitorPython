#!/usr/bin/env zendmd
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
import pprint

def GetVMElements(content, elementList):
    print("Getting all ESX elements ...")
    #elementList = [vim.HostSystem]
    #host_view = content.viewManager.CreateContainerView(content.rootFolder,
    #                                                    [vim.HostSystem],
    #                                                    True)
    element_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        elementList,
                                                        True)
    obj = [element for element in element_view.view]
    element_view.Destroy()
    return obj

def GetVMHosts(content, elementList):
    print("Getting all ESX hosts ...")
    #elementList = [vim.HostSystem]
    #host_view = content.viewManager.CreateContainerView(content.rootFolder,
    #                                                    [vim.HostSystem],
    #                                                    True)
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        elementList,
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

    #hosts = GetVMHosts(content)
    hosts = GetVMElements(content, [vim.HostSystem])
    print('Hosts is %s \n ' % (hosts))
    for host in hosts:
        #if host.name == 'swiesxi6.steinwall.lan':
	    #print('Host Perf provide summary is %s \n' % (perfManager.QueryPerfProviderSummary(host)))
	    print('Host is %s name is %s \n' % (host, host.name))

    #vms = GetVMs(content)
    vms = GetVMElements(content, [vim.VirtualMachine])

    print(' ---------Virtual Machines-----------')
    for vm in vms:
        print('VM is %s name is %s \n' % (vm, vm.name))
        print('VM runtime.powerState is %s \n' % (vm.runtime.powerState))
        print('VM summary.overallStatus is %s \n' % (vm.summary.overallStatus))
                
    #datastores = GetDatastores(content)
    datastores = GetVMElements(content, [vim.Datastore])

    print(' ---------Datastores -----------')
    for datastore in datastores:
        print('Datastore is %s name is %s \n' % (datastore, datastore.name))
        print('Datastore accessible is  %s  \n' % (datastore.summary.accessible))
        print('Datastore diskFreeSpace is  %s  \n' % (datastore.summary.freeSpace))

# Main section
if __name__ == "__main__":
    sys.exit(main())
