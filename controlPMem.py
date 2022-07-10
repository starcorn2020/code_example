import sys,paramiko,time,json

#import modules for test
# insidePath: For NDA
sys.path.append("insidePath\Modules\BMC\Basic")
sys.path.append("insidePath\Modules\BMC\Power")
sys.path.append("insidePath\Modules\general")

import sshConnect,ipmiPowerAction,basicCheck,pingServer

def checkPmemMode(OS_ip,OS_user,OS_pwd):

    # Parameter:
    # OS_ip: Linux System SUT's IP for Login.
    # OS_user: Linux System SUT's Username for Login. 
    # OS_pwd: Linux System SUT's Password for Login.

    # This function will check Pmem Mode (Memory/Storage) and return mode (Memory/Storage)
    # If Check mode failed, return 0 

    result = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,'ipmctl show -memoryresources')
    if result ==0:
        print(f'[Failed] Failed to get ipmctl info.')
        return 0
    else:
        try:
            # pmemMode = 'unknown'
            # ssh_send_command return byte, convert it to string
            result = result.decode('utf-8')
            print('[Log] ipmctl show -memoryresources :')
            print(result)
            '''
            result:
            
            MemoryType   | DDR         | PMemModule   | Total
            ==========================================================
            Volatile     | 0.000 GiB   | 2024.000 GiB | 2024.000 GiB
            AppDirect    | -           | 0.000 GiB    | 0.000 GiB
            Cache        | 512.000 GiB | -            | 512.000 GiB
            Inaccessible | 0.000 GiB   | 5.874 GiB    | 5.874 GiB
            Physical     | 512.000 GiB | 2029.874 GiB | 2541.874 GiB
            '''
            # split Mem mode cap and Add mode cap
            MemModeStr = result.split('\n')[2].split('|')[2].split(' ')[1]
            AddModeStr = result.split('\n')[3].split('|')[2].split(' ')[1]
            # judge mode
            pmemMode = 'unknown'
            if float(AddModeStr)>0 and float(MemModeStr) ==0:
                pmemMode = 'Storage'
            elif float(AddModeStr)==0 and float(MemModeStr)>0:
                pmemMode = 'Memory'
            else:
                # for mix mode or change mode failed
                pmemMode = 'unknown'
            return pmemMode
        except Exception as e:
            print(f'{e}')
            return 0


def createNamespace(OS_ip,OS_user,OS_pwd,**kwargs):
    # Parameter:
    # OS_ip: Linux System SUT's IP for Login.
    # OS_user: Linux System SUT's Username for Login. 
    # OS_pwd: Linux System SUT's Password for Login.

    # This function will create Namespace under Storage Mode,
    # Sent command to change Pmem mode

    # Check region
    regionDev = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,'ndctl list -R')
    if regionDev ==0:
        print(f'[Failed] ndctl list -R.')
        return 0

    # byte -> string -> json
    regionDev = json.loads(regionDev.decode('utf-8'))
    # Sorted list [{},{}]
    regionDev = sorted(regionDev, key=lambda d: d['dev'])
    # Run each region
    for i in range(len(regionDev)):
        # Change Region to disk
        if 'mountOnly' not in kwargs:

            namespaceDev = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'ndctl create-namespace -m fsdax -r {regionDev[i]["dev"]}') # byte -> string
            if namespaceDev ==0:
                print(f'[Failed] "ndctl create-namespace -m fsdax -r {regionDev[i]["dev"]}" Failed.')
                return 0
            elif b'failed to create namespace: No space left on device' in namespaceDev:
                # 1. created
                print(f'[Log] {regionDev[i]["dev"]} : failed to create namespace: No space left on device')
                    
            diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,'lsblk')
            if diskcommand ==0:
                print(f'[Failed] "mkdir /mnt/pmem{i}" Failed.')
                return 0
            
            # mkdir /mnt/pmem*
            diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'mkdir /mnt/pmem{i}')
            if diskcommand ==0:
                print(f'[Failed] "mkdir /mnt/pmem{i}" Failed.')
                return 0

            # mkfs -t xfs -f /dev/pmem*
            # diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'mkfs -t xfs -f /dev/pmem{i}')
            diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'mkfs -t xfs -f /dev/pmem{i}')
            if diskcommand ==0:
                print(f'[Failed] "mkfs -t xfs -f /dev/pmem{i}" Failed.')
                return 0

            # mkfs.xfs -f -m reflink=0 /dev/pmem*
            diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'mkfs.xfs -f -m reflink=0 /dev/pmem{i}')
            if diskcommand ==0:
                print(f'[Failed] "mkfs.xfs -f -m reflink=0 /dev/pmem{i}" Failed.')
                return 0

            # mount -o dax /dev/pmem* /mnt/pmem*            
            diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'mount -o dax /dev/pmem{i} /mnt/pmem{i}')
            if diskcommand ==0:
                print(f'[Failed] "mount -o dax /dev/pmem{i} /mnt/pmem{i}" Failed.')
                return 0

        elif kwargs['mountOnly'] =='only':
            # mount -o dax /dev/pmem* /mnt/pmem*            
            diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'mount -o dax /dev/pmem{i} /mnt/pmem{i}')
            if diskcommand ==0:
                print(f'[Failed] "mount -o dax /dev/pmem{i} /mnt/pmem{i}" Failed.')
                return 0
        else:
            print(f"[Error] Wrong Option of input {kwargs['mountOnly']}")
            return 0

    if 'getInfo' in kwargs:
        namespasce = getNamespace(OS_ip,OS_user,OS_pwd)
        # check create namespace successful or not
        if namespasce ==0 or namespasce==-1:
            return 0 
        else:
            if len(namespasce)==len(regionDev):
                # Check mount status
                count = 0
                for key,value in namespasce.items():
                    if namespasce[key] =='':
                        print(f'{key} not mount successfully.')
                        count+=1
                # all file/dictionary are mount in system
                if count ==0:
                    # Check return value
                    if kwargs['getInfo'] =='fio':
                        fioInfo = ''
                        for key,value in namespasce.items():
                            fioInfo+=f'{key}:'
                        #fioInfo[-1] -> ':' 
                        return fioInfo[:-1]
                    elif kwargs['getInfo'] =='disk':
                        # diskInfo -> Dict
                        return namespasce
                    else:
                        # Successed but return option value is unknown
                        print(f'Error input value : {kwargs["getInfo"]}')
                        return 1
                else:
                    return 0
            else:
                print(f'[Failed] Create Namespace Failed.')
                return 0
    else:
        # Successed, no return value
        return 1

def deleteNamespace(OS_ip,OS_user,OS_pwd):
    # Parameter:
    # OS_ip: Linux System SUT's IP for Login.
    # OS_user: Linux System SUT's Username for Login. 
    # OS_pwd: Linux System SUT's Password for Login.

    # This function will delete Namespace under Storage Mode
    # and check it created successfully.

    # Check region 
    regionDev = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,'ndctl list')
    if regionDev ==0:
        print(f'[Failed] ndctl list.')
        return 0
    elif regionDev ==b'':
        # Check lsblk -> pmem namespace existed or not
        diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,'lsblk')
        if diskcommand ==0:
            print(f'[Failed] "rmdir /mnt/pmem{i}" Failed.')
            return 0
        elif b'pmem' not in diskcommand:
            print("No Pmem's namespace in disk list")
            return 1

    # byte -> string -> json
    regionDev = json.loads(regionDev.decode('utf-8'))
    regionDev = sorted(regionDev, key=lambda d: d['dev'])
    # Run each region
    for i in range(len(regionDev)):
        # umount /mnt/pmem*
        diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'umount /mnt/pmem{i}')
        if diskcommand ==0:
            print(f'[Failed] "umount /mnt/pmem{i}" Failed.')
            return 0
        # rmdir /mnt/pmem*
        diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'rmdir /mnt/pmem{i}')
        if diskcommand ==0:
            print(f'[Failed] "rmdir /mnt/pmem{i}" Failed.')
            return 0
        # ndctl disable-namespace [dev name]
        diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'ndctl disable-namespace {regionDev[i]["dev"]}')
        if diskcommand ==0:
            print(f'[Failed] "ndctl disable-namespace {regionDev[i]["dev"]}" Failed.')
            return 0
        # ndctl destroy-namespace [dev name]
        diskcommand = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,f'ndctl destroy-namespace {regionDev[i]["dev"]}')
        if diskcommand ==0:
            print(f'[Failed] "ndctl destroy-namespace {regionDev[i]["dev"]}" Failed.')
            return 0
            
    namespasce = getNamespace(OS_ip,OS_user,OS_pwd)
    if namespasce==0:
        print('[Log] Delete Pmem namespace and unmount disk successfully.')
        return 1
    else:
        print('[Failed] Delete namespace and region failed. Please delete those manually.')
        return 0

def getNamespace(OS_ip,OS_user,OS_pwd,**kwargs):
    
    # Parameter:
    # OS_ip: Linux System SUT's IP for Login.
    # OS_user: Linux System SUT's Username for Login. 
    # OS_pwd: Linux System SUT's Password for Login.
    # **kwargs : value = fio ,if no input will return dict

    # This function will get Namespace and return

    # Return singal:
    # 1 -> Success Get Pmem info
    # 0 -> Failed Get Pmem info
    # -1 -> Get Pmem's dev/pmem but no mnt/pmem/

    # Check region
    lsblkInfo = sshConnect.ssh_send_command(OS_ip,OS_user,OS_pwd,'lsblk')
    if lsblkInfo ==0:
        print(f'[Failed] lsblk')
        return 0

    diskInfo = dict()
    fioString = ''
    # Get Pmeme's disk info
    lsblkInfo = str(lsblkInfo,'utf-8')
    print('[Log] lsblk : ')
    print(f'{lsblkInfo}')
    lsblkList = lsblkInfo.split('\n')
    # print(lsblkList)
    for i,value in enumerate(lsblkList):
        if 'pmem' in lsblkList[i].lower():
            arr = lsblkList[i].split(' ')
            # arr[0] : pmem namespace's name 
            # arr[-1] : disk mount check
            if 'pmem' in arr[0] and '/mnt/pmem' in arr[-1]:
                diskInfo[f'/dev/{arr[0]}']=f'{arr[-1]}'
                fioString+=f'/dev/{arr[0]}:'
            elif 'pmem' in arr[0] and '/mnt/pmem' not in arr[-1]:
                print('[Log] Pmem in AD Mode but not mounted.')
                print(lsblkList[i])
                return -1
    # Check info 
    if len(diskInfo) ==0:
        print('[Log] No pmem namaspace in disk list.')
        return 0
    else:
        if 'valueFor' in kwargs:
            if kwargs['valueFor'] == 'fio':
                return fioString[:-1]
            else:
                return 1
        else:
            return diskInfo

def typePmemMode(OS_ip,OS_user,OS_pwd,ipmiDict,choiceMode,Machine_initial_time):
    # Parameter:
    # OS_ip: Linux System SUT's IP for Login.
    # OS_user: Linux System SUT's Username for Login. 
    # OS_pwd: Linux System SUT's Password for Login.
    # choiceMode: Storage/Memory.
    # Machine_initial_time: Ping time after power cycle

    # This function will type Pmem Mode (Memory), power cycle and check Pmem Mode

    # Return:
    # Success 1
    # Failed 0

    # Check SUT's Pmem Mode 
    pemmemode = checkPmemMode(OS_ip,OS_user,OS_pwd)
    # kwargs Key : value > 'PmemMode' : 'Memory' or 'Storage'
    if pemmemode == 'unknown':
        print(f"[Error] ipmctl show -a -region: {pemmemode}")
        return 0

    elif choiceMode == pemmemode:
        print(f'[Log] No need to type Pmem mode.')
        # 'Storage' mode return string for fio
        if pemmemode=='Storage':
            # No Pmem Mode need change.  
            fioString = getNamespace(OS_ip,OS_user,OS_pwd,valueFor='fio')   
            #  no namespcae in lsblk then create namespace
            if fioString ==0:
                fioString = createNamespace(OS_ip,OS_user,OS_pwd,getInfo='fio')
                # if create namespcae failed
                if fioString =='' or fioString==0:
                    print(f'[Failed] Pmem Moudle create Namespace under Storage Mode Failed.')
                    return 0
            elif fioString ==-1:
                # Namespace in lsblk and no mount successfully
                status = deleteNamespace(OS_ip,OS_user,OS_pwd)
                if status ==0:
                    # Delete namesapce failed
                    print('[Failed] Delete namesapce failed')
                    return 0
                elif status ==1:
                    # Delete namespace successfully
                    fioString = createNamespace(OS_ip,OS_user,OS_pwd,getInfo='fio')
                    # if create namespcae failed
                    if fioString =='' or fioString==0:
                        print(f'[Failed] Pmem Moudle create Namespace under Storage Mode Failed.')
                        return 0
            return fioString
        else:
            return 1
    else:

        print(f'[Log] Type Pmem mode from {pemmemode} to {choiceMode}.')
        if choiceMode == 'Memory':
            # pemem command to change mode
            pmemcommand = 'ipmctl create -f -goal MemoryMode=100\n'
            # before change mode from storage to memory, comfirm no namespace in disk list
            if pemmemode == 'Storage':
                # Check namespace is not existed
                status = deleteNamespace(OS_ip,OS_user,OS_pwd)
                if status ==0:
                    # Delete namesapce failed
                    print('[Failed] Delete namesapce failed')
                    print('[Log] Try to delete namespace again.')
                    status = deleteNamespace(OS_ip,OS_user,OS_pwd)
                    if status ==0:
                        return 0
                elif status ==1:
                    # Delete namespace successfully
                    pass
            elif pemmemode == 'Memory':
                # No thing to do
                pass                
        elif choiceMode == 'Storage':
            # pemem command to change mode
            pmemcommand = 'ipmctl create -f -goal persistentmemorytype=appdirect\n'
        else:
            # remind word
            print(f'[Error] Please input correct option, not {choiceMode}.')
            return 0
        
        # Sent command to change Pmem mode
        try:
            
            print(f'[Log] Type Pmem mode ........... {time.ctime(time.time())}')
            tran = paramiko.Transport(sock=(OS_ip,22))
            tran.connect(username=OS_user,password=OS_pwd)
            channel = tran.open_session()
            channel.get_pty()
            channel.invoke_shell()
            channel.send(pmemcommand)
            # Timer to record time 
            tiktok = time.time() + 300
            # exit for time record. if failed (time out) ,exit = 0, successed, exit = 1.
            exit = 0            
            while time.time() < tiktok:
                time.sleep(1.5)
                res = channel.recv(65535).decode('utf8')
                # if res and pmemcommand not in res:
                #     sys.stdout.write(res.strip('\n'))
                if res.endswith('# ') or res.endswith('$ ') or res.endswith(': '):
                    exit=1
                    
                    break
                   
        except paramiko.SSHException:
            print('[Failed] failed to connect to SSH')
            return 0
        except Exception as e:
            print(f'{e}')
            return 0

        # Check change mode success or fail
        if exit == 0:
            # if failed return 0
            print('[Error] Send ipmictl command time out...')
            return 0

        print(f'[Log] Power Cycle after type Pmem mode ........... {time.ctime(time.time())}')
        # if successs, power cycle and memry mode return 1, storage mode change userspace and region
        powerstatus = ipmiPowerAction.powerAction('cycle',ipmiDict)
        if powerstatus == 0:
            # power cycle failed
            return 0
        # Check OS Usable
        # After type Pmem Moudle, SUT Boot boot will spent more time
        # No need to record pingtime  
        pingTimee = pingServer.pingTime('OS',OS_ip,int(Machine_initial_time))
        if pingTimee == -1:
            print(f'[Failed] Try to ping OS over {Machine_initial_time} mins') 
            return 0

        # power cycle successed
        # Check pmem mode type successed or not
        pemmemode = checkPmemMode(OS_ip,OS_user,OS_pwd)
        if choiceMode != pemmemode:
            # If not 
            print('[Failed] Change Pmem Mode Failed.')
            return 0
        # If successed
        print('[Log] Change Pmem Mode Successed.')
        if choiceMode == 'Memory':
            return 1
        elif choiceMode =='Storage':
            # Using ndctl to change mode            
            fioString = createNamespace(OS_ip,OS_user,OS_pwd,getInfo='fio')
            if fioString ==0:
                print(f'[Failed] Create Namespace Failed.')
                return 0
            elif fioString == -1:
                print(f'[Failed] Mount Namespace Failed.')
                return -1

            # Check device info
            checkStatus = basicCheck.checkHardDrive(OS_ip,OS_user,OS_pwd,fioString)
            if checkStatus == 1:
                print(f'[Success] Create Namespace Successed.')
                # return fio_string for fio test
                return fioString
            elif checkStatus == 0:
                print(f'[Failed] Create Namespace Failed.')
                return 0
