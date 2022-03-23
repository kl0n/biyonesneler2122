import pandas as pd 

class SubsMat(object):

    def __init__(self, filename) -> None:
        self.smdf = pd.read_csv(filename, sep='\s+', comment='#')
        self.smdict = {}
        for k,v in self.smdf.iteritems():
            ssdict = {}
            for i,j in v.iteritems():
                ssdict[i] = j
            self.smdict[k] = ssdict
        print('SubsMat initialized...')
        print(self.smdict)

    def score(self, a, b):
        return self.smdict[a][b]

    def hello():
        print('hello!')

    def __str__(self) -> str:  # overriding
        return self.smdf.to_string()


class SeqIO(object):

    def __init__(self, filename) -> None:
        f = open(filename, 'r')
        self.seqCollection = []
        currentSeq = ''
        seqid = ''
        line = f.readline()
        while line:
            if line.startswith('>'):
                if len(currentSeq) > 0:
                    self.seqCollection.append(Sequence(seqid, currentSeq))
                seqid = line.split(' ')[0]
                seqid = seqid[1:]
                currentSeq = ''
            else:
                if len(seqid) > 0:
                    currentSeq = currentSeq + line.strip()
            line = f.readline()
        if len(currentSeq) > 0:
            self.seqCollection.append(Sequence(seqid, currentSeq))
        
    def seqList(self):
        seqidList = []
        for i in self.seqCollection:
            seqidList.append(i.id)
        return seqidList

    def gets(self, seqId):
        result = ''
        for i in self.seqCollection:
            if i.id == seqId:
                result = i.seq
                break
        return result



class Sequence(object):

    def __init__(self, id:str, seq:str) -> None:
        self.id = id
        self.seq = seq
        print('## Sequence class init active...')

    def __str__(self) -> str:
        return '{0}: {1} letters'.format(self.id, len(self.seq))

    def readFasta(filename):
        pass



class DNA(Sequence):

    def __init__(self, id: str, seq: str) -> None:
        super().__init__(id, seq)
        print('## DNA class init active')

    def __str__(self) -> str:
        return '{0}: {1} bases'.format(self.id, len(self.seq))



class Protein(Sequence):

    def __init__(self, id: str, seq: str) -> None:
        super().__init__(id, seq)