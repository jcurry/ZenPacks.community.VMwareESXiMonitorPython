==============================
ZenPack to support VMware ESXi
==============================

Description
===========
This ZenPack allows Zenoss to monitor VMware ESXi Hosts and their VMs and datastores.
It is based on the ZenPacks.community.VMwareESXiMonitor written by Eric Enns and 
Matthias Kittl ( http://wiki.zenoss.org/ZenPack:VMware_ESXi_Monitor ) but
whereas the older version used the vSphere SDK for Perl and used zencommand performance templates, this
version uses the pyvmomi Python vSphere SDK and PythonCollector performance templates.  This should 
improve performance dramatically, especially where there are many subcomponents. For more information
on the pyvmomi SDK see https://pypi.python.org/pypi/pyvmomi and https://github.com/vmware/pyvmomi .

This version is built with the zenpacklib library (version 1.0.3) so does not have explicit code definitions for
device classes, device and component objects or zProperties.  Templates are also created through zenpacklib.
These elements are all created in the zenpack.yaml file in the main directory of the ZenPack.
See http://zenpacklib.zenoss.com/en/latest/index.html for more information on zenpacklib.

Note that if templates are changed in the zenpack.yaml file then when the ZenPack is reinstalled, the
existing templates will be renamed in the Zenoss ZODB database and the new template from the YAML file
will be installed; thus a backup is effectively taken.  Old templates should be deleted in the Zenoss GUI
when the new version is proven.

Note that the zenpacklib.py file in the main directory of the ZenPack has been modified slightly.  The 
default version places all rrd performance data files directly under a directory named after the device,
with subdirectories for instances of components.
The original ZenPack (and the older standard default behaviour) was to create a directory hierarchy with
an extra subdirectory for relationships.
    * Old:      fred.class.example.org/esxiVm/myVm1/cpuUsage.rrd
    * New:      fred.class.example.org/myVm1/cpuUsage.rrd

To be able to preserve performance data, zenpacklib.py has been modified in the rrdPath method to 
restore the old behaviour.  If zenpacklib.py is changed or upgraded for any reason, this same change
must be made to preserve the data paths.


This ZenPack creates the /Server/VMware and /Server/VMware/ESXi Device Classes. All ESXi Hosts have 
to be added to the /Server/VMware/ESXi Device Class. 

The ZenPack introduces  new zProperties:
    * zVSphereUsername
    * zVSpherePassword

The ZenPack creates a new device object called ESXiHost and new component types for:
    * ESXiVM
    * ESXiDatastore


The Overview display for a device in the /Server/VMware/ESXi class has been extended in the
bottom-right panel to include VMware-specific data.

The /Server/VMware/ESXi device class is supplied with appropriate zProperties, modeler plugins  
and templates applied.  The zPythonClass standard property is set 
to ZenPacks.community.VMwareESXiMonitorPython.ESXiHost for the device class.

Component templates for ESXiHost, ESXiDatastore and ESXiVM  are supplied.  These templates match
those of the original ZenPack (indeed were generated using "zenpacklib.py dump_templates" ).
    * ESXiHost
        * client_eof
        * cpuReservedcapacity
        * cpuUsage
        * cpuUsageAvg
        * cpuUsageMax
        * cpuUsageMin
        * diskUsage
        * memActive
        * memGranted
        * memSwapused
        * memUsage
        * netDroppedRx
        * netDroppedTx
        * netPacketsRx
        * netPacketsTx
        * netReceived
        * netTransmitted
        * sysUpTime

    * ESXiDatastore
        * connectionStatus
        
    * ESXiVM
        * adminStatus
        * operStatus
        * cpuUsage
        * cpuUsageAvg
        * cpuUsageMax
        * cpuUsageMin
        * diskUsage
        * memConsumed
        * memOverhead
        * memUsage


An ethernetCsmacd template is also supplied for /Server/VMware/ESXi which checks operStatus.

Note that there is a single datasource called VMware that is used for both the ESXiHost device
and the ESXiVM and ESXiDatastore components.  It is defined in the datasources directory of the
ZenPack.

These Python templates require the PythonCollector ZenPack to be installed as a 
prerequisite (version >=1.6)

There may be a large number of components for ESXiHost devices, each with a large number of
datapoints.  The cycle time of the templates is set at 300 seconds and it is strongly recommended
that this is not changed. The datasource is constructed so that it is only run once for a given ESXiHost
in a given polling cycle interval and will collect data for the host and all components in that run.

The ZenPack includes a /Status/VMware event, used in the templates, plus a large number of event instances 
under the /VMware/ESXi event class which have all come directly from the earlier ZenPack.

Similarly, there are a large number of VMware MIBs included to replicate the earlier ZenPack.

Administrative status and Operational status of VMs is as follows:

No/not enough data points collected (e.g. new VM has been detected during modeling)

    admin state "blue"
    operating state "blue"

VM powered on and entity is ok:

    admin state "green"
    operating state "green"

VM powered on and entity definitely has a problem:

    admin state "green"
    operating state "red"

VM powered on and entity might have a problem:

    admin state "green"
    operating state "yellow"

VM powered on and entity state is unknown:

    admin state "green"
    operating state "grey"

VM powered off:

    admin state "red"
    operating state "grey"

VM suspended:

    admin state "orange"
    operating state "grey"

VM state unknown:

    admin state "grey"
    operating state "grey"



Requirements & Dependencies
===========================

    * Zenoss Versions Supported:  4.x
    * External Dependencies 

      * The zenpacklib package that this ZenPack is built on, requires PyYAML.  This is installed as 
      standard with Zenoss 5 and with Zenoss 4 with SP457.  To test whether it is installed, as
      the zenoss user, enter the python environment and import yaml:

      *  python
      *  import yaml
      *  yaml
      *   
      *  <module 'yaml' from '/opt/zenoss/lib/python2.7/site-packages/PyYAML-3.11-py2.7-linux-x86_64.egg/yaml/__init__.py'>

      If pyYAML is not installed, install it, as the zenoss user, with:

        easy_install PyYAML

      and then rerun the test above. You may see warning messages referring to the absence of libyaml - you 
      appear to be able to ignore these.


      * The pyvmomi Python vSphere SDK is required. With Zenoss 4.2.5 it appears
        essential to get the older version 5.5.0 otherwise errors result trying to find elements of urllib.
        pyvmomi-5.5.0-py2.7.egg is now included in the zenpack's lib directory and lines are added to the zenpack's
        __init__.py so that the zenoss libdir has this file appended.  There is no need to separately install
        pyvmomi unless you wish to.

        Once the ZenPack is installed, you can test that pyvmomi is accessible with:
          * zendmd
          *  import pyVmomi
          *  pyVmomi
          *   
          * <module 'pyVmomi' from '/opt/zenoss/local/ZenPacks.community.VMwareESXiMonitorPython/ZenPacks/community/VMwareESXiMonitorPython/lib/pyvmomi-5.5.0-py2.7.egg/pyVmomi/__init__.py'>


        If you do wish to install pyvmomi independently:
          * From pypi (https://pypi.python.org/pypi/pyvmomi ) follow the "5.5.0" link to download the
            zip file.  Unzip the file. Change directory into the pyvmomi-5.5.0 directory.  Install with:

                python setup.py install

          * A copy of the pyvmomi-5.5.0.zip file is in the lib directory of the ZenPack.        
        
        To test that the SDK is installed use:
      *  python
      *  import pyVmomi
      *  pyVmomi
      *   
      *  <module 'pyVmomi' from '/opt/zenoss/lib/python2.7/site-packages/pyvmomi-5.5.0-py2.7.egg/pyVmomi/__init__.pyc'>


    * ZenPack Dependencies: PythonCollector >= 1.6
    * Installation Notes: Restart zenoss entirely after installation
    * Configuration: Remember to set the zVSphereUsername and zVSpherePassword properties for devices / device classes.



Download
========
Download the appropriate package for your Zenoss version from the list
below.

* Zenoss 4.0+ `Latest Package for Python 2.7`_

ZenPack installation
======================

This ZenPack can be installed from the .egg file using either the GUI or the
zenpack command line. To install in development mode, from github - 
https://github.com/jcurry/ZenPacks.community.VMwareESXiMonitorPython  use the "Download ZIP" button
(on the right) to download a tgz file and unpack it to a local directory, say,
$ZENHOME/local.  Install from $ZENHOME/local with:

zenpack --link --install ZenPacks.community.VMwareESXiMonitorPython

Restart zenoss after installation.

Note that when removing this ZenPack you get the following error message:

    WARNING:zen.zenpacklib:Unable to remove DeviceClass Server/VMware/ESXi (not found)

This message appears to be benign and the /Server/VMware/ESXi IS removed.


Device Support
==============

The ZenPack has only been tested so far with Zenoss 4.2.5 with SUP 203 and SUP 457.


Upgrading from ZenPacks.community.VMwareESXiMonitor to this ZenPack ( ZenPacks.community.VMwareESXiMonitorPython )
=================================================================================================================

The upgrade should first be tested in a development environment.

Existing devices will be moved to a temporary device class.  
NOTE: Any existing local templates created for ESXi devices or their components WILL BE LOST.


* Backup the entire system
* Perform a zenbackup
* Move all devices under existing /Server/VMware/ESXi device class to a temporary device class.  /Ping   may be 
  appropriate if it currently has no devices in it.  Or create a new subclass under /Ping.
* Remove the old ZenPack
   * zenpack --remove ZenPacks.community.VMwareESXiMonitor  
* Completely restart Zenoss
* Ensure the PythonCollector ZenPack is at at least version 1.6  
* Check whether PyYAML is installed.  If not, install it.  See notes above.
* Install pyvmomi if required as an independent package; not actually necessary for the ZenPack to work - see notes above.
* Install new ZenPack
* Completely restart Zenoss
* Set zVSphereUsername / zVSpherePassword in device / device classes  
* Move initial test device back from /Ping to new /Server/VMware/ESXi
* Model this device and check components are correct
* Check that performance data is appearing in the correct directories and that graphs are correct.  

Change History
==============
* 3.0.0
   * Initial Release - version chosen as major version update from original VMwareESXiMonitor ZenPack
* 3.0.1
   * With Matthias improvements to datasource, /VMware Reports included in objects.xml, status renderer corrected,
     performanceSource and instance attributes of datasource removed, modelers moved from cmd subdirectory to python
     subdirectory, esxiHostName attribute removed from ESXiHost device object.
* 3.0.2
   * Various tidying up of datasource. Include pyvmomi-5.5.0-py2.7.egg in lib directory and __init__.py modified
     so libdir includes these pyvmomi libraries.
* 3.0.3
   * The operating status of all physical network interfaces is now being monitored.


Screenshots
===========

See the screenshots directory.


.. External References Below. Nothing Below This Line Should Be Rendered

.. _Latest Package for Python 2.7: https://github.com/jcurry/ZenPacks.community.VMwareESXiMonitorPython/blob/master/dist/ZenPacks.community.VMwareESXiMonitorPython-3.0.3-py2.7.egg?raw=true


Acknowledgements
================

This ZenPack is an update to the excellent ZenPack developed by Eric Enns and
Matthias Kittl.



