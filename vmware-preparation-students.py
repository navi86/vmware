#!/usr/bin/env python

import argparse
from pyvim import connect
from pyvim.task import WaitForTask
from pyVmomi import vim
import ssl


import re
import ssl
import time
import requests
from vmware.vapi.vsphere.client import create_vsphere_client
from com.vmware.vcenter_client import VM, Folder

class ConnectTovCenter:
    def __init__(self, server, user, password, ssl_context):
        self.connect = connect.SmartConnect(host=server, user=user, pwd=password,
                                  sslContext=ssl_context)
        #data_center = si.content.rootFolder.childEntity[0]

class MyException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        #self.message = message


from com.vmware.vcenter_client import VM

'''
def get_vms(stub_config, list_folders):
#    session = requests.session()
#    session.verify = False
#    client = create_vsphere_client(server='xxxxx',
#                                   username='xxxxxx',
#                                   password='xxxxxx',
#                                   session=session)

    list_vms=[]
    for folder_name in list_folders:
        folder_filter = Folder.FilterSpec(names=set([folder_name]))
        folder_id = stub_config.vcenter.Folder.list(folder_filter)[0].folder
        vm_filter = VM.FilterSpec(folders=set([folder_id]))
        list_vms.append(stub_config.vcenter.VM.list(vm_filter))
    print('nothing')
    return  list_vms
'''
def get_snapshots_by_name_recursively(snapshots, snapname):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.name == snapname:
            snap_obj.append(snapshot)
        else:
            snap_obj = snap_obj + get_snapshots_by_name_recursively(
                                    snapshot.childSnapshotList, snapname)
    return snap_obj


def get_vms(connection, list_students, c3folder):
    """
    :param connection: connection to vCneter
    :param list_students: list of students which VM need to get
    :param c3folder: folder  where C3 vms are located
    :return: list of vms objects
    """
    '''
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
        
    '''
    content = connection.connect.RetrieveContent()
    container = content.rootFolder  # starting point to look into
    viewType = [vim.Folder]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(
        container, viewType, recursive)

    list_vms = []
    folders_obj = containerView.view
    list_folders = []
    list_students_lower = [student.lower() for student in list_students]
    #get folders where VMs are located
    for folder_obj in folders_obj:
        if (folder_obj.name).lower() in list_students_lower or (folder_obj.name).lower() == c3folder.lower():
            list_folders.append(folder_obj)
    # Check if there are two folders with the same name
    if len([item.name.lower() for item in list_folders]) == len(set([item.name.lower() for item in list_folders])):
        # get list VMs
        for folder_id in list_folders:
            vms = folder_id.childEntity
            for vm in vms:
                # append object to the list of it's a vm from required students
                if isinstance(vm, (vim.VirtualMachine)) and \
                    (vm.name[-2:] in [student[-2:] for student in list_students] or \
                     vm.name.split('-')[0] in list_students_lower):
                    list_vms.append(vm)
    else:
        # Raise an error if there more than one folder of student
        raise MyException('There is a dubplicate name of folder')
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

    mask_student = 'Student'
    list_students = []
    if args.list_students[0] == 'all':
        for i in range(1, 17):
            if i < 10:
                list_students.append(mask_student + '0' + str(i))
            else:
                list_students.append(mask_student + str(i))
    else:
        list_students = args.list_students
    #list_students = ['Student01']
    if not list_students:
        raise MyException('Students were not selected')
################################
    #session = requests.session()
    #session.verify = False
    #client = create_vsphere_client(server=args.server,
    #                               username=args.username,
    #                               password=args.password,
    #                               session=session)
    # Get list VMs
    # VM is looking in the folder c3labs infrastructure
    # list_vms = get_vms(connection=vCenter, list_students=list_students)
    #list_vms = get_vms(client,list_students)

#    folder_filter = Folder.FilterSpec(names=set(['c3labs infrastructure']))
#    folder_id = client.vcenter.Folder.list(folder_filter)[0].folder
#    vm_filter = VM.FilterSpec(folders=set([folder_id]))
#    client.vcenter.VM.list(vm_filter)
################################

    # Get list VMs
    # VM is looking in the folder c3labs infrastructure
    list_vms = get_vms(connection=vCenter, list_students=list_students, c3folder='c3labs c3')
    print(sorted([vm.name for vm in list_vms]))
    if args.revert:
        print('Revert procedure has started')
        # PowerOff VMs
        list_vms_powerOff, list_vms_powerOff_already = PowerOffVMs(list_vms=list_vms)

        # Revert
        #list_vms_reverted, list_vms_notreverted = RevertSnapshot(list_vms=list_vms)
    if args.powerOne:
        print('PowerOne procedure has started')
        # PowerOn VMs
        list_vms_powerOn, list_vms_alreadyPowerOn = PowerOnVMs(list_vms=list_vms)
        print('vms were already PowerOne:', list_vms_alreadyPowerOn)
        print('vms were PowerOne:', list_vms_powerOn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some taks.')
    parser.add_argument('-s', '--server', dest='server', default='10.20.10.13', type=str, help='server address')
    parser.add_argument('-u', '--username', dest='username', type=str, help='username to connect vCenter',
                        default='administrator@vsphere.local')
    parser.add_argument('-p', '--password', dest='password', type=str, help='password to connect vCenter',
                        default='password')
    parser.add_argument('--revert', dest='revert', action='store_true', help='Execute revert Students.')
    parser.add_argument('--powerOne', dest='powerOne', action='store_true', help='Execute powering vms. Boolean value.')
    parser.add_argument('--students', dest='list_students', nargs='+', type=str,
                        help='list of students. For choosing all students choose "all"', default = [])
    #parser.add_argument('-skipssl', dest='skipverification', type=bool, help='skip ssl verification', default=True)
    args = parser.parse_args()

    main()



