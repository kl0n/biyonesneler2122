import sqlite3
import requests
import time
import pandas
from io import StringIO
from lxml import etree
import pandas as pd


class Ftdb(object):

    def __init__(self, dbname:str) -> None:
        self.db = sqlite3.connect(dbname)
        self.dblst = sqlite3.connect(dbname)
        self.dblst.row_factory = lambda cursor, row: row[0]
        cursor = self.db.cursor()
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS "features" (
                "featid"	INTEGER PRIMARY KEY AUTOINCREMENT,
                "acc"       TEXT,
                "startpos"	INTEGER,
                "endpos"	INTEGER,
                "feattype"	TEXT
                )
            '''
        )
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS "qualifiers" (
                "qid"	INTEGER PRIMARY KEY AUTOINCREMENT,
                "qkey"	TEXT,
                "qvalue"	TEXT,
                "featid"	INTEGER,
                FOREIGN KEY("featid") REFERENCES "features"("featid")
                )
            '''
        )
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS "uniprot" (
                "uid"	INTEGER PRIMARY KEY AUTOINCREMENT,
                "acc"	TEXT,
                "ukey"	TEXT,
                "uvalue"	TEXT
                )
            '''
        )


    def queryNCBI(self, acc:list) -> str:
        # build query
        term = ''
        for a in acc:
            term = term + '{0}[ACCN] OR '.format(a)
        print(term[:-4])
        esearch = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
        params = {
            'db': 'nuccore',
            'term': term[:-4],
            'usehistory': 'y'
        }
        r = requests.get(esearch, params)
        print('{0} ---> {1}'.format(r.url, r))
        
        e = etree.fromstring(r.content)
        webEnv = e.findtext('WebEnv')
        queryKey = e.findtext('QueryKey')

        efetch = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        params = {
            'db': 'nuccore',
            'query_key': queryKey,
            'WebEnv': webEnv,
            'rettype': 'ft',
            'retmode': 'text'
        }
        r = requests.get(efetch, params=params)
        print('{0} ---> {1}'.format(r.url, r))
        return r.content.decode('utf-8')

    
    def queryUniProt(self, acclst:list) -> pd.DataFrame:
        # build query 
        term = ''
        for a in acclst:
            term = term + 'id:{0} OR '.format(a)
        upurl = 'https://www.uniprot.org/uniprot/'
        params = {
            'query': term[:-4],
            'format': 'tab',
            'columns': 'id,genes,go'
        }
        r = requests.get(upurl, params)
        print(r.url, r, r.text)
        csv = StringIO(r.text)
        df = pd.read_csv(csv, sep='\t')
        return df

    
    def ftNCBI(self, acclst:list):
        curlst = self.dblst.cursor()
        curlst.execute('select distinct acc from features')
        presentAccLst = curlst.fetchall()
        newAccList = []
        for a in acclst:
            if a not in presentAccLst:
                newAccList.append(a)
        r = self.queryNCBI(newAccList)
        cursor = self.db.cursor()
        acc = ''
        for l in r.split('\n'):
            if l.startswith('>'):
                if acc != l.split('|')[1]:
                    acc = l.split('|')[1]
            else:
                cols = l.split('\t')
                if len(cols[0]) > 0 and len(cols) > 2:  # a new feature
                    cursor.execute(
                        'INSERT INTO features (acc, startpos, endpos, feattype) VALUES (?,?,?,?)',
                        (acc, int(cols[0]), int(cols[1]), cols[2])
                    )
                    featTableRowId = cursor.lastrowid
                    #print(featTableRowId, l)
                else:
                    if len(cols) == 5:
                        cursor.execute(
                            'INSERT INTO qualifiers (qkey, qvalue, featid) VALUES (?,?,?)',
                            (cols[3], cols[4], featTableRowId)
                        )
                    if len(cols) == 4:
                        cursor.execute(
                            'INSERT INTO qualifiers (qkey, featid) VALUES (?,?)',
                            (cols[3], featTableRowId)
                        )
            #print('.', end='')
        self.db.commit()

    
    def ftUniProt(self, acclst, batchSize=250):
        cursor = self.db.cursor()
        curlst = self.dblst.cursor()
        for batch in self.__fuzzyReshape(acclst, batchSize):
            print('Uniprot query batch:')
            print(batch)
            bquery = '('
            for a in batch:
                bquery = bquery + '"{0}",'.format(a)
            bquery = bquery[:-1] + ')'
            cmd = 'select distinct acc from uniprot where acc in {0}'.format(bquery)
            print(cmd)
            curlst.execute(cmd)
            ignorelst = curlst.fetchall()
            print('ignore list:')
            print(ignorelst)
            queryList = []
            for a in batch:
                if a not in ignorelst:
                    if '-' in a:
                        a = a.split('-')[0]
                    queryList.append(a)
            print('q:', queryList)
            if len(queryList) > 0:
                df = self.queryUniProt(queryList)
                for i,r in df.iterrows():
                    entry = str(r['Entry'])
                    gnames = str(r['Gene names']).split(' ')
                    go = str(r['Gene ontology (GO)']).split(';')
                    print(entry, gnames, go)
                    for g in gnames:
                        cursor.execute(
                            'INSERT INTO uniprot (acc, ukey, uvalue) VALUES (?,?,?)',
                            (entry, 'gene_name', g)
                        )
                    for g in go:
                        cursor.execute(
                            'INSERT INTO uniprot (acc, ukey, uvalue) VALUES (?,?,?)',
                            (entry, 'go', g)
                        )
            self.db.commit()


    def __fuzzyReshape(self, a, n):
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