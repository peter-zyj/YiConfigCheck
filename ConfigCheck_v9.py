#!/usr/local/bin/python3
import os,sys,re,shutil
import pexpect,traceback
import time,argparse,datetime
from multiprocessing import Process, Queue, Manager,Array, Lock


########SSH logon stuff############
default_passwd = "rootroot"
prompt_firstlogin = "Are you sure you want to continue connecting \(yes/no\)\?"
prompt_passwd = "root@.*'s password:"
prompt_logined = "\[root@.*\]#"
prompt_percentage = ".*100%.*"
prompt_tested = "\[root@.*\]#"
prompt_init = "continue ? (yes/no) [y]:"


def Standard_Reply_SCP(ssh,IP):
    try:
        result = "Not Set"
        result = ssh.expect([prompt_firstlogin, prompt_passwd, prompt_logined, pexpect.TIMEOUT, prompt_percentage],timeout=10)
        #ssh.logfile = sys.stdout   
        ssh.logfile = None

        if result == 0:
            ssh.sendline('yes')
            ssh.expect(prompt_passwd)
            ssh.sendline(default_passwd)
            ssh.expect(prompt_percentage,timeout=10)
        elif result == 1:
            ssh.sendline(default_passwd)
            ssh.expect(prompt_percentage,timeout=10)
        elif result == 2:
            pass
        elif result == 3:
            print ("ssh to %s timeout" %IP)
            raise
        elif result == 4:
            pass
        return ssh,result
    except:
        if result == 3:
            print ("[TIMEOUT]%s for the file Transfer" % (IP))
        else:
            e = sys.exc_info()[0]
            print ("<p>Error: %s</p>" % e)
            print (traceback.print_exc())
            print ("result is ",result)
        return ssh,None


def Standard_Reply_SSHCmmand(IP,cmd,prompt=prompt_logined):
    try:
        result = "Not Set"
        ssh = pexpect.spawn('ssh root@%s' % IP)
        result = ssh.expect([prompt_firstlogin, prompt_passwd, prompt, prompt_init, pexpect.TIMEOUT],timeout=10)

        ssh.logfile = None
        if result == 0:
            ssh.sendline('yes')
            ssh.expect(prompt_passwd)
            ssh.sendline(default_passwd)
            ssh.expect(prompt)
            ssh.sendline(cmd)
            ssh.expect(prompt)
        elif result == 1:
            ssh.sendline(default_passwd)
            ssh.expect(prompt)
            ssh.sendline(cmd)
            ssh.expect(prompt)            
        elif result == 2:
            pass
        elif result == 3:
            ssh.sendline('n')
            ssh.expect(prompt)
            ssh.sendline(cmd)
            ssh.expect(prompt)           
        elif result == 4:
            print ("Connection::"+"ssh to %s timeout" %IP)
            raise
        return ssh,ssh.before[:-1]
    except:
        print ("result is ",result)
        if result != 4:
            print ('SSHClient::Mismatch BTW default expect or unexpected things happen!')
        debug = "Connection::"+str(ssh.before[:-1])
        print (debug)
        return debug,None

def categoryFilter(ip,serverCat):
    cmd_cos = "rpm -qa | grep -e '^cserver' | awk '{printf\"RESULT:\";printf$0;print\":END\"}'"
    cmd_cmc = "rpm -qa | grep -e '^cmc' | awk '{printf\"RESULT:\";printf$0;print\":END\"}'"
    cmd_centos = "python -mplatform | awk '{printf\"RESULT:\";printf$0;print\":END\"}'"

    pattern_cos = "RESULT:.*?cserver.*?:END"
    pattern_cmc = "RESULT:.*?cmc.*?:END"
    pattern_cs6 = "RESULT:.*?centos-6.*?:END"
    pattern_cs7 = "RESULT:.*?centos-7.*?:END"

    ssh,resp = Standard_Reply_SSHCmmand(ip,cmd_cos)
    ssh.close()

    ssh2,resp2 = Standard_Reply_SSHCmmand(ip,cmd_cmc)
    ssh2.close()

    ssh3,resp3 = Standard_Reply_SSHCmmand(ip,cmd_centos)
    ssh3.close()

    if not resp:
        print("Command:%s failure"%(cmd_cos))
        return
    cmd_result = str(resp)
    respList = re.compile(pattern_cos).findall(cmd_result)

    if not resp2:
        print("Command:%s failure"%(cmd_cmc))
        return
    cmd_result2 = str(resp2)
    respList2 = re.compile(pattern_cmc).findall(cmd_result2)

    if not resp3:
        print("Command:%s failure"%(cmd_centos))
        return
    cmd_result3 = str(resp3)
    respList3 = re.compile(pattern_cs7).findall(cmd_result3)


    if respList != []:
        if respList3 != []:
            serverCat[ip+":centos-7"] = "cos"
        else:
            serverCat[ip+":centos-6"] = "cos"
    elif respList2 != []:
        if respList3 != []:
            serverCat[ip+":centos-7"] = "cmc"
        else:
            serverCat[ip+":centos-6"] = "cmc"
    else:
        pass   #ignore None-CMC  None-COS




class Node:
    def __init__(self,type,ipcs,path):
        ip,cs = ipcs.split(":")

        self.ipAddress = ip
        self.configFiles = {}
        self.svcBoot = {}
        self.result = {}
        self.configResult = {}
        self.svcResult = {}
        self.type = type
        self.version = cs
        self.ssh = None

        fName = self.type + "_" + ip
        self.path = "%s/%s" % (path,fName)

        os.makedirs("%s" % (self.path))
        open("%s/%s" % (self.path,cs),"a").close()


    def setConfigFiles(self, configDict):
        if self.version == "centos-6" and self.type == "cos":
            self.configFiles = configDict["centos-6"]
        if self.version == "centos-7" and self.type == "cos":
            self.configFiles = configDict["centos-7"]
        if self.type == "cmc":
            self.configFiles = configDict


    def setServiceStatus(self, serviceDict):
        if self.version == "centos-6" and self.type == "cos":
            self.svcBoot = serviceDict["centos-6"]
        if self.version == "centos-7" and self.type == "cos":
            self.svcBoot = serviceDict["centos-7"]
        if self.type == "cmc":
            self.svcBoot = serviceDict


    def fetchConfig(self):
        for fName in self.configFiles:
            fPath = self.configFiles[fName].replace(".",fName)
            scp = pexpect.spawn("scp root@%s:%s %s" % (self.ipAddress,fPath,self.path+"/."))
            scp,result = Standard_Reply_SCP(scp,self.ipAddress)

            if result:
                self.configResult[fName] = True
            else:
                print ("scp to %s error: %s" % (self.ipAddress,scp.before[:-1]))
                self.configResult[fName] = False
            scp.close()

    def fetchStatus(self):
        if self.type == "cos":
            if self.version == "centos-7":
                cmdX = "systemctl status serviceName"
            else:
                cmdX = "service serviceName status"

            content = ""
            for svc in self.svcBoot:
                cmd = cmdX.replace("serviceName",svc)
                if not self.ssh:
                    self.ssh,resp = Standard_Reply_SSHCmmand(self.ipAddress,cmd)
                else:  
                    try:
                        self.ssh.sendline(cmd)
                        self.ssh.expect(prompt_logined,timeout=10)
                        resp = self.ssh.before[:-1]
                    except:
                        debug = "ERR::"+str(ssh.before[:-1])
                        print (debug)



                if not resp:
                    print("Command:%s failure"%(cmd))
                    content += "%s:error\n"%(svc)
                    self.svcResult[svc] = False
                else:
                    cmd_result = str(resp)
                    if "systemctl" in cmd:
                        respList = re.compile("(?<=Active: )[^\s]+ \(.*?\)").findall(cmd_result)
                    else:
                        pattern = r"(?m)(?<=%s )(?!status)\w+ \w+"%(svc)
                        respList = re.compile(pattern).findall(cmd_result)

                    if respList == []:
                        pattern2 = r"(?m)(?<=%s )\(pid\s+ \d+\)(.*?)(?=\\r)"%(svc)
                        respList2 = re.compile(pattern2).findall(cmd_result)

                        if respList2 == [] and svc != "clm":
                            status = "Not Exist::%s"%(self.ssh.before[:-1])
                        elif svc == "clm":
                            ansi_color_escape = re.compile(r'\\x1b\[[0-9;]*m')
                            cmd_result2 = ansi_color_escape.sub('', cmd_result.strip())
                            if "clm: Not running" in cmd_result2:
                                status = "Not running"
                            elif "clm: Running" in cmd_result2:
                                status = "Running"
                            else:
                                status = "Not Exist::%s"%(self.ssh.before[:-1])

                        else:
                            ansi_color_escape = re.compile(r'\\x1b\[[0-9;]*m')
                            status = ansi_color_escape.sub('', respList2[0].strip())
                    else:
                        ansi_color_escape = re.compile(r'\\x1b\[[0-9;]*m')
                        status = ansi_color_escape.sub('', respList[0].strip())

                    content += "%s:%s\n" % (svc,status)

            svcFile = self.path+"/services"
            with open(svcFile,'w') as f:
                f.write(content)
            return

        if self.type == "cmc":
            content = ""
            for svc in self.svcBoot["systemctl"]:
                cmd = "systemctl status %s" % (svc)
                if not self.ssh:
                    self.ssh,resp = Standard_Reply_SSHCmmand(self.ipAddress,cmd)
                else:  
                    try:
                        self.ssh.sendline(cmd)
                        self.ssh.expect(prompt_logined,timeout=10)
                        resp = self.ssh.before[:-1]
                    except:
                        debug = "ERR::"+str(ssh.before[:-1])
                        print (debug)

                if not resp:
                    print("Command:%s failure"%(cmd))
                    content += "%s:error\n"%(svc)
                    self.svcResult[svc] = False
                else:
                    cmd_result = str(resp)
                    respList = re.compile("(?<=Active: )[^\s]+ \(.*?\)").findall(cmd_result)
                    if respList == []:
                        status = "Not Exist::%s"%(self.ssh.before[:-1])
                    else:
                        ansi_color_escape = re.compile(r'\\x1b\[[0-9;]*m')
                        status = ansi_color_escape.sub('', respList[0].strip())

                    content += "%s:%s\n" % (svc,status)

            for svc in self.svcBoot["service"]:
                cmd = "service %s status" % (svc)
                if not self.ssh:
                    self.ssh,resp = Standard_Reply_SSHCmmand(self.ipAddress,cmd)
                else:  
                    try:
                        self.ssh.sendline(cmd)
                        self.ssh.expect(prompt_logined,timeout=10)
                        resp = self.ssh.before[:-1]
                    except:
                        debug = "ERR::"+str(ssh.before[:-1])
                        print (debug)

                if not resp:
                    print("Command:%s failure"%(cmd))
                    content += "%s:error\n"%(svc)
                    self.svcResult[svc] = False
                else:
                    cmd_result = str(resp)
                    pattern = r"(?m)(?<=%s )(?!status)\w+ \w+"%(svc)   #my python3 weird can't implement (?m)(by default), still treat it as (?s)
                    respList = re.compile(pattern).findall(cmd_result)

                    if "datastax-agent" in svc:
                        respList2 = re.compile("(?<=Active: )[^\s]+ \(.*?\)").findall(cmd_result)
                        if respList2 == []:
                            status = "Not Exist::%s"%(self.ssh.before[:-1])
                        else:
                            ansi_color_escape = re.compile(r'\\x1b\[[0-9;]*m')
                            status = ansi_color_escape.sub('', respList2[0].strip())
                    elif respList == []:
                        status = "Not Exist::%s"%(self.ssh.before[:-1])
                    else:
                        status = respList[0].strip()

                    content += "%s:%s\n" % (svc,status)
   
            svcFile = self.path+"/services"
            with open(svcFile,'w') as f:
                f.write(content)

            return

        self.ssh.close()


    def showConfigFiles(self):
        print(self.ConfigFiles)

    def showServiceStatus(self):
        print(self.ServiceStatus)

    def erResult(self,key,value):
        self.result[key] = value

def dictHandling(file,dict):

    with open(file,"r") as f:
        content = f.read()
    lines = content.split()
    if "cos_path" in file:
        for eachline in lines:
            if re.compile("^\s*$").findall(eachline) == []:
                key,value = eachline.split("::")
                if "centos-6" in key:
                    newKey = key.replace("[centos-6]","").strip()
                    dict["centos-6"][newKey] = value.strip()
                elif "centos-7" in key:
                    newKey = key.replace("[centos-7]","").strip()
                    dict["centos-7"][newKey] = value.strip()
                elif "onbox" in key and dict["cassandra"] == "onbox":
                    newKey = key.replace("[onbox]","").strip()
                    dict["centos-7"][newKey] = value.strip()
                    dict["centos-6"][newKey.strip()] = value.strip()
                elif "onbox" in key and dict["cassandra"] == "offbox":
                    continue
                else:
                    dict["centos-7"][key.strip()] = value.strip()
                    dict["centos-6"][key.strip()] = value.strip()
        return dict

    if "cos_services" in file:
        for eachline in lines:
            if re.compile("^\s*$").findall(eachline) == []:
                key,value = eachline.split(":")
                if "centos-6" in key:
                    newKey = key.replace("[centos-6]","").strip()
                    dict["centos-6"][newKey] = value.strip()
                elif "centos-7" in key:
                    newKey = key.replace("[centos-7]","").strip()
                    dict["centos-7"][newKey] = value.strip()
                else:
                    dict["centos-7"][key.strip()] = value.strip()
                    dict["centos-6"][key.strip()] = value.strip()
        return dict

    if "cmc_path" in file:
        for eachline in lines:
            if re.compile("^\s*$").findall(eachline) == []:
                key,value = eachline.split("::")
                dict[key.strip()] = value.strip()
        return dict

    if "cmc_services" in file:
        for eachline in lines:
            if re.compile("^\s*$").findall(eachline) == []:
                key,value = eachline.split(":")
                if "systemctl" in key:
                    newKey = key.replace("[systemctl]","").strip()
                    dict["systemctl"][newKey] = value.strip()
                elif "service" in key:
                    newKey = key.replace("[service]","").strip()
                    dict["service"][newKey] = value.strip()
        return dict



def listServer(ip):
    #1. Fetch the list of COS and 
    cmd_consul = "consul members"
    ssh,resp = Standard_Reply_SSHCmmand(ip,cmd_consul)
    ssh.close()

    if not resp:
        print("Command:%s failure"%(cmd_consul))
        return


    consul_result = str(resp)
    pattern = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?=:8301)"
    ipList = re.compile(pattern).findall(consul_result)

    manager_obj = Manager()
    serverCat = manager_obj.dict()


    jobs = []

    for ip in ipList:
        p = Process(target=categoryFilter, args=(ip,serverCat))
        p.start()
        jobs.append(p)

    for i in jobs:
        i.join()


    cmcList = []
    cosList = []
    for key,value in serverCat.items():
        if value == "cos": 
            cosList.append(key)
        else:
            cmcList.append(key)

    return cosList,cmcList

###############1. Done################

def mainAction(cosList,cmcList,tag,base):
    #2. Re-Org the dictionary of COS server/COS config; CMC server/CMC config
    if os.path.isdir(tag):
        print("the folder already exist!")
        answer = input("Overwritten the Folder??yes/no [y/n]")
        if 'y' in answer:
            shutil.rmtree(tag)
        else:
            return
    os.mkdir(tag)

    cos_node_services = {}
    cos_node_services["centos-6"] = {}
    cos_node_services["centos-7"] = {}
    cos_node_path = {}
    cos_node_path["centos-6"] = {}
    cos_node_path["centos-7"] = {}
    cmc_node_path = {}
    cmc_node_services = {}
    cmc_node_services["service"] = {}
    cmc_node_services["systemctl"] = {}

    if cmcList == []:
        cos_node_path["cassandra"] = "onbox"
    else:
        cos_node_path["cassandra"] = "offbox"

    cos_node_services = dictHandling(base+"/cos_services",cos_node_services)
    cos_node_path = dictHandling(base+"/cos_path",cos_node_path)
    cmc_node_path = dictHandling(base+"/cmc_path",cmc_node_path)
    cmc_node_services = dictHandling(base+"/cmc_services",cmc_node_services)

    classCos = []
    for item in cosList:
        cosNode = Node("cos",item,tag)
        cosNode.setConfigFiles(cos_node_path)
        cosNode.setServiceStatus(cos_node_services)
        classCos.append(cosNode)

    classCmc = []
    for item in cmcList:
        cmcNode = Node("cmc",item,tag)
        cmcNode.setConfigFiles(cmc_node_path)
        cmcNode.setServiceStatus(cmc_node_services)
        classCmc.append(cmcNode)

#3. Fetch COS
    jobs = []
    for cosObj in classCos:
        p = Process(target=cosObj.fetchConfig, args=())
        p.start()
        jobs.append(p)

#4. Fetch CMC
    for cmcObj in classCmc:
        p = Process(target=cmcObj.fetchConfig, args=())
        p.start()
        jobs.append(p)

#5. Fetch COS services
    for cosObj in classCos:
       p = Process(target=cosObj.fetchStatus, args=())
       p.start()
       jobs.append(p)

#6. Fetch CMC services]
    for cosObj in classCmc:
        p = Process(target=cosObj.fetchStatus, args=())
        p.start()
        jobs.append(p)

    for i in jobs:
        i.join()
    
def dirDiff(comList):
    dir1 = comList[0].strip()
    dir2 = comList[1].strip()

    result = ""
    cmd = "diff --brief -r %s %s" % (dir1,dir2)
    dirList = os.popen(cmd).read().split("\n")
    for item in dirList:
        result += item + "\n"
        if "diff" in item:
            file1 = item.split()[1]
            file2 = item.split()[3]
            cmd2 = "diff %s %s" % (file1,file2)
            fileList = os.popen(cmd2).read()
            result += fileList + "\n"
            result += "~~~~~~~~~~~~~~~~\n"
    print (result)



#class UserAction(argparse.Action):
#    def __call__(self, parser, namespace, values, option_string=None):
#        if not namespace.config_folder_Name:
#            parser.error('Missing config_folder_Name')
#        setattr(namespace, self.dest, values)


if __name__ == '__main__':
    usage = "ConfigCheck_v6.py [-s SAMPLE_IP <-cn CONFIG_FOLDER_NAME>] [-sn SERVER_FOLDER_NAME] [-d folder1,folder2] [--version] [-h HELP]"
    parser = argparse.ArgumentParser(description='The COS Cluster Configuration Checking Tool',usage=usage)
    #parser.add_argument("sample_IP", type=str, help="The Server IP of the Cluster Member)
    #parser.add_argument("config_folder_Name", type=str, help="The Folder name for the reference config file")

    parser.add_argument('-cn',action='store',
                        dest='config_folder_Name',default=None,
                        help='The Folder name for the reference config file')
#   parser.add_argument('-s', action=UserAction,
#                       dest='sample_IP',default=None,
#                       help='The Server IP of the Cluster Member')
    parser.add_argument('-s', action='store',
                        dest='sample_IP',default=None,
                        help='The Server IP of the Cluster Member')
    parser.add_argument('-sn', action='store',
                        dest='server_folder_Name',default=None,
                        help='The Folder name created for each server')
    parser.add_argument('-d', action='store',
                        dest='diff',default=None,
                        help='2 folder need to compare the difference')

    parser.add_argument('--version', action='version',
                        version='%(prog)s 1.0')

    results = parser.parse_args()


    if results.sample_IP and not results.config_folder_Name:
        print(parser.print_help())
        sys.exit(1)

    if results.config_folder_Name:
        base = results.config_folder_Name.strip()

    if results.sample_IP:
        ip = results.sample_IP.strip()
        if results.server_folder_Name:
            tag = results.server_folder_Name.strip().replace(":","@")
        else:
            t = str(datetime.datetime.now()).replace(":","@")
            tag = t.replace(" ","#")
        cosList,cmcList = listServer(ip)
        mainAction(cosList,cmcList,tag,base)
    elif results.diff:
        comList = results.diff.strip().split(",")
        dirDiff(comList)
    else:
        print(parser.print_help())


