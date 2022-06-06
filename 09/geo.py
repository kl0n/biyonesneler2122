import re
import json
import requests
from lxml import etree
from io import StringIO
import pandas as pd 
import re

def entrezNucleotide(accessionList:list, fn:str):
    term = ''
    for a in accessionList:
        term = term + f'{a}[ACCN] OR '
    esearch = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    params = {
            'db': 'nuccore',
            'term': term[:-4],
            'usehistory': 'y'
        }
    r = requests.get(esearch, params)
    print(f'{r.url} ---> {r}')

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
    print(f'{r.url} ---> {r}')
    f = open(fn, 'w')
    f.write(r.content.decode('utf-8'))
    f.close()


def ncbiFT(fn:str) -> dict:
    ncbi = {}
    f = open(fn, 'r')
    acc = ''
    feat = {}
    l = f.readline()
    while l:
        if l.startswith('>Feature'):
            if acc != l.split('|')[1].replace('.', '_'):
                acc = l.split('|')[1].replace('.', '_')
                ncbi[acc] = []
        else:
            cols = l.split('\t')
            if len(cols) == 3:
                if len(feat.keys()) > 0:
                    ncbi[acc].append(feat)
                fstart = int(re.sub('[^0-9]', '', cols[0]))
                fend = int(re.sub('[^0-9]', '', cols[1]))
                if (fend - fstart) > 0:
                    feat = {
                        '_type': cols[2].strip(),
                        '_start': fstart,
                        '_end': fend,
                        '_strand': '+'
                    }
                else:
                    feat = {
                        '_type': cols[2].strip(),
                        '_start': fend,
                        '_end': fstart,
                        '_strand': '-'
                    }
            if len(cols) == 4:
                qkey = cols[3]
                if qkey not in feat:
                    feat[qkey] = [1]
                else:
                    feat[qkey].append(1)
            if len(cols) == 5:
                qkey = cols[3].strip()
                qval = cols[4].strip()
                if qkey not in feat:
                    feat[qkey] = [qval]
                else:
                    feat[qkey].append(qval)
        l = f.readline()
    if len(feat.keys()) > 0:
        ncbi[acc].append(feat)
    js = json.dumps(ncbi, indent=2)
    f = open(f'{fn}.json', 'w')
    f.write(js)
    f.close()
    return ncbi

def uniprot(accessionList:list, rootElement:str, batchSize=200) -> dict:
    up = {rootElement: []}
    for batch in fuzzyReshape(accessionList, batchSize):
        upSearchTerm = ''
        for a in batch:
            upSearchTerm = upSearchTerm + f'id:{a} OR '
        upurl = 'https://www.uniprot.org/uniprot/'
        params = {
            'query': upSearchTerm[:-4],
            'format': 'tab',
            'columns': 'id,genes,go-id,database(refseq)'
        }
        r = requests.get(upurl, params)
        print(r.url, r)
        csv = StringIO(r.text)
        for i,r in pd.read_csv(csv, sep='\t').iterrows():
            entry = {
                'id': str(r['Entry']).strip(),
                'gene_names': str(r['Gene names']).strip().split(),
                'goid': str(r['Gene ontology IDs']).strip().split(';'),
                'refseq': str(r['Cross-reference (refseq)']).strip().split(';')[:-1]
            }
            up[rootElement].append(entry)
    f = open(f'{rootElement}.up.json', 'w')
    f.write(json.dumps(up, indent=2))
    f.close()
    return up


def fuzzyReshape(itemsList:list, batchSize:int) -> list:
    reshaped = []
    for i in range(0, len(itemsList), batchSize):
        j = i + batchSize
        if j > len(itemsList): j = len(itemsList)
        reshaped.append(itemsList[i:j])
    return reshaped


def platflocation(locstr:str) -> dict:
    loclist = []
    if locstr != 'nan':
        # print(locstr)
        loc = locstr.split('///')
        for l in loc:
            id = l.split('(')[0].strip().replace('.', '_')
            start = re.findall('(?<=\().*(?=\.\.)', l)[0]
            end = 0
            strand = '+'
            if 'complement' in l:
                end = re.findall('(?<=\.\.).*(?=\,)', l)[0]
                strand = '-'
            else:
                end = re.findall('(?<=\.\.).*(?=\))', l)[0]
            loclist.append(
                {
                    '_id': id,
                    '_start': start,
                    '_end': end,
                    '_strand': strand
                }
            )
    return loclist
    

def platform(fn:str) -> dict:
    f = open(fn, 'r')
    l = f.readline()
    while('!platform_table_begin' not in l):
        l = f.readline()
    df = pd.read_csv(f, delimiter='\t')
    platfAcc = fn.split('.')[0]
    platf = {platfAcc: []}
    for i,r in df.iterrows():
        entry = {
            'id': str(r['ID']).strip(),
            'gene_symbol': str(r['Gene symbol']).strip().split('///'),
            'orf': str(r['Platform_ORF']).strip(),
            'location': platflocation(str(r['Chromosome annotation']).strip())
        }
        platf[platfAcc].append(entry)
    return platf