import sys,os,time,json,re
from typing import Dict

#import modules for test
# insidePath: For NDA
sys.path.append("insidePath\Modules\BIOS")
sys.path.append("insidePath\Modules\BMC\Basic")
sys.path.append("insidePath\Modules\BMC\LogCollection")
sys.path.append("insidePath\Modules\general")
sys.path.append("insidePath\Modules\BMC\Power")
sys.path.append("insidePath\Modules\BMC\FWupdate")

#print("appended")
import basicCheck,testCaseOutputFormat
import clearSELLog,getSDR,getBMCLog

#getting parameter from Jenkins
BMC_ip=os.getenv("BMC_ip")
BMC_user=os.getenv("BMC_user")
BMC_pwd=os.getenv("BMC_pw")
ciphersuite=os.getenv("ciphersuite")
Machine_type=os.getenv("Machine_type")
Dimm_number=os.getenv("Dimm_number")
Drive_number=os.getenv("Drive_number")
specPath = r'insidePath\RubypassSpec.txt'

ipmiDict={}
ipmiDict['bmcUser'] = f' -U {BMC_user}'
ipmiDict['bmcPwd'] = f' -P {BMC_pwd}'
ipmiDict['bmcIP'] = f' -H {BMC_ip}'    
ipmiDict['command'] = f' -C {ciphersuite}'


def comareSensorSpec(sensorInfo:str,specInfo:str,sensorType:str) -> bool:

    # This function will compare snesor and spec is consistent or not
    # If they are same return True else False

    # Argument
    # sensorInfo: Server's Sensor info (get from snesor list) 
    # specInfo: Spec's Snesor info (get from spec pdf)
    # kwargs: key -> sensor type
        
    keepWord = ['.','-']
    # sensorType = {'degrees c':'0x01','volts':'0x02','amps':'0x03','rpm':'0x04','watts':'0x0B'} #Record the machine code of sersor type

    if 'N/A' in specInfo:
        specInfo = 'na'
    else:
        # join numeric and keywords (".","-")
        specInfo = ''.join([specInfo[i] for i in range(len(specInfo)) if specInfo[i].isnumeric() == True or specInfo[i] in keepWord])
    
    # return True if sensorInfo == specInfo else False
    if sensorInfo == specInfo:
        return True
    else: 
        # if (sensorInfor == na and specInfo ==na) then will retrun Trun else Fasle
        if 'na' in sensorInfo or 'na' in specInfo:
            return False # Return False
        elif abs(float(sensorInfo)-float(specInfo)) <= 0.1: 
            return True
        elif '0x04' == sensorType and abs(float(sensorInfo)-float(specInfo))%7==0:
            return True
        else:
            return False

if __name__ == '__main__':

    #Basic check: BMC IP, OS IP, BMC account/password
    #make sure test environment is ready for automation
    testCaseOutputFormat.basicCheckOutputHead()
    #Check if OS IP is available
    if 0 == basicCheck.checkBMC(BMC_ip):
        print(f"[Log] Ping BMC Fail.")
        sys.exit(-1)
        
    if 0 == basicCheck.checkLoginBMC(ipmiDict):
        print(f"[Log] Login BMC Fail.")
        sys.exit(-1)

    if basicCheck.checkFile(specPath) ==0:
        print(f'[Log] Spec File Not exist')
    testCaseOutputFormat.basicCheckOutputFoot()
    
    testCaseOutputFormat.automationProducerOutputHead('Clear Sel Log')

    # Clear sel log
    if 1 == clearSELLog.clearSELLog(ipmiDict):
        print('[Pass] Clear sel log Pass.')
    else:
        print('[Fail] Clear sel log Fail.')
    testCaseOutputFormat.automationProducerOutputFoot()

    # Start test
    print(f"\n\n{time.ctime(time.time())}::BMC SDR Info Comfirm Start=============================================")

    # Paramter
    eixtOption = False
    testCaseId = 'C46600'
    testCaseTitle = 'SDR info'
    # Define the result 
    sdrOverflow = 'yes' if 'RubyPass' == Machine_type else 'no'

    # C46600 Step1 
    testCaseOutputFormat.testCaseOutputHead('1',testCaseId,testCaseTitle,'Run ipmitool sdr info')
    # Start to get SDR Info
    sdrInfo = getSDR.returnSDRVersionWithDict(ipmiDict)
    if 0 == sdrInfo or '' == sdrInfo:
        sdrinfoResult = 'Fail'
        testResultMessage = 'Get SDR info: Fail' 
    else:
        sdrinfoResult = 'Pass'
        testResultMessage = 'Get SDR info: Pass'
        
    testCaseOutputFormat.testCaseOutputFoot('1',sdrinfoResult,testResultMessage)

    # C46600 Step2
    if 'Pass' in sdrinfoResult:

        testCaseOutputFormat.testCaseOutputHead('2',testCaseId,testCaseTitle,'Check "SDR version" 0x51.')
        print(f'SDR Version : {sdrInfo["sdr version"]}')
        if '0x51' == sdrInfo['sdr version']:
            testResult = 'Pass'
            testResultMessage = '[Pass] Check SDR Version'
        else:
            testResult = 'Fail'
            testResultMessage = '[Fail] Check SDR Version'
            eixtOption = True
        testCaseOutputFormat.testCaseOutputFoot('2',testResult,testResultMessage)

        testCaseOutputFormat.testCaseOutputHead('3',testCaseId,testCaseTitle,'Check "SDR overflow" no. Note: RubyPass "SDR overflow" = Yes.')
        print(f'SDR Overflow : {sdrInfo["sdr overflow"]}')
        if sdrOverflow == sdrInfo['sdr overflow'].lower():
            testResult = 'Pass'
            testResultMessage = '"Check "SDR overflow"'
        else:
            testResult = 'Fail'
            testResultMessage = f'Check "SDR overflow", SDR Info in Machine: {sdrInfo["sdr overflow"]}'
            eixtOption = True
        testCaseOutputFormat.testCaseOutputFoot('3',testResult,testResultMessage)

    else:
        print('[Log] Get SDR Info Fail. Script will Pass Step 2, 3 ')
        print('[Log] Step2 : Check "SDR version" 0x51.')   
        print('[Log] Strp3 : Check "SDR overflow" no. Note: RubyPass "SDR overflow" = Yes.') 

    # Start test
    print(f"\n\n{time.ctime(time.time())}::BMC Sensor Spec Comfirm Start=============================================")

    # Argument
    testCaseId = 'C46601'
    testCaseTitle = 'Sensor default setting'

    testCaseOutputFormat.testCaseOutputHead('1',testCaseId,testCaseTitle,'1. Issue command: ipmitool sensor list.')
    sensorInfo = getBMCLog.returnBMCLog(ipmiDict,'sensor list')
    if '' == sensorInfo or 0 ==sensorInfo:
        testResult = 'Fail'
        testResultMessage = '[Fail] Issue command: ipmitool sensor list'
        if '' == sensorInfo:
            print('[Log] Sensor List is BLANK.')
        else:
            print('[Log] Failed to get Sensor List')
    else:
        testResult = 'Pass'
        testResultMessage = '[Pass] Issue command: ipmitool sensor list'
        print('[Log] Sensor List:')
        print(sensorInfo)
    testCaseOutputFormat.testCaseOutputFoot('2',testResult,testResultMessage)

    if testResult == 'Fail':
        print('[Fail] Cannot get sensor list to compare with spec.')
        sys.exit(-1)

    # Print Test Title
    testcaseStep = 'Compare the output with sensor spec, sensor count and name should be the same.\n'
    testcaseStep += 'Check the sensor type, threshold values are same as spec.\n'
    testcaseStep += 'Check each sensor in sensor spec by accessing the detail sensor record:\n'
    testcaseStep += '\bipmitool sensor get "CPU Power" (replace CPU Power to your sensor)\n'
    testcaseStep += 'Compare the detail data with sensor spec, should be consistent.\n'
    testCaseOutputFormat.testCaseOutputHead('2, 3, 4, 5',testCaseId,testCaseTitle,testcaseStep)

    # Arguments
    specStr = open(specPath,'r').read() # get one line string
    specDict = json.loads(specStr) # get dictionary 
    inSpect = list() #Load Sensor List name in Spec
    notInSpec = list() #Load Sensor List name not in Spec
    notInSensorGet = list()#Load Snesor Get Fail name
    comparedDict = dict()#Load Compared sensor data
    sensorDict = dict() #Load Sensor List's Data
    deviceCount = [0,0] #Dimm,Drive
    sensorType = {'degrees c':'0x01','volts':'0x02','amps':'0x03','rpm':'0x04','watts':'0x0B'} #Record the machine code of sersor type
    sensorTypeReverse = {'0x01':'degrees c','0x02':'volts','0x03':'amps','0x04':'rpm','0x0B':'watts'} # Reverse Record the machine code of sersor type
    sensorTypeForSensorGetCompare = {'0x01':'temperature','0x02':'voltage','0x03':'current','0x04':'fan','0x0B':'other'}
    sensorList = sensorInfo.split('\n')[:-1] #Sensor Info Split into List and take off index -1

    # Start to deal data and compare with spec json
    for i,row in enumerate(sensorList):

        # In cells Array:
        # value = [name to fit spec, sensor reading value, sensor reading type, ok or cr, na, LC, LNC, UNC, UC]
        # index = [0               , 1                   , 2                  , 3       , 4 , 5 , 6  , 7  , 8 ]
        
        # Extend Row into Cell
        cells = [cell.strip() for cell in row.split('|')]
        cells.append(cells[0]) #Orign name for sensor get
        cells[0] = cells[0].lower() #Lower Str for key compare
        # search sensor name in spec or not
        if cells[0] in specDict.keys():
            inSpect.append(cells[0]) #add Orign name  
        else:
        
            # If key Not in Spec, transfer key and compare it again
            if 'i' in cells[0][-2] and 'n' in cells[0][-1]:
                # te in string's last, like "psu1 current in"
                cells[0] = f'{cells[0][:-3]} input' #delete " in" and add " input"

            # If key Not in Spec, transfer key and compare it again
            if 'o' in cells[0][-3] and 'u' in cells[0][-2] and 't' in cells[0][-1]:
                # te in string's last, like "psu1 power out"
                cells[0] = f'{cells[0][:-4]} output' #delete " out" and add " output"

            # If key Not in Spec, transfer key and compare it again
            if 't' in cells[0][-2] and 'e' in cells[0][-1]:
                # te in string's last, like "cpu0 te"
                cells[0] = f'{cells[0][:-3]} temp' #delete " te" and add " temp"

            # If key Not in Spec, transfer key and compare it again
            if 'v' in cells[0][-2] and 'r' in cells[0][-1]:
                # vr in string's last, like "cpu0 vccd hv vr"
                cells[0] = f'{cells[0]} temp'
            
            # If key Not in Spec, transfer key and compare it again
            if 'e' in cells[0][-3] and 'h' in cells[0][-2] and 'v' in cells[0][-1]:
                # ehv in string's last, like "cup0 pvccfa ehv"
                cells[0] = f'{cells[0]} fivra'

            # search for keyword a1/a2/a3 
            aSituiation = re.search(' [a-z][0-9] ', cells[0])
            if None != aSituiation:
                # replace string to fit specJson's key
                oldStr = f'{cells[0][aSituiation.start(0)+1]}{cells[0][aSituiation.start(0)+2]}' #[a-z][0-9]
                newStr = f'{cells[0][aSituiation.start(0)+1]}#' #[a-z]# 
                cells[0] = cells[0].replace(oldStr,newStr)
            
            # search for keyword drive1/drive2/drive3/drive4/drive5/drive6
            bSituiation = re.search('drive[0-9] ', cells[0])
            if None !=bSituiation:
                # replace string to fit specJson's key
                oldStr = f'{bSituiation.group(0)}'#drive[0-9]
                newStr = 'drive# '
                cells[0] =cells[0].replace(oldStr,newStr)

            # Research sensor name  
            if cells[0] in specDict.keys():
                inSpect.append(cells[0])
            else:
                notInSpec.append(cells[0])

        # value = [name to fit spec, sensor reading value, sensor reading type, ok or cr, na, LC, LNC, UNC, UC, Orign Name]
        # index = [0               , 1                   , 2                  , 3       , 4 , 5 , 6  , 7  , 8 , 9         ]
        sensorDict[cells[0]] = cells

        # if server's sensor in spect then compare spec correct or not 
        if cells[0] in inSpect:

            print(f'[Log] Sensor Nmae: {cells[0]} in Spec.')
            print(f"[Log] Start to compare {cells[0]}'s Sensor List info with Spec info.")
            print('Note: If no error happend then no more log printed.')
            # comparedDict[snesor name] = {}
            sensorGetName = cells[-1]
            comparedDict[sensorGetName] = dict({'Sensor List':{'Sensor Type':'','LC':'','LNC':'','UNC':'','UC':''},'Sensor Get':dict()}) #key is orign name
            # specInfo's key -> Sensor Number, Entity ID, Entity Inst, Sensor Type, Event Reading Type, Reading Mask:Dict(key{LC,LNC,UNC,UC}), Redfish URI, Sensor Get
            specInfo = specDict.get(cells[0])

            # check Dimm and Drive
            if 'dimm' in sensorGetName.lower():
                deviceCount[0] += 1 

            if 'drive' in sensorGetName.lower():
                deviceCount[1] += 1

            # sensorType -> {machine code: real status}
            sensorTypeKey = cells[2].lower()
            SUTSensorType = sensorTypeKey if sensorType.get(sensorTypeKey) == None else sensorType.get(sensorTypeKey)

            # Reading Mask -> key: LC,LNC,UNC,UC
            if comareSensorSpec(cells[5],specInfo['Reading Mask']['LC'],SUTSensorType):
                comparedDict[sensorGetName]['Sensor List']['LC'] = 1
            else:
                comparedDict[sensorGetName]['Sensor List']['LC'] = 0
                # Diff Log
                print('[Log] -----------------------------------------------------------------')
                print(f"Sensor List Name : {{{sensorGetName}}}'s LC not consistant with Spec info.")
                print(f"  In Spec PDF    : {specInfo['Reading Mask']['LC']}")
                print(f"  In Sensor List : {cells[5]}")
                print('----------------------------------------------------------------- [Log]')
            print('[Log] Sensor List LC Compare finished.')

            # Reading Mask -> key: LC,LNC,UNC,UC
            if comareSensorSpec(cells[6],specInfo['Reading Mask']['LNC'],SUTSensorType):
                comparedDict[sensorGetName]['Sensor List']['LNC'] = 1
            else:
                comparedDict[sensorGetName]['Sensor List']['LNC'] = 0
                print('[Log] -----------------------------------------------------------------')
                print(f"Sensor List Name : {{{sensorGetName}}}'s LNC not consistant with Spec info.")
                print(f"  In Spec PDF    : {specInfo['Reading Mask']['LNC']}")
                print(f"  In Sensor List : {cells[6]}")
                print('----------------------------------------------------------------- [Log]')
            print('[Log] Sensor List LNC Compare finished.')

            # Reading Mask -> key: LC,LNC,UNC,UC
            if comareSensorSpec(cells[7],specInfo['Reading Mask']['UNC'],SUTSensorType):
                comparedDict[sensorGetName]['Sensor List']['UNC'] = 1
            else:
                comparedDict[sensorGetName]['Sensor List']['UNC'] = 0
                print('[Log] -----------------------------------------------------------------')
                print(f"Sensor List Name : {{{sensorGetName}}}'s UNC not consistant with Spec info.")
                print(f"  In Spec PDF    : {specInfo['Reading Mask']['UNC']}")
                print(f"  In Sensor List : {cells[7]}")
                print('----------------------------------------------------------------- [Log]')
            print('[Log] Sensor List UNC Compare finished.')

            # Reading Mask -> key: LC,LNC,UNC,UC
            if comareSensorSpec(cells[8],specInfo['Reading Mask']['UC'],SUTSensorType):
                comparedDict[sensorGetName]['Sensor List']['UC'] = 1
            else:
                comparedDict[sensorGetName]['Sensor List']['UC'] = 0
                print('[Log] -----------------------------------------------------------------')
                print(f"Sensor List Name : {{{sensorGetName}}}'s UC not consistant with Spec info.")
                print(f"  In Spec PDF    : {specInfo['Reading Mask']['UC']}")
                print(f"  In Sensor List : {cells[8]}")
                print('----------------------------------------------------------------- [Log]')
            print('[Log] Sensor List UC Compare finished.')

            # Start to check in Sensor Get
            print(f"[Log] Start to compare {cells[0]}'s Sensor Get info with Spec info.")
            print('Note: If no error happend then no more log printed.')
            sensorGetDict = getSDR.returnSensorGetDict(ipmiDict,cells[-1])
            if sensorGetDict==-1:
                sensorGetDict = getSDR.returnSensorGetDict(ipmiDict,f'{cells[-1]} ') #16bit
            elif sensorGetDict==0:
                time.sleep(15)
                print('[Log] Time Sleep 15 sencond to wait OS process over.')
                sensorGetDict = getSDR.returnSensorGetDict(ipmiDict,cells[-1])

            if sensorGetDict==-1:
                notInSensorGet.append(cells[-1])
                print('************************************************')
                print(f'[Fail] Cannot get "{cells[-1]}" snesor info.*')
                print('************************************************')
            elif sensorGetDict==0:
                notInSensorGet.append(cells[-1])
                print(f"[Fail] Please Check SUT's situation.")
            elif sensorGetDict!=-1 and sensorGetDict!=0:
                print(f'[Log] Sensor name :{cells[0]} can get sensor info')
                # Compare Entity ID 
                specEntityId = f"{str(int(specInfo.get('Entity ID'),16))}.{str(int(specInfo.get('Entity Inst'),16))}"  #Hexadecimal System -> int
                sensorGetEntityId = sensorGetDict.get('Entity ID')#str -> int
                if specEntityId == sensorGetEntityId:
                    comparedDict[sensorGetName]['Sensor Get']['Entity ID'] = 1
                else:
                    comparedDict[sensorGetName]['Sensor Get']['Entity ID'] = 0
                    print('[Log] -----------------------------------------------------------------')
                    print(f"Sensor Get Name : {{{sensorGetName}}}'s Entity ID not consistant with Spec info.")
                    print(f"  In Spec PDF   : {specEntityId}")
                    print(f"  In Sensor Get : {sensorGetEntityId}")
                    print('----------------------------------------------------------------- [Log]')
                print('[Log] Sensor Get Entity ID Compare finished.')

                # Compare Sensor Type
                sensorGetInfo = 'na' if sensorGetDict.get('Sensor Type (Threshold)') == None else sensorGetDict['Sensor Type (Threshold)']
                if sensorTypeForSensorGetCompare[specInfo.get('Sensor Type')] == sensorGetInfo:
                    comparedDict[sensorGetName]['Sensor Get']['Sensor Type'] = 1
                else:
                    comparedDict[sensorGetName]['Sensor Get']['Sensor Type'] = 0
                    print('[Log] -----------------------------------------------------------------')
                    print(f"Sensor Get Name : {{{sensorGetName}}}'s Sensor Type not consistant with Spec info.")
                    print(f"  In Spec PDF   : {sensorTypeForSensorGetCompare[specInfo.get('Sensor Type')]}")
                    print(f"  In Sensor Get : {sensorGetInfo}")
                    print('----------------------------------------------------------------- [Log]')
                print('[Log] Sensor Get Sensor Type Compare finished.')

                # Compare LC/LNC/UNC/UC
                sensorGetInfo = 'na' if sensorGetDict.get('Lower Critical') == None else sensorGetDict['Lower Critical']
                if comareSensorSpec(sensorGetInfo,specInfo['Reading Mask']['LC'],SUTSensorType):
                    comparedDict[sensorGetName]['Sensor Get']['LC'] = 1
                else:
                    comparedDict[sensorGetName]['Sensor Get']['LC'] = 0
                    print('[Log] -----------------------------------------------------------------')
                    print(f"Sensor Get Name : {{{sensorGetName}}}'s LC not consistant with Spec info.")
                    print(f"  In Spec PDF   : {specInfo['Reading Mask']['LC']}")
                    print(f"  In Sensor Get : {sensorGetInfo}")
                    print('----------------------------------------------------------------- [Log]')
                print('[Log] Sensor Get LC Compare finished.')

                # Compare LC/LNC/UNC/UC
                sensorGetInfo = 'na' if sensorGetDict.get('Lower Non-Critical') == None else sensorGetDict['Lower Non-Critical']
                if comareSensorSpec(sensorGetInfo,specInfo['Reading Mask']['LNC'],SUTSensorType):
                    comparedDict[sensorGetName]['Sensor Get']['LNC'] = 1
                else:
                    comparedDict[sensorGetName]['Sensor Get']['LNC'] = 0
                    print('[Log] -----------------------------------------------------------------')
                    print(f"Sensor Get Name : {{{sensorGetName}}}'s LNC not consistant with Spec info.")
                    print(f"  In Spec PDF   : {specInfo['Reading Mask']['LNC']}")
                    print(f"  In Sensor Get : {sensorGetInfo}")
                    print('----------------------------------------------------------------- [Log]')
                print('[Log] Sensor Get LNC Compare finished.')

                # Compare LC/LNC/UNC/UC
                sensorGetInfo = 'na' if None == sensorGetDict.get('Upper Non-Critical') else sensorGetDict['Upper Non-Critical']
                if comareSensorSpec(sensorGetInfo,specInfo['Reading Mask']['UNC'],SUTSensorType):
                    comparedDict[sensorGetName]['Sensor Get']['UNC'] = 1
                else:
                    comparedDict[sensorGetName]['Sensor Get']['UNC'] = 0
                    print('[Log] -----------------------------------------------------------------')
                    print(f"Sensor Get Name : {{{sensorGetName}}}'s UNC not consistant with Spec info.")
                    print(f"  In Spec PDF   : {specInfo['Reading Mask']['UNC']}")
                    print(f"  In Sensor Get : {sensorGetInfo}")
                    print('----------------------------------------------------------------- [Log]')
                print('[Log] Sensor Get UNC Compare finished.')

                # Compare LC/LNC/UNC/UC
                sensorGetInfo = 'na' if sensorGetDict.get('Upper Critical') == None else sensorGetDict['Upper Critical']
                if comareSensorSpec(sensorGetInfo,specInfo['Reading Mask']['UC'],SUTSensorType):
                    comparedDict[sensorGetName]['Sensor Get']['UC'] = 1
                else:
                    comparedDict[sensorGetName]['Sensor Get']['UC'] = 0
                    print('[Log] -----------------------------------------------------------------')
                    print(f"Sensor Get Name : {{{sensorGetName}}}'s UC not consistant with Spec info.")
                    print(f"  In Spec PDF   : {specInfo['Reading Mask']['UC']}")
                    print(f"  In Sensor Get : {sensorGetInfo}")
                    print('----------------------------------------------------------------- [Log]')
                print('[Log] Sensor Get UC Compare finished.')

    # Check Fail and gernerate testResultMessage
    testResultMessage = ''
    for namekey,nameValue in comparedDict.items():

        # Sensor Get Error Message
        FailMessage = [f' {namekey} Sensor Get {sensorGetKey} existed not consistant.\n' for sensorGetKey,sensorGetVal in nameValue['Sensor Get'].items() if sensorGetVal ==0]
        testResultMessage+= ''.join(FailMessage)

        # Sensor List Error Message
        FailMessage = [f' {namekey} Sensor List {sensorGetKey} existed not consistant.\n' for sensorGetKey,sensorGetVal in nameValue['Sensor List'].items() if sensorGetVal ==0]
        testResultMessage+= ''.join(FailMessage)

    if '\n' in testResultMessage:
        testResult = 'Fail'
        eixtOption = True
    else:
        testResult = 'Pass'

    testCaseOutputFormat.testCaseOutputFoot('2, 3, 4, 5',testResult,testResultMessage)
    
    # Generate Spec Not In Sensor List 
    testCaseOutputFormat.resultOutputHead()
    specNotInSensorList = [key for key in specDict.keys() if key not in inSpect]
    # Count those not in machine
    deviceNotInMachine = [specDict[name]["Sensor Get"] for name in specNotInSensorList]
    # Dimm
    Dimm_number = int(Dimm_number) if Dimm_number != None else 0
    if deviceCount[0] == Dimm_number:
        print('[Pass] Dimm Count in Sensor List same as Inputed')
    else:
        print('[Fail] Dimm Count in Sensor List not same as Inputed')
        eixtOption=True
    print(f'Dimm Count : {deviceCount[0]}')
    print(f'Dimm Number: {Dimm_number}')

    # Drive
    Drive_number = int(Drive_number) if Drive_number != None else 0
    if deviceCount[1] == Drive_number:
        print('[Pass] Drive Count in Sensor List same as Inputed')
    else:
        print('[Fail] Drive Count in Sensor List not same as Inputed')
        eixtOption=True

    # Result
    print(f'Drive Count : {deviceCount[1]}')
    print(f'Drive Number: {Drive_number}')
    print('')
    print(f'Sensor in ipmitool sensor list and Spec : {[sensorDict[name][-1] for name in inSpect ]}')
    print(f'Sensor in ipmitool sensor list but not in Spec : {[sensorDict[name][-1] for name in notInSpec]}')
    print(f'Sensor in Spec but not in ipmitool sensor list : {list(deviceNotInMachine)}') # deal in above line 
    print(f'Sensor in ipmitool sensor list but ipmitool sensor get Fail: {notInSensorGet}')
    testCaseOutputFormat.resultOutputFoot()

    if eixtOption == True:
        sys.exit(-1)
