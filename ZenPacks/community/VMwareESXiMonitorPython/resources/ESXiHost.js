/*
* Customizations to ESXiHost Overview Page
*/
Ext.onReady(function() {
    var DEVICE_SNMP_ID = 'deviceoverviewpanel_snmpsummary';
    Ext.ComponentMgr.onAvailable(DEVICE_SNMP_ID, function() {
    var snmp = Ext.getCmp(DEVICE_SNMP_ID);
    snmp.removeField('snmpSysName');
    snmp.removeField('snmpLocation');
    snmp.removeField('snmpContact');
    snmp.removeField('snmpDescr');
    snmp.removeField('snmpCommunity');
    snmp.removeField('snmpVersion');
    snmp.addField({
        xtype: 'displayfield',
        id: 'cpu-mhz-displayfield',
        name: 'cpuMhz',
        fieldLabel: _t('CPU MHz')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'cpu-model-displayfield',
        name: 'cpuModel',
        fieldLabel: _t('Processor Type')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'num-cpu-cores-displayfield',
        name: 'numCpuCores',
        fieldLabel: _t('CPU Cores')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'num-cpu-pkgs-displayfield',
        name: 'numCpuPkgs',
        fieldLabel: _t('Processor Sockets')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'num-cpu-cores-per-pkgs-displayfield',
        name: 'numCpuCoresPerPkgs',
        fieldLabel: _t('Cores per Socket')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'num-cpu-threads-displayfield',
        name: 'numCpuThreads',
        fieldLabel: _t('Logical Processors')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'num-nics-displayfield',
        name: 'numNics',
        fieldLabel: _t('Number of NICs')
    });
    snmp.addField({
        xtype: 'displayfield',
        id: 'vmotion-state-displayfield',
        name: 'vmotionState',
        fieldLabel: _t('vMotion Enabled')
    });
    });
});

Ext.apply(Zenoss.render, {
    used_free_space: function(n) {
        if (n<0) {
            return _t('Unknown');
        } else {
            return Zenoss.render.bytesString(n);
        }
    },
    usedPercent: function(n) {
        if (n=='Unknown' || n<0) {
            return _t('Unknown');
        } else {
            return n + '%';
        }
    },
    adminStatus: function(n) {
        var status = parseInt(n),
            tpl = new Ext.Template(
                '<img border="0" src="img/{color}_dot.png"',
                'style="vertical-align:middle"/>'
            ),
            result = '';
        tpl.compile();
        switch (status) {
            case 1:
                result += tpl.apply({color:'green'});
                break; 
            case 2:
                result += tpl.apply({color:'red'});
                break; 
            case 3:
                result += tpl.apply({color:'orange'});
                break; 
            default:
                result += tpl.apply({color:'blue'});
        }
        return result;
    },
    operStatus: function(n) {
        var status = parseInt(n),
            tpl = new Ext.Template(
                '<img border="0" src="img/{color}_dot.png"',
                'style="vertical-align:middle"/>'
            ),
            result = '';
        tpl.compile();
        switch (status) {
            case 0:
                result += tpl.apply({color:'grey'});
                break;
            case 1:
                result += tpl.apply({color:'green'});
                break;
            case 2:
                result += tpl.apply({color:'red'});
                break;
            case 3:
                result += tpl.apply({color:'yellow'});
                break;
            case 4:
                result += tpl.apply({color:'grey'});
                break;
            default:
                result += tpl.apply({color:'blue'});
        }
        return result;
    },
});
