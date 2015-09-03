################################################################################
#
# This program is part of the VMwareESXiMonitor Zenpack for Zenoss.
# Copyright (C) 2014 Eric Enns, Matthias Kittl.
#
# This program can be used under the GNU General Public License version 2
# You can find full information here: http://www.zenoss.com/oss
#
################################################################################

from Products.ZenReports.Utils import Record

class esxi_plugin(object):
    "The ESXi Report Plugin"

    def run(self, dmd, args):
        report = []
        for esxiHost in dmd.Devices.Server.VMware.ESXi.getSubDevices():
            for esxiVm in esxiHost.esxiVm():
                report.append(
                    Record(
                        esxiHostName = esxiHost.name(),
                        esxiHostPath = esxiHost.getPrimaryUrlPath(),
                        esxiVmName = esxiVm.name(),
                        esxiVmPath = esxiVm.getPrimaryUrlPath(),
                        osType = esxiVm.osType,
                        memory = esxiVm.memory,
                        adminStatus = esxiVm.adminStatus(),
                        operStatus = esxiVm.operStatus(),
                    )
                )
        return report

