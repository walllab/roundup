#! /usr/bin/python

import math
import operator
import random
import re
import numpy as np
import orthology_query
import format_orthology_cluster_result

'''
need python version 2.6 for bin()
'''


class BinStrSafe:
    '''
    This is a safe but slow implementation of binary string,
    it is used to test the functioning of BinStr class below
    in a new system, new in terms of OS and memory
    '''
    def __init__(self,aBinStr):
        self.bs=aBinStr
        self.num1s = -1;
        self.num0s = -1;
        self.length = len(aBinStr)

    def __and__(self,other):
        assert len(self.bs) == len(other.bs)

        tmpStr=""
        for ch1, ch2 in zip(self.bs,other.bs):
            if ch1 == ch2: tmpStr+=ch1
            else: tmpStr+="0"

        return BinStrSafe(tmpStr)

    def __xor__(self,other):
        assert len(self.bs) == len(other.bs)

        tmpStr=""
        t=('1','0')
        for ch1, ch2 in zip(self.bs,other.bs):
            tmpStr+=t[ch1==ch2]

        return BinStrSafe(tmpStr)

    def __or__(self,other):
        assert len(self.bs) == len(other.bs)

        tmpStr=""
        for ch1, ch2 in zip(self.bs,other.bs):
            if ch1 == ch2: tmpStr+= ch1
            else: tmpStr+="1"

        return BinStrSafe(tmpStr)

    def __invert__(self):
        tmpStr=""
        t=('1','0')
        for ch1 in self.bs:
            tmpStr+=t[ch1=="1"]

        return BinStrSafe(tmpStr)

    def toStr(self):
        return self.bs

    def count1_0(self):
        self.num1s=self.__count1()
        self.num0s = self.length - self.num1s

    def hammingDistance(self,other):
        tmpInt=0
        for ch1, ch2 in zip(self.bs,other.bs):
            tmpInt+=(ch1!=ch2)

        return tmpInt

    def __count1(self,aBinStr=None):
        if aBinStr is None:tmpStr=self.bs
        else: tmpStr=aBinStr
        n1=0
        for ch1 in tmpStr:
            n1+=(ch1=="1")

        return n1

    def getJointDistStats(self,other):
        """It returns the number of ij in a joint distribution,
        i,j = 0,1; The return value is a list [n11,n10,n01,n00]."""
        if self.num1s == -1: self.count1_0()
        if other.num1s == -1: other.count1_0()

        joint = (self & other)
        n11 = joint.__count1() #number of 11 in joint distribution
        n10 = self.num1s - n11
        n01 = other.num1s - n11
        n00 = self.length - self.num1s - other.num1s + n11

        return [n11,n10,n01,n00]


    def U(self,other,ilni=None):
        '''calculate the Uncertainty Coefficient U(self|other),
        the two binary string must have equal length.
        U(x|y) = [H(x) + H(y) - H(x,y)] / H(x)
               = 1-
               [Sum(nyi*log nyi)-Sum(nij*log nij)] / [n*log n - Sum(nxi*log nxi)]
        i,j = 0, 1
        nyi: the number of i in the profile of y
        nxi: the number of i in the profile of x
        nij: the number of ij in the joint distribution of x and y
        log can be base 2 or e, here e is used.
        ilni is an array of length self.length, ilni[i] == i*ln(i).
        This array is used to avoid repeated calculation of i*ln(i)
        for the same i.'''
        assert self.num0s * self.num1s > 0, "some genes have too few 0 or 1"
        jointStats = self.getJointDistStats(other)

        return 1 - (self.__sumKlnK([other.num0s,other.num1s],ilni) - \
                    self.__sumKlnK(jointStats,ilni)) /               \
                   (self.__sumKlnK([self.length],ilni) -             \
                    self.__sumKlnK([self.num0s,self.num1s],ilni))


    def __sumKlnK(self,kArray,ilni=None):
        """calculate Sum(k*ln(k)), for k in kArray"""
        tmpSum = 0.0
        if ilni is None:
            for k in kArray:
                assert k>= 0
                if k > 0: tmpSum += k*math.log(k)
        else:
            for k in kArray:
                assert k>= 0
                tmpSum += ilni[k]

        return tmpSum


class BinStr:
    """
    Do operations on binary string, binary operators are for binary
    strings of EQUAL length. The binary string is converted
    to long int type which all the operation are acted on. While long
    int has unlimited precision in python, its actual precision may be
    bounded by physical memory or OS. A test of 1200 bits binary strings
    implemented by this class runs ok on a windows xp PC with 3G RAM
    
    The first time to use this class in a new system, one should run
    testBinStrClass() to make sure it is working correctly.
    """

    def __init__(self, aBinStrOrInt=None, length=None):
        """aBinStrOrInt can be a binary string or int. __init__ can be
        called with __init__(aBinStr) or __init__(anInt,length) or
        __init__() to use its utility functions"""
        if aBinStrOrInt is not None:
            if type(aBinStrOrInt) is str:
                self.int = long(aBinStrOrInt, 2)
                self.length = len(aBinStrOrInt)
            else:
                self.int = aBinStrOrInt
                self.length = length

            self.num1s = -1;
            self.num0s = -1;

    def __and__(self, other):
        tmpInt = self.int & other.int
        return BinStr(tmpInt, self.length)

    def __xor__(self, other):
        tmpInt = self.int ^ other.int
        return BinStr(tmpInt, self.length)

    def __or__(self, other):
        tmpInt = self.int | other.int
        return BinStr(tmpInt, self.length)

    def __invert__(self):
        """flip 1 to 0 and 0 to 1, return the integer representing the
        flipped binary string"""
        mask = (1 << self.length) - 1  #mask is 11...111 of length self.length
        '''From Python Doc: "The unary ~ (invert) operator yields the bitwise
        inversion of its plain or long integer argument. The bitwise inversion
        of x is defined as -(x+1)." It is a bit confusing!'''
        tmpInt =  ~ self.int & mask
        return BinStr(tmpInt, self.length)


    def count1_0(self):
        """calculate the number of 1s and 0s in a binary string"""
        if self.num0s == -1 or self.num1s == -1:
            self.num1s = self.__count1()
            self.num0s = self.length - self.num1s


    def hammingDistance(self, other):
        """Hamming Distance is the number of different bits
        between two binary strings"""
        tmpInt = self.int ^ other.int
        return self.__count1(tmpInt)


    def getJointDistStats(self, other):
        """It returns the number of ij in a joint distribution,
        i,j = 0,1; The return value is a list [n11,n10,n01,n00]."""
        if self.num1s == -1: self.count1_0()
        if other.num1s == -1: other.count1_0()

        joint = self & other
        n11 = joint.__count1() #number of 11 in joint distribution
        n10 = self.num1s - n11
        n01 = other.num1s - n11
        n00 = self.length - self.num1s - other.num1s + n11

        return [n11, n10, n01, n00]


#    def U(self, other, ilni=None):
#        '''calculate the Uncertainty Coefficient U(self|other),
#        the two binary string must have equal length.
#        U(x|y) = [H(x) + H(y) - H(x,y)] / H(x) = I(x,y) / H(x)
#               = 1-
#               [Sum(nyi*log nyi)-Sum(nij*log nij)] / [n*log n - Sum(nxi*log nxi)]
#        i,j = 0, 1
#        nyi: the number of i in the profile of y
#        nxi: the number of i in the profile of x
#        nij: the number of ij in the joint distribution of x and y
#        The base of log does not affect the U
#        ilni is an array of length self.length, ilni[i] == i*ln(i).
#        This array is used to avoid repeated calculation of i*ln(i)
#        for the same i.
#
#        Note: U is from 0 to 1, i.e. [0,1]. However in python, U can be
#        -6.345e-16 when it should be 0, making the U negative'''
#        jointStats = self.getJointDistStats(other)
#        assert self.num0s * self.num1s > 0, "some genes have too few 0 or 1"
#
#        denom=self.__sumKlnK([self.length], ilni) -             \
#             self.__sumKlnK([self.num0s, self.num1s], ilni)
#
#        numerator = self.__sumKlnK([other.num0s, other.num1s], ilni) - \
#                    self.__sumKlnK(jointStats, ilni)
#
#        return  1 -  numerator / denom


    def U(self, other, ilni=None):
        return 1-self.hammingDistance(other)*1.0/self.length


    def H(self, ilni=None, base=2): #math.e
        '''return the entropy H = [n*log n - Sum(ni*log ni)]/n'''
        self.count1_0()
        assert self.num0s * self.num1s > 0, "some genes have too few 0 or 1"
        numerator=self.__sumKlnK([self.length], ilni, base) -             \
             self.__sumKlnK([self.num0s, self.num1s], ilni, base)

        return numerator/self.length


    def jH(self, other, ilni=None, base=2): #math.e
        '''return the joint entropy H(x,y) = [n*log n - Sum(nij*log nij)]/n'''
        jointStats = self.getJointDistStats(other)
        assert self.num0s * self.num1s > 0, "self have too few 0 or 1"
        assert other.num0s * other.num1s > 0, "other have too few 0 or 1"
        assert self.length > 0

        numerator = self.__sumKlnK([self.length], ilni, base) -  \
             self.__sumKlnK(jointStats, ilni, base)

        return  numerator / self.length


    def I(self, other, ilni=None, base=2):
        '''return the mutural information
        I(x,y) = [n*log(n)-Sum(nix*log(nix)) - Sum(niy*log(niy)) + Sum(nij*log(nij))]/n'''
        jointStats = self.getJointDistStats(other)
        assert self.num0s * self.num1s > 0, "self have too few 0 or 1"
        assert other.num0s * other.num1s > 0, "other have too few 0 or 1"
        assert self.length > 0

        numerator = self.__sumKlnK([self.length], ilni, base) -     \
             self.__sumKlnK([self.num0s, self.num1s], ilni, base) -   \
             self.__sumKlnK([other.num0s, other.num1s], ilni, base) + \
             self.__sumKlnK(jointStats, ilni, base)

        return  numerator / self.length


    def toStr(self, anInt=None):
        """output the binary string of an int with precision of the
        length of the original binStr"""
        if anInt is None: anInt = self.int

        mask = 1 << self.length
        assert mask > anInt
        tmpInt = anInt | mask
        tmpStr = bin(tmpInt)
        return tmpStr[3:]


    def toList(self):
        """output the list of 0 and 1 of an int with precision of the
        length of the original binStr"""
        return self.toStr().replace("", " ").strip().split()


    def toRandBinStr(self,length,prob0):
        """convert to random bin string of length length
        with prob(0)==prob0"""
        randInt=0
        binStr=""
        while length:
            length-=1
            randInt=random.randint(1,10)
            if randInt <= 10*prob0: binStr+="0"
            else:binStr+="1"

        self.__init__(binStr)


    def testBinStrClass(self,strLen=1200,numStr=1000):
        fOr = lambda a, b: a | b
        fAnd = lambda a, b: a & b
        fXor = lambda a, b: a ^ b
        fInvert = lambda a, b=None: ~a
        fHd=lambda a, b: a.hammingDistance(b)
        fJd=lambda a, b: a.getJointDistStats(b)

        #U is not tested because if all the below works
        #U should be fine
        fs=[fOr, fAnd, fXor, fInvert,fHd, fJd]
        fNames=["|","&","^","~","hd","jd"]

        while numStr:
            numStr-=1
            prob=random.randint(0,10)/10.0
            self.toRandBinStr(strLen,prob)
            other=BinStr()
            prob=random.randint(0,10)/10.0
            other.toRandBinStr(strLen,prob)
            bss1=BinStrSafe(self.toStr())
            bss2=BinStrSafe(other.toStr())

            for f,fn in zip(fs,fNames):
                bsTmp=f(self, other)
                bssTmp=f(bss1, bss2)
                if fn == '~':
                    assert bsTmp==bssTmp or bsTmp.toStr() == bssTmp.toStr(), \
                    "Error in " + fn + "\nStr:\t" + bss1.toStr()
                    "In BinStr:\t"+ bsTmp.toStr()+ \
                    "In BinStrSafe:\t"+ bssTmp.toStr()
                else:
                    assert bsTmp==bssTmp or bsTmp.toStr() == bssTmp.toStr(), \
                    "Error in " + fn + "\nStr1:\t" + \
                    bss1.toStr()+"\nStr2:\t"+ bss2.toStr()+ \
                    "In BinStr:\t"+ bsTmp.toStr()+ \
                    "In BinStrSafe:\t"+ bssTmp.toStr()

        print "BinStr class is working well!"



    def __count1(self, anInt=None):
        """return the number of 1s in the binary format of an int"""
        if anInt is None: tmpInt = self.int
        else: tmpInt = anInt
        n1 = 0
        """tmpInt-1 in two's complement flips the rightmost 1 and inverts
        the 0s to the right of it. So, tmpInt & (tmpInt-1) removes the
        rightmost 1"""

        while tmpInt:
            tmpInt = tmpInt & (tmpInt-1)
            n1 += 1

        return n1

    def __bitLength(self, anInt=None):
        """return the index of the left-most 1. 0011001 returns 5"""
        index = 0
        if anInt is None: tmpInt = self.int
        else: tmpInt = anInt

        while tmpInt:
            tmpInt = tmpInt >> 1
            index += 1

        return index


    def __sumKlnK(self, kArray, ilni=None, base=2):
        """calculate Sum(k*log(k,base)), for k in kArray"""
        tmpSum = 0.0
        if ilni is None:
            for k in kArray:
                assert k >= 0,"some ni < 0"
                if k>0: tmpSum += k * math.log(k,base) #if k==0, klnk=0
        else:
            for k in kArray:
                assert k >= 0,"some ni <= 0"
                tmpSum += ilni[k]

        return tmpSum


class GeneProfile:
    """This class stores a phylogenetic profile and do
    a number of operations on those profiles"""


    __functionNames = ("  and(a,b)", " !and(a,b)", "  ior(a,b)", " !ior(a,b)", \
                       " and(a,!b)", "!and(a,!b)", " and(b,!a)", "!and(b,!a)", \
                       "  xor(a,b)", " !xor(a,b)")
    __functionIDs = (1,2,3,4,5,6,5,6,7,8)
    __f1 = lambda a, b: a & b
    __f3 = lambda a, b: a | b
    __f5a = lambda a, b: a & ( ~ b)
    __f5b = lambda a, b: b & ( ~ a)
    __f7 = lambda a, b: a ^ b
    __fs = (__f1, __f3, __f5a, __f5b, __f7)

    __ilni = [0]
    # An array to store i*ln(i) for i in 0..numOrgs-1, it is created to
    # avoid repeated computation of i*ln(i) for the same i

    def __init__(self, profileName=None, orgs=None):
        """Create a phylogenetic profile with given profileName and
        orgs, an array of organism names
        call __init__() to use its utility function"""
        if profileName is not None and orgs is not None:
            self.name = profileName
            self.orgs = orgs[:]
            self.geneIDs = []  #string array of geneIDs
            self.profiles = []  #profile of genes in BinStr array
            self.results = []
            """list of tuple, each tuple=
            (fID, fName, cID, aID, bID, U(c|f(a,b)), U(c|a),
             U(c|b), U(c|f(a,b))-U(c|a)-U(c|b)) """

            if len(self.__ilni) < len(orgs):
                f = lambda i:i * math.log(i)
                self.__ilni.extend(map(f,range(len(self.__ilni),len(orgs)+1)))




    def __delGenesWlowH(self, min0_1):
        """delete genes with low H (entropy), ie., those with too
        few 0s or 1s. They are not useful in finding logic triplets.
           min0_1: if < 1: min percentage of 0s or 1s in the profile
        of a gene. If > 1: min number of 0 or 1 in the profile.
           This method removes genes where in its profile
        num0s or num1s < math.floor(min0_1*numOrg) if min0_1 < 1, or
        num0s or num1s < min0_1 if min0_1 > 1"""
        numOrgs = len(self.orgs)
        if min0_1 < 1:
            minNum0or1 = math.floor(min0_1 * numOrgs)
        else: minNum0or1 = min0_1
        numGenes = len(self.geneIDs)

        for i in xrange(numGenes-1, -1, -1):
            aProfile = self.profiles[i]
            aProfile.count1_0()
            if aProfile.num0s < minNum0or1 or aProfile.num1s < minNum0or1:
                del(self.geneIDs[i])
                del(self.profiles[i])
                

    def getProfileFromRoundup(self,queryFileName):
        '''
        read query from queryFile and query the roundup to get the
        phylogenetic profile, i.e, the matrix. Format of query file is:
        genomes=Chlamydia_trachomatis.aa, Mycoplasma_genitalium.aa, Ureaplasma_urealyticum.aa
        evalue=1e-20
        divergence=0.2 
        distance_lower_limit=None
        distance_upper_limit=None
        '''
        # read parameters
        sp=re.compile('[=#]')
        reps={'None':None,'y':True,'n':False}
        f=lambda x: x.strip()
        param={}
        #with open(queryFileName, 'r') as iFile: #not compatible with Python v2.5
        iFile = open(queryFileName, 'r')
        for line in iFile:
            line=line.strip()
            if line and line.find("#")!=0:
                line=line.replace(' ','')
                tmpList=map(f,sp.split(line))
                if tmpList[1] in reps:
                    param[tmpList[0]]=reps[tmpList[1]]
                else:param[tmpList[0]]=tmpList[1]
        iFile.close()

        param['genomes']=param['genomes'].split(',')

        # get Orthologs from roundup db, result is a dict
        result=orthology_query.doOrthologyQuery2(**param)

        '''This is a revised version of clusterResultToPhylogeneticProfile()
        in format_orthology_cluster_result.py. The revision skipped the
        caching step'''

        headers = result['headers']
        self.__init__(param['query_desc'], headers[:-1]) 

        f=lambda x:str(int(bool(x)))
        seqIdToDataMap = result.get('seq_id_to_data_map', {})
        termMap = result.get('term_map', {})

        assert result['type'] == 'clusters'
        for row in result['rows']:
            aProfile=map(f,row[:-1])
            self.profiles.append(BinStr(''.join(aProfile)))
            
            clusterInfo = ['', '', '']
            for seqIds in row:
                for seqId in seqIds:
                    newClusterInfo = format_orthology_cluster_result.makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    clusterInfo = format_orthology_cluster_result.chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
            self.geneIDs.append(','.join(clusterInfo))



    def getLogicTripletsUnique(self, min0_1, maxUcab, minUcf):
        """return the number of UNIQUE logic triplets satifying the
        criterion: min0_1, maxUcab, minUcf; And add those triplet into
        self.results. Being unique means that for each triplet c,a,b,
        only the f with max U(c|f) is selected UNLESS
        U(c|f.greatest) - U(c|f.other) < 0.1, when f.other will be
        selected too. This method is not recommended to use because
        without bootstrap, U value from one sample is not very
        reliable, therefore fs with smaller U may also be real and
        should be reported as well.

        Note: U(c|f) == U(c|!f),in this case the one having smaller
        hamming distance with c is selected, both f and !f are selected
        if they have equal hamming distance with c.

        min0_1: if < 1: min percentage of 0s or 1s in the profile
        of a gene. If > 1: min number of 0 or 1 in the profile.
        maxUcab: max U(c|a) or U(c|b)
        minUcf: min U(c|f)"""
        self.__delGenesWlowH(min0_1)
        numGenes = len(self.profiles)

        for a in xrange(numGenes):
            for b in xrange(a + 1, numGenes):
                for c in xrange(numGenes):
                    if c not in [a,b]:
                        pc = self.profiles[c]
                        pa = self.profiles[a]
                        pb = self.profiles[b]
                        Uca = pc.U(pa, self.__ilni)
                        Ucb = pc.U(pb, self.__ilni)
                        if Uca < maxUcab and Ucb < maxUcab:
                            UcfList=[]
                            for i in range(5):
                                f = self.__fs[i]
                                fab = f(pa, pb)
                                Ifab =  ~ fab  #If is !f
                                Ucf = pc.U(fab, self.__ilni) # Ucf == Uc!f

                                if Ucf > minUcf:
                                    isIf,isf = 0,0
                                    hdf = pc.hammingDistance(fab)
                                    hdIf = pc.hammingDistance(Ifab)
                                    if hdf > hdIf:isIf = 1
                                    elif hdf < hdIf:isf = 1
                                    else:isf,isIf = 1,1                    

                                    if isf: UcfList.append([2*i,Ucf])
                                    if isIf: UcfList.append([2*i+1,Ucf])

                            # difference from getLogicTriplet
                            if len(UcfList) > 0:  # for same c,a,b, only take the greatest Ucf
                                UcfList=sorted(UcfList, key=operator.itemgetter(1), reverse=True)

                                for k in xrange(len(UcfList)):
                                    if k==0 or UcfList[0][1] - UcfList[k][1] < 0.1:
                                            # any UcfList[k][1] that is equal to UcfList[0][1]
                                            # should be added to result. But the == for two float
                                            # numbers may not work properly.
                                        self.__fillResults(UcfList[k][0], c, a, b, UcfList[k][1], Uca, Ucb)

        return len(self.results) #return false if no triplet is found


    def getLogicTriplets(self, min0_1, maxUcab, minUcf):
        """return the number of logic triplets satifying the
        criterion: min0_1, maxUcab, minUcf; And add those triplet into
        self.results.  For a triplet c,a,b, any relationship that
        meets the criterion are selected, so there can be multiple
        relationships for the triplet.

        Note: U(c|f) == U(c|!f),in this case the one having smaller
        hamming distance with c is selected, both f and !f are selected
        if they have equal hamming distance with c.

        min0_1: if < 1: min percentage of 0s or 1s in the profile
        of a gene. If > 1: min number of 0 or 1 in the profile.
        maxUcab: max U(c|a) or U(c|b)
        minUcf: min U(c|f)"""
        self.__delGenesWlowH(min0_1)
        numGenes = len(self.profiles)

        for a in xrange(numGenes):
            print "gene #:",a+1,"of",numGenes,len(self.results),"relationships found so far"
            for b in xrange(a + 1, numGenes):
                for c in xrange(numGenes):
                    if c not in [a,b]:
                        pc = self.profiles[c]
                        pa = self.profiles[a]
                        pb = self.profiles[b]
                        Uca = pc.U(pa, self.__ilni)
                        Ucb = pc.U(pb, self.__ilni)

                        if Uca < maxUcab and Ucb < maxUcab:
                            for i in range(5):
                                f = self.__fs[i]
                                fab = f(pa, pb)
                                Ifab =  ~ fab  #If is !f
                                # Uc!f is not computed because it == Ucf always.
                                Ucf = pc.U(fab, self.__ilni)

#                                if Ucf > minUcf:
#                                    isf, isIf = 0,0
#                                    hdf = pc.hammingDistance(fab)
#                                    hdIf = pc.hammingDistance(Ifab)
#                                    if hdf > hdIf:isIf = 1
#                                    elif hdf < hdIf:isf = 1
#                                    else:isf,isIf = 1,1
#
#                                    if isf: self.__fillResults(2*i, c, a, b, Ucf, Uca, Ucb)
#                                    if isIf: self.__fillResults(2*i+1, c, a, b, Ucf, Uca, Ucb)


                                #for the new U definition
                                if Ucf > minUcf: self.__fillResults(2*i, c, a, b, Ucf, Uca, Ucb)
                                else:
                                    UcIf = 1 - Ucf
                                    if UcIf > minUcf: self.__fillResults(2*i+1, c, a, b, Ucf, Uca, Ucb)

        return len(self.results) #return false if no triplet is found


    def getLogicTripletsOfSomeGenes(self, min0_1, maxUcab, minUcf,genes):
        """return the number of logic triplets involving specified genes
        satifying the criterion: min0_1, maxUcab, minUcf; And add those
        triplet into self.results.  """
        self.__delGenesWlowH(min0_1)
        numGenes = len(self.profiles)

        for a in xrange(numGenes):
            for b in xrange(a + 1, numGenes):
                for c in xrange(numGenes):
                    if c not in [a,b] and (self.geneIDs[a] in genes or \
                    self.geneIDs[b] in genes or self.geneIDs[c] in genes):
                        pc = self.profiles[c]
                        pa = self.profiles[a]
                        pb = self.profiles[b]
                        Uca = pc.U(pa, self.__ilni)
                        Ucb = pc.U(pb, self.__ilni)

                        if Uca < maxUcab and Ucb < maxUcab:
                            for i in range(5):
                                f = self.__fs[i]
                                fab = f(pa, pb)
                                Ifab =  ~ fab  #If is !f
                                # Uc!f is not computed because it == Ucf always.
                                Ucf = pc.U(fab, self.__ilni)

                                if Ucf > minUcf:
                                    isf, isIf = 0,0
                                    hdf = pc.hammingDistance(fab)
                                    hdIf = pc.hammingDistance(Ifab)
                                    if hdf > hdIf:isIf = 1
                                    elif hdf < hdIf:isf = 1
                                    else:isf,isIf = 1,1

                                    if isf: self.__fillResults(2*i, c, a, b, Ucf, Uca, Ucb)
                                    if isIf: self.__fillResults(2*i+1, c, a, b, Ucf, Uca, Ucb)

        return len(self.results) #return false if no triplet is found


    def bootStrap(self,numTimes,min0_1, maxUcab, minUcf, sortKeys=None):
        """numTimes of random sampling on orgs with replacement,
        each sample size is numOrgs. final result is a list of list
        sortKeys is a list of the following index:
        [typeID, typeName, c, a, b, numOfOccurance, UcfMean, UcaMean, UcbMean, (Ucf-max(Uca,Ucb))Mean, UcfStd, UcaStd, UcbStd, (Ucf-max(Uca,Ucb))Std]
           0         1     2  3  4        5             6       7         8             9                 10       11     12            13"""
        bsResult={} #boot strap results
        while numTimes:
            numTimes-=1
            aSample=self.samplingWReplacement()
            if aSample.getLogicTriplets(min0_1, maxUcab, minUcf) > 0:
                for r in aSample.results:
                    f4=tuple(r[:5])  #first 4 items
                    if f4 in bsResult: bsResult[f4].append(r[5:])
                    else:bsResult[f4]=[r[5:]]

        finalResult=[]
        for k in bsResult:
            f4=list(k)
            Us=zip(*bsResult[k])
            f4.append(len(Us[0]))
            f4.extend(map(np.mean,Us))
            f4.extend(map(np.std,Us))
            finalResult.append(tuple(f4[:])) #convert to a tuple for fast sort

        if sortKeys is not None:
            finalResult=sorted(finalResult, key=operator.itemgetter(*sortKeys), reverse=True)
        
        return finalResult
    
    
    def __getColumProfile(self, colInds=None, aProfile=None, useList=True):
        '''
        given a list of colum index in aProfile, return the profile of those colums
        if useList is True, each profile is a list of 0 and 1, otherwise
        each profile is a BinStr
        '''
        if colInds is None: colInds=range(len(self.orgs))
        if aProfile is None: aProfile=self.profiles
        f1=lambda aBinStr:aBinStr.toList()
        profList=map(f1,aProfile)
        profilesOrg=[[row[i] for row in profList] for i in colInds]
        
        if not useList:
            f=lambda aList:BinStr(''.join(aList))
            profilesOrg=map(f,profilesOrg)
            
        return profilesOrg


    def removeRedundantGeonmes(self,minDistance=5):
        '''
        remove the genomes that are too close to each other.
        distance = hamming.distance *100 / numGenes
        hamming distance is between the profiles of the two genomes

        when the distance between two genomes < minDistance, the
        one with fewer genes are removed. Notice that there is a flaw
        in this method:

        For org a,b,c, if hd(a,b)<5 and b is kept, hd(a,c)<5 and a is kept
        for order [c,a,b], only b is left after this method
        for order [b,a,c], b and c are left after this method
        '''
        numOrgs=len(self.orgs)
        numGenes=len(self.geneIDs)
        profilesOrg=self.__getColumProfile(useList=False)

        removedInds=[] # index of removed orgs
        for i in xrange(numOrgs):
            if i not in removedInds:
                for j in xrange(i+1,numOrgs):
                    if j not in removedInds:
                        pi,pj = profilesOrg[i], profilesOrg[j]
                        hd=pi.hammingDistance(pj)
                        dist = hd*100/numGenes
                        if dist < minDistance:
                            pi.count1_0()
                            pj.count1_0()
                            if pi.num1s >= pj.num1s:
                                removedInds.append(j)
                                print self.orgs[i]+"\t"+str(dist)+"\t"+self.orgs[j]
                            else:
                                removedInds.append(i)
                                print self.orgs[j]+"\t"+str(dist)+"\t"+self.orgs[i]
                                break

        if(len(removedInds)>0):
            removedInds=sorted(removedInds,reverse=True)
            for i in removedInds:
                del(profilesOrg[i])
                del(self.orgs[i])

            cleanProfile=self.__getColumProfile(range(len(self.geneIDs)), profilesOrg, False)
            self.profiles=cleanProfile


    def samplingWReplacement(self):
        """randomly sample the current profile with replacement,
        returns a new profile of the same size"""  
        randInds=[]  #random index
        numOrgs=len(self.orgs)
        for i in xrange(numOrgs):
            randInds.append(random.randint(0,numOrgs-1)) #random Index

        sampleProfile=self.getSamplingProfile(randInds)
        return sampleProfile


    def getSamplingProfile(self, orgIndex):
        """given a list of org index, return a profile
        containing only those orgs. orgIndex starts from 0"""
        randList=self.__getColumProfile(orgIndex)
        randList=np.array(randList).transpose().tolist()
        orgs=[]
        for i in orgIndex:
            orgs.append(self.orgs[i])

        sampleProfile=GeneProfile("sample", orgs)
        sampleProfile.geneIDs=self.geneIDs[:]
        f=lambda aList:BinStr(''.join(aList))
        sampleProfile.profiles=map(f,randList)

        return sampleProfile


    def sortResults(self):
        """sort the results in Result, a 2d list where each cell contains a
        list [typeID, typeName, c, a, b, Ucf, Uca, Ucb, Ucf-max(Uca,Ucb)]
        index   0         1     2  3  4   5    6    7         8"""
        self.results=sorted(self.results, key=operator.itemgetter(8,5,6,7), reverse=True)

    def printResults(self):
        print "typeID\ttypeName\tc\ta\tb\tUcf\tUca\tUcb\tUcf-max(Uca,Ucb)"
        for t in self.results:
            print "%d\t%s\t%s\t%s\t%s\t%.2f\t%.2f\t%.2f\t%.2f" % t


    def writeResultsToFile(self,fileName):
        #with open(fileName, 'w') as oFile:
        oFile = open(fileName, 'w')
        oFile.write("typeID\ttypeName\tc\ta\tb\tUcf\tUca\tUcb\tUcf-max(Uca,Ucb)\n")
        for t in self.results:
            oFile.write("%d\t%s\t%s\t%s\t%s\t%.6f\t%.6f\t%.6f\t%.6f\n" % t)
            #oFile.write("%d\t%s\t%s\t%s\t%s\t%f\t%f\t%f\t%f\n" % t)
        oFile.close()


    def writeBootStrapResultsToFile(self,bootStrapResults,fileName):
        #with open(fileName, 'w') as oFile:
        oFile = open(fileName, 'w')
        oFile.write("typeID\ttypeName\tc\ta\tb\tnumOfOccurance\tUcfMean\tUcaMean\tUcbMean\t(Ucf-max(Uca,Ucb))Mean\tUcfStd\tUcaStd\tUcbStd\t(Ucf-max(Uca,Ucb))Std\n")
        for t in bootStrapResults:
            oFile.write("%d\t%s\t%s\t%s\t%s\t%d\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\n" % t)
        oFile.close()


    def toRandProfile(self, name, numGenes, numOrgs):
        """convert the current profile to random profile with
        given name, number of genes, and number of orgs"""
        tmpF=lambda i:"o"+str(i)
        tmpOrgs=map(tmpF,range(1,numOrgs+1))
        self.__init__(name,tmpOrgs)

        tmpF=lambda i:"g"+str(i)
        self.geneIDs=map(tmpF,range(1,numGenes+1))
        self.profiles=range(numGenes)
        
        for i in range(numGenes):
            prob=random.randint(0,10)/10.0
            tmpBinStr=BinStr()
            tmpBinStr.toRandBinStr(numOrgs,prob)
            self.profiles[i]=tmpBinStr

    
    def writeProfileToFile(self,fileName,delim=" "):
        """Assume the delim is space,output file format is:
        profileName orgName1 orgName2 orgName3 ... 
        geneID1 010...
        geneID2 101..."""
        #with open(fileName, 'w') as oFile:
        oFile = open(fileName, 'w')
        oFile.write(self.name+delim+delim.join(self.orgs)+"\n")
        for i in range(len(self.geneIDs)):
            tmpStr=self.profiles[i].toStr().replace("",delim)
            oFile.write(self.geneIDs[i]+tmpStr+"\n")
        oFile.close()
        
    
    def readProfileFromFile(self,fileName,delimRegExp="\s+"):
        '''Default delimRegExp="\s+".
        Assume the delim is space,input file format is:
        profileName orgName1 orgName2 orgName3 ...
        geneID1 0 1 0 ...
        geneID2 1 0 1 ...'''
        sp=re.compile(delimRegExp)

        #with open(queryFileName, 'r') as iFile: #does not compatible with v2.5
        iFile = open(fileName, 'r')
        lineNum=0
        for line in iFile:
            line=line.strip()
            if line:
                tmpList=sp.split(line)
                lineNum+=1
                if lineNum==1:
                    self.__init__(tmpList[0],tmpList[1:])
                else:
                    self.geneIDs.append(tmpList[0])
                    self.profiles.append(BinStr(''.join(tmpList[1:])))
        iFile.close()


    def readProfileFromRoundupMatrixFile(self,fileName,delimRegExp="\s+"):
        '''Default delimRegExp="\s+".
        Assume the delim is space,input file format is:
        profileName orgName1 orgName2 orgName3 ...
        geneID1 0 1 0 ...
        geneID2 1 0 1 ...'''
        sp=re.compile(delimRegExp)
        sp2=re.compile("\W+")

        #with open(queryFileName, 'r') as iFile: #does not compatible with v2.5
        iFile = open(fileName, 'r')
        lineNum=0
        for line in iFile:
            line=line.strip()
            if line:
                tmpList=sp.split(line)
                lineNum+=1
                if lineNum==1:
                    self.__init__("roundup_output",tmpList[:-1])
                else:
                    self.geneIDs.append("_".join(sp2.split(tmpList[-1])))
                    self.profiles.append(BinStr(''.join(tmpList[:-1])))
        iFile.close()


    def __fillResults(self, fi, c, a, b, Ucf,Uca, Ucb):
        """Add identified functions to the array results
        fi: index in __fs; c: index of gene c in geneIDs;
        Ucf: U(c|f); """
        diffU=Ucf-max([Uca,Ucb])
        self.results.append((self.__functionIDs[fi], \
            self.__functionNames[fi], self.geneIDs[c], \
            self.geneIDs[a], self.geneIDs[b], Ucf, Uca, Ucb, diffU))


    def getGeneProfile(self,geneName):
        '''
        return the profile of a gene
        if contains is true, returns the 1st gene that contains
        the geneName, otherwise returns the 1st gene that equals
        the geneName
        '''
        for i in xrange(len(self.geneIDs)):
            if self.geneIDs[i].find(geneName)>0:
                return self.profiles[i]

        return Null



