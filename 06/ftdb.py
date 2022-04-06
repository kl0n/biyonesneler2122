from os import curdir
import readline
import sqlite3
from io import StringIO
import pandas as pd 
import time
import requests

class Ftdb(object):

    def __init__(self, dbname:str) -> None:
        self.db = sqlite3.connect(dbname)
        cursor = self.db.cursor()
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS "features" (
                "featid"	INTEGER PRIMARY KEY AUTOINCREMENT,
                "acc"       TEXT,
                "startpos"	INTEGER,
                "endpos"	INTEGER,
                "feattype"	TEXT
                )
            ''')
        cursor.execute(
        '''CREATE TABLE IF NOT EXISTS "qualifiers" (
            "qid"	INTEGER PRIMARY KEY AUTOINCREMENT,
            "qkey"	TEXT,
            "qvalue"	TEXT,
            "featid"	INTEGER,
            FOREIGN KEY("featid") REFERENCES "features"("featid")
            )
        ''')

    def readFT(self, fn:str):
        f = open(fn, 'r')
        cursor = self.db.cursor()
        acc = ''
        upaccdict = {}
        featTableRowId = 0
        line = f.readline()
        while(line):
            if line.startswith('>'):
                if acc != line.split('|')[1]:
                    acc = line.split('|')[1]
            else:
                cols = line.split('\t')
                if len(cols[0]) > 0 and len(cols) > 2:
                    cursor.execute(
                        'INSERT INTO features (acc, startpos, endpos, feattype) VALUES (?,?,?,?)',
                        (acc, cols[0], cols[1], cols[2])
                    )
                    featTableRowId = cursor.lastrowid
                    print(featTableRowId, line)
                else:
                    if len(cols) == 5:
                        cursor.execute(
                            'INSERT INTO qualifiers (qkey, qvalue, featid) VALUES (?,?,?)',
                            (cols[3], cols[4], featTableRowId)
                        )
                        if cols[4].startswith('UniProtKB'):
                            upacc = cols[4].strip().split(':')[1]
                            if not upacc in upaccdict:
                                upaccdict[upacc] = [featTableRowId]
                            else:
                                upaccdict[upacc].append(featTableRowId)
                    if len(cols) == 4:
                        cursor.execute(
                            'INSERT INTO qualifiers (qkey, featid) VALUES (?,?)',
                            (cols[3], featTableRowId)
                        )
                    print('---->', line)
            line = f.readline()
        self.db.commit()
        return upaccdict

    def queryUniProt(self, upaccdict:dict, batchSize=20):
        upurl = 'https://www.uniprot.org/uniprot/'
        for batchQueryAccL in self.__fuzzyReshape(upaccdict.keys(), batchSize):
            query = ''
            for acc in batchQueryAccL:
                query = query + 'id:{0} OR '.format(acc)
                # id:P00561 OR id:P00547 OR id:P00934 OR 
            params = {
                'query': query[:-4],
                'format': 'tab',
                'columns': 'id,genes,go'
            }
            r = requests.get(upurl, params)
            print('\n\n')
            csv = StringIO(r.text)
            df = pd.read_csv(csv, sep='\t')
            print(df)
            time.sleep(5)


    def __fuzzyReshape(self, a:list, n:int):
        c = 0
        batch = []
        result = []
        for i in a:
            batch.append(i)
            c += 1
            if c>= n:
                result.append(batch)
                batch = []
                c = 0
        if len(batch) > 0:
            result.append(batch)
        return result