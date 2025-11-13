
'''
 Author: Chao Fan
 E-mail: fanchao.cn@gmail.com 
 Created in Jun. 2015, revised in Jan. 2016. 
 
 This code obtains the number of individuals that migrants between households with directions, 
 which used to construct weighted directed network. 
 Note 1: Here only adjacent household transfering is considered. 
 Note 2: The situation that household ID = 0, which means such individual is not in the community in the year is not considered.
 
 Input: 
     Household information of each individual.
     The format is: node ID, household ID in 1986, 1992, 1999 and 2010. 
     The attributes are seperated by tabs.     
 Output: 
     The weight and direction of individual miggration.
     The format is: source household, target household, weight.
     The attributes are seperated by tabs.     
 
 Example1:
     Household information of individual1 is: ID1 A B B C, so its miggration pattern is A-B and B-C.
     Household information of individual2 is: ID2 A B 0 C, so its miggration pattern is only A-B.
'''

inFile = open('info-household.txt','r')
outFile = open('hhMigration.txt','w')

totalHHDict = {}
for eachline in inFile:
    idvHHDict = {}
    item = eachline.strip().split('\t')
    hhList = [item[1],item[2],item[3],item[4]]
    for i in range(3):
        for j in range(i+1,4):
            hh1,hh2 = hhList[i],hhList[j]
            if hh1 != hh2 and hh1 != '0' and hh2 != '0':
                link = (hh1,hh2)
                if not idvHHDict.has_key(link):
                    idvHHDict[link] = 0                
    for eachkey in idvHHDict.iterkeys():
        if not totalHHDict.has_key(eachkey):
            totalHHDict[eachkey] = 0
        totalHHDict[eachkey] += 1
        

for i,j in sorted(totalHHDict.iteritems(), key=lambda x:x[1], reverse=True):
    outFile.write(str(i[0])+'\t'+str(i[1])+'\t'+str(j)+'\n')
