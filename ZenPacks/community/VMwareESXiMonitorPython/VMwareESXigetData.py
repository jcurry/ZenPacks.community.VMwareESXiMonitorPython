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

__doc__ = """VMwareESXigetData utility

gathers ESXi element information.

"""

from pyVim.connect import SmartConnect, Disconnect
import atexit

import ssl
import sys

def getData(host, username, password, port, log, elementList):
    log.debug('In getData. host is %s, username is %s, password is %s, port is %s \n' % (host, username, password, port))
    addr = (host, port)
    log.debug('host is %s  port is %s  and addr is %s' % (host, port, addr))
    try:
        log.debug('ssl get_server_certificate gives: \n %s' % (ssl.get_server_certificate(addr)))
    except Exception as e:
        log.debug(' Exception is %s' % (e))
        t,o,tb = sys.exc_info()
        log.debug('In Exception: type is %s object is %s lineno is %s' % (t, o, tb.tb_lineno))

    serviceInstance = SmartConnect(host=host,
                                   user=username,
                                   pwd=password,
                                   port=port)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()
    element_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        elementList,
                                                        True)
    elements = [element for element in element_view.view]
    log.debug(' in getData - elements is %s \n' % (elements))
    element_view.Destroy()

    return elements
