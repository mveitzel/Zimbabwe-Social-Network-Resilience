
''' 
 Author: Chao Fan
 E-mail: fanchao.cn@gmail.com 
 Created in Jun. 2015, revised in Jan. 2016. 
 
 This code obtains the comers and leavers for some specific household in each year.
 Input: 
     1. Node list of the network of each year (1986, 1992, 1999 and 2010).      
     2. Individual attribute including ID, gender, birth year, death year and household ID for each year.
 Output: 
     The comer and leaver of each household in each year.
     Results format:
         Year
         new comers:
         ID [gender, birth year, death year, household 1986, household 1992, household 1999, household 2010]
         ......
         leavers:
         ID [gender, birth year, death year, household 1986, household 1992, household 1999, household 2010]     
         ...... 
 '''
  
idvInfo = open('nodeList.txt','r')
idvInfoDict = {}
for eachline in idvInfo:
    item = eachline.strip().split('\t')
    ID = item[0]
    info = item[1:]
    idvInfoDict[ID] = info

hhList = ['1','2','3','3.1','4','4.1','5','5.1','5.2','6']
for eachHH in hhList:
    hhDict = {}
    yearList = ['1986', '1992', '1999', '2010']
    for k in range(4):
        eachYear = yearList[k]    
        nodeFile = open('nodeList'+eachYear+'.txt','r')
        hhDict[k] = []
        for eachline in nodeFile:
            item = eachline.strip().split('\t')
            idvID,hhID = item[0],item[2]
            if hhID == eachHH:            
                hhDict[k].append(idvID) 
        nodeFile.close()
    
    outFile = open('hhComerLeaver'+str(eachHH)+'.txt','w')
    for k in range(3):
        print yearList[k+1]
        outFile.write(yearList[k+1]+'\n')
        aList = hhDict[k]
        bList = hhDict[k+1]
        print 'new comers:'
        outFile.write('new comers:'+'\n')
        for k in bList:
            if k not in aList:
                print k, idvInfoDict[k]
                outFile.write(str(k)+'\t'+str(idvInfoDict[k])+'\n')
        print 'leavers:'
        outFile.write('leavers:'+'\n')
        for k in aList:
            if k not in bList:
                print k, idvInfoDict[k]
                outFile.write(str(k)+'\t'+str(idvInfoDict[k])+'\n')
        print '\n'
        outFile.write('\n')