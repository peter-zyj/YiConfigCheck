======
Usage
======
ConfigCheck.py [-s SAMPLE_IP <-cn CONFIG_FOLDER_NAME>] [-sn SERVER_FOLDER_NAME] [-d folder1,folder2] [--version] [-h HELP]

 The COS Cluster Configuration Checking Tool

 optional arguments:
   -h, --help            show this help message and exit
   -cn CONFIG_FOLDER_NAME
                         The Folder name for the reference config file
   -s SAMPLE_IP          The Server IP of the Cluster Member
   -sn SERVER_FOLDER_NAME
                         The Folder name created for each server
   -d DIFF               2 folder need to compare the difference
   --version             show program's version number and exit
 None

======== 
Senario
========
1.Before the Cluster Upgrade/Update ,or,  Customer Running well without big issue
Fetch the Configuration of the Cluster(like the baseline)::
 
 time python3 ConfigCheck.py -s 10.94.153.42 -cn standard -sn Before_RUS       //10.94.153.42 is just one member of the cluster
 the folder already exist!
 Overwritten the Folder??yes/no [y/n]y

 real        0m13.846s
 user       0m2.598s
 sys          0m1.682s
 
Before_RUS yijunzhu$ 
tree::
 |____cmc_10.94.153.45
 | |____cassandra-env.sh
 | |____cassandra-rackdc.properties
 | |____cassandra.yaml
 | |____centos-7
 | |____chrony.conf
 | |____consul.json
 | |____hosts
 | |____network
 | |____services
 |____cmc_10.94.153.46
 | |____cassandra-env.sh
 | |____cassandra-rackdc.properties
 | |____cassandra.yaml
 .......
 |____cos_10.94.153.41
 | |____centos-7
 | |____chrony.conf
 | |____consul.json
 | |____cosd.conf
 | |____public.xml
 | |____RemoteServers
 | |____services
 | |____setupfile
 | |____subnettable
 |____cos_10.94.153.42
 | |____centos-7
 | |____chrony.conf
 | |____consul.json
 | |____cosd.conf
 | |____public.xml
 | |____RemoteServers
 | |____services 
 
2.After the Upgrade/Update ,or, Customer report the issues;   Before continue the deep debug/trouble-shooting  
Fetch the Configuration of the Cluster::

 time python3 ConfigCheck_v7.py -s 10.94.153.42 -cn standard -sn After_RUS
 real        0m13.846s
 user       0m2.598s
 sys          0m1.682s
 
3.Compare the configuration and service status::
 
 python3 ConfigCheck_v7.py -d Before_RUS,After_RUS

 Files Before_RUS/cos_10.94.153.41/centos-7 and After_RUS/cos_10.94.153.41/centos-7 differ
 1d0
 < zhu

 ~~~~~~~~~~~~~~~~
 Files Before_RUS /cos_10.94.153.41/setupfile and After_RUS/cos_10.94.153.41/setupfile differ
 33c33
 < surge support 1
 ---
 > #surge support 1

 ~~~~~~~~~~~~~~~~
 Only in After_RUS: yijun   
