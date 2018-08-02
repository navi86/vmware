#!/usr/bin/env python

import argparse
from pyvim import connect
from pyvim.task import WaitForTask
import ssl
import time


import ssl
import requests
from vmware.vapi.vsphere.client import create_vsphere_client
from com.vmware.vcenter_client import VM, Folder

class ConnectTovCenter:
    def __init__(self, server, user, password, ssl_context):
        self.connect = connect.SmartConnect(host=server, user=user, pwd=password,
                                  sslContext=ssl_context)
        #data_center = si.content.rootFolder.childEntity[0]


from com.vmware.vcenter_client import VM

'''
def get_vms(stub_config, folders):
    #Return identifiers of a list of vms
    vm_svc = VM(stub_config)
    #vms = vm_svc.list(VM.FilterSpec(names=vm_names))
    vms = vm_svc.list(VM.FilterSpec(folders=folders))

    if len(vms) == 0:
        print('No vm found')
        return None

    #print("Found VMs '{}' ({})".format(vm_names, vms))
    return vms
'''
def get_vms(stub_config, folders):
    session = requests.session()
    session.verify = False
    client = create_vsphere_client(server='xxxxx',
                                   username='xxxxxx',
                                   password='xxxxxx',
                                   session=session)

    folder_filter = Folder.FilterSpec(names=set(['vm']))
    folder_id = client.vcenter.Folder.list(folder_filter)[0].folder
    vm_filter = VM.FilterSpec(folders=set([folder_id]))
    client.vcenter.VM.list(vm_filter)

def get_snapshots_by_name_recursively(snapshots, snapname):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.name == snapname:
            snap_obj.append(snapshot)
        else:
            snap_obj = snap_obj + get_snapshots_by_name_recursively(
                                    snapshot.childSnapshotList, snapname)
    return snap_obj

def get_vms(connection, list_students):
    """
    :param connection: connection to vCneter
    :param list_students: list of students which VM need to get
    :return: list of vms objects
    """
    data_center = connection.connect.content.rootFolder.childEntity[0]

    # list_vms = []
    list_vms = []

    level1 = data_center.vmFolder.childEntity

    for obj1 in level1:
        if obj1._wsdlName == 'Folder' and obj1.name == 'c3labs infrastructure':
            level2 = obj1.childEntity
            for obj2 in level2:
                if obj2.name in list_students:
                    level3 = obj2.childEntity
                    for obj3 in level3:
                        if obj3._wsdlName == 'VirtualMachine':
                            #list_vms[obj3.name] = obj3
                            list_vms.append(obj3)
    return list_vms

def RevertSnapshot(list_vms):
    """
    :param list_students: dict of students which need revert to golden state
    :return: dict of vms with key:ID and value:VM name
    """
    list_vms_reverted = []
    list_vms_not_reverted = []
    snapshot_name = 'golden_state'
    operation = 'revert'

    #for key, vm in list_vms.items():
    for vm in list_vms:
        snap_obj = get_snapshots_by_name_recursively(vm.snapshot.rootSnapshotList, snapshot_name)
        if len(snap_obj) == 1:
            snap_obj = snap_obj[0].snapshot
            if operation == 'revert':
                print("Reverting to snapshot %s" % snapshot_name)
                WaitForTask(snap_obj.RevertToSnapshot_Task())
                list_vms_reverted.append(vm.name)
            else:
                print("Operation  {} is not exist. Perhaps operation may not be printed correctly".format(operation))
        else:
            print("No snapshots found with name: %s on VM: %s" % (snapshot_name, vm.name))
            list_vms_not_reverted.append(vm.name)


    return list_vms_reverted, list_vms_not_reverted


def PowerOnVMs(list_vms):
    """
    :param list_students: list VM which should be PowerOn
    :return: list of vms which were powerOn and which had been PowerOn.
    """
    list_vms_powerOn = []
    list_vms_PowerOn_already = []
    for vm in list_vms:
        if (vm.summary.runtime.powerState == 'poweredOff'):
            print('Need to powerOn VM {}'.format(vm.name))
            vm.PowerOn()
            list_vms_powerOn.append(vm.name)
        else:
            list_vms_PowerOn_already.append(vm.name)


    return list_vms_powerOn, list_vms_PowerOn_already

def check_status(vm, time_, state):
    time.sleep(5)
    timer = 5
    result = ''
    while (vm.summary.runtime.powerState != state and timer < time_):
        time.sleep(5)
        timer += 5
    if (vm.summary.runtime.powerState != state and state == 'poweredOn'):
        result = 'error while powering VM {}'.format(vm.name)
    elif (vm.summary.runtime.powerState != state and state == 'poweredOff'):
        vm.PowerOff()
        result = 'error while powering VM {}'.format(vm.name)
    else:
        result = 'success'
    return result

def PowerOffVMs(list_vms):
    """
    :param list_students: list VM which should be PowerOff
    :return: list of vms which were powerOff
    """
    list_vms_powerOff = []
    list_vms_powerOff_already = []
    errors = []
    required_state = 'poweredOff'

    for vm in list_vms:
        if (vm.summary.runtime.powerState == 'poweredOn'):
            print('Need to powerOff VM {}'.format(vm.name))
            try:
                if (vm.summary.guest.toolsStatus == 'toolsOk'):
                    vm.ShutdownGuest()
                else:
                    vm.PowerOff()
                status = check_status(vm, 300, required_state)
                if status == 'success':
                    list_vms_powerOff.append(vm.name)
                else:
                    print('Something went wrong')
                    raise ValueError("Can't change VM state to {}".format(required_state))
            except Exception as e:
                errors.append(e.msg)
        else:
            list_vms_powerOff_already.append(vm.name)

    return list_vms_powerOff, list_vms_powerOff_already

def main():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_context.verify_mode = ssl.CERT_NONE
    vCenter = ConnectTovCenter(server=args.server, user=args.username, password=args.password, ssl_context=ssl_context)

    #list_students = ['Student01', 'Student10', 'Student16']
    #list_students = ['Student01']

    print(args.list_students)
################################
    session = requests.session()
    session.verify = False
    client = create_vsphere_client(server=args.server,
                                   username=args.username,
                                   password=args.password,
                                   session=session)

    folder_filter = Folder.FilterSpec(names=set(['vm']))
    folder_id = client.vcenter.Folder.list(folder_filter)[0].folder
    vm_filter = VM.FilterSpec(folders=set([folder_id]))
    client.vcenter.VM.list(vm_filter)
################################

    # Get list VMs
    # VM is looking in the folder c3labs infrastructure
    #list_vms = get_vms(connection=vCenter, list_students=list_students)
    list_vms = get_vms(connection=vCenter, list_students=args.list_students)
    print(list_vms)

    # PowerOff VMs
    list_vms_powerOff, list_vms_powerOff_already = PowerOffVMs(list_vms=list_vms)

    # Revert
    #list_vms_reverted, list_vms_notreverted = RevertSnapshot(list_vms=list_vms)

    # PowerOn VMs
    #list_vms_powerOn, list_vms_alreadyPowerOn = PowerOnVMs(list_vms=list_vms)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-s', dest='server', default='10.20.10.13', type=str, help='server address')
    parser.add_argument('-u', dest='username', type=str, help='username to connect vCenter', default='administrator@vsphere.local')
    parser.add_argument('-p', dest='password', type=str, help='password to connect vCenter', default='vmware_password')
    parser.add_argument('-students', dest='list_students', nargs='+', type=str, help='list of students', default = [])
    #parser.add_argument('-skipssl', dest='skipverification', type=bool, help='skip ssl verification', default=True)
    args = parser.parse_args()

    main()



