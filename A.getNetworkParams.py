
''' 
 Author: Chao Fan
 E-mail: fanchao.cn@gmail.com 
 Created in Jun. 2015, revised in Jan. 2016. 
 
 This code obtains the main parameters of each network.
 Input: 
     node list and edge list of network.
     The format of node list is: node ID, attribute1, arribute2.... The attributes are seperated by tabs.
     The format of node list is: ID of node 1, ID of node 2, type of edge, attribute1, arribute2.... 
     The attributes are seperated by tabs. The type of edges in our research is 'undirected'.
 Output: 
     print the parameters on the screen.
 
'''

def get_net_params(nodelist,edgelist):
    import networkx as nx
    G = nx.Graph()    
    G.add_nodes_from(nodeList)
    G.add_edges_from(edgeList,create_using = nx.Graph())
    
    N = G.number_of_nodes()
    print 'the total number of nodes in the network is: '+str(N)
    M = G.number_of_edges()
    print 'the total number of edge in the network is: '+str(M)
    aveDegree = float(2.0*M/N)
    aveDegree = round(aveDegree,4)
    print 'the average degree of the network is: '+str(aveDegree)
    aveCC = nx.average_clustering(G) 
    aveCC = round(aveCC,4)
    print 'the average clustering coefficient of the network is: '+str(aveCC)
    r = nx.degree_pearson_correlation_coefficient(G)
    r = round(r,4)
    print 'the assortativity coefficient of the network is: '+str(r)
    ncc = nx.number_connected_components(G)    
    print 'the total number of connected components is: '+str(ncc)        
    CC = nx.connected_components(G)
    print 'the number of nodes in each connected components is: '
    for k in CC:
        print str(len(k)),
    print '\n'
    
    
if __name__ == "__main__":
    yearList = ['','1986', '1992', '1999', '2010']    
    for eachYear in yearList:    
        print 'Year '+str(eachYear)
        # read nodes
        nodeFile = open('nodelist'+str(eachYear)+'.txt','r')
        nodeList = []
        for eachline in nodeFile:
            nodeID = eachline.strip().split('\t')[0]
            nodeList.append(nodeID)
        # read edges    
        edgeFile = open('edgelist'+str(eachYear)+'.txt','r')   
        edgeList = []
        for eachline in edgeFile:
            item = eachline.strip().split('\t')
            a,b = item[0],item[1]
            edgeList.append((a,b))
        # calculate parameters
        get_net_params(nodeList,edgeList) 
