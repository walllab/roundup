


# orthData: a tuple of params, orthologs.
# params: a tuple of query genome, subject genome, divergence, and evalue.
# orthologs: a list of query id, subject id, and distance.

#########################################
# ORTHDATAS SERIALIZATION AND PERSISTANCE
#########################################


class OrthData(object):

    def __init__(self, params, orthologs):
        self.params = params
        self.orthologs = orthologs


def orthDatasFromFile(path):
    return [orthData for orthData in orthDatasFromFileGen(path)]


def orthDatasFromFileGen(path):
    '''
    path: contains zero or more orthDatas.  must exist.
    yields: every orthData, a pair of params and orthologs, in path.
    '''
    with open(path) as fh:
        for line in fh:
            if line.startswith('PA'):
                lineType, qdb, sdb, div, evalue = line.strip().split('\t')
                orthologs = []
            elif line.startswith('OR'):
                lineType, qid, sid, dist = line.strip().split('\t')                        
                orthologs.append((qid, sid, dist))
            elif line.startswith('//'):
                yield ((qdb, sdb, div, evalue), orthologs)


def orthDatasFromFilesGen(paths):
    '''
    paths: a list of file paths containing orthDatas.
    yields: every orthData in every file in paths
    '''
    for path in paths:
        for orthData in orthDatasFromFile(path):
            yield orthData


def orthDatasToFile(orthDatas, path, mode='w'):
    '''
    orthDatas: a list of rsd orthDatas. orthData is a pair of params and orthologs
    path: where to save the orthDatas
    mode: change to 'a' to append to an existing file
    serializes orthDatas and persists them to path
    Inspired by the Uniprot dat files, a set of orthologs starts with a params row, then has 0 or more ortholog rows, then has an end row.
    Easy to parse.  Can represent a set of parameters with no orthologs.
    Example:
    PA\tLACJO\tYEAS7\t0.2\t1e-15
    OR\tQ74IU0\tA6ZM40\t1.7016
    OR\tQ74K17\tA6ZKK5\t0.8215
    //
    PA      MYCGE   MYCHP   0.2     1e-15
    //
    '''
    with open(path, mode) as fh:
        for (qdb, sdb, div, evalue), orthologs in orthDatas:
            fh.write('PA\t{}\t{}\t{}\t{}\n'.format(qdb, sdb, div, evalue))
            for ortholog in orthologs:
                fh.write('OR\t{}\t{}\t{}\n'.format(*ortholog))
            fh.write('//\n')
    
                    
