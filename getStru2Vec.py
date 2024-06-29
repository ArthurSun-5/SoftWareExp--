import pickle
import multiprocessing
from pythonStructured import *
from sqlangStructured import *


# 多进程处理Python查询
def multiproPythonQuery(dataList):
    return [pythonQueryParse(line) for line in dataList]


# 多进程处理Python代码
def multiproPythonCode(dataList):
    return [pythonCodeParse(line) for line in dataList]


# 多进程处理Python上下文
def multiproPythonContext(dataList):
    result = []
    for line in dataList:
        if line == '-10000':
            result.append(['-10000'])
        else:
            result.append(pythonContextParse(line))
    return result


# 多进程处理SQL查询
def multiproSqlangQuery(dataList):
    return [sqlangQueryParse(line) for line in dataList]


# 多进程处理SQL代码
def multiproSqlangCode(dataList):
    return [sqlangCodeParse(line) for line in dataList]


# 多进程处理SQL上下文
def multiproSqlangContext(dataList):
    result = []
    for line in dataList:
        if line == '-10000':
            result.append(['-10000'])
        else:
            result.append(sqlangContextParse(line))
    return result


# 使用多进程解析数据
def parse(dataList, splitNum, contextFunc, queryFunc, codeFunc):
    pool = multiprocessing.Pool()
    splitList = [dataList[i:i + splitNum] for i in range(0, len(dataList), splitNum)]

    # 处理上下文
    results = pool.map(contextFunc, splitList)
    contextData = [item for sublist in results for item in sublist]
    print(f'上下文条数：{len(contextData)}')

    # 处理查询
    results = pool.map(queryFunc, splitList)
    queryData = [item for sublist in results for item in sublist]
    print(f'查询条数：{len(queryData)}')

    # 处理代码
    results = pool.map(codeFunc, splitList)
    codeData = [item for sublist in results for item in sublist]
    print(f'代码条数：{len(codeData)}')

    pool.close()
    pool.join()

    return contextData, queryData, codeData


# 主函数，用于处理不同语言类型的语料
def main(langType, splitNum, sourcePath, savePath, contextFunc, queryFunc, codeFunc):
    with open(sourcePath, 'rb') as f:
        corpusList = pickle.load(f)

    contextData, queryData, codeData = parse(corpusList, splitNum, contextFunc, queryFunc, codeFunc)
    qids = [item[0] for item in corpusList]

    totalData = [[qids[i], contextData[i], codeData[i], queryData[i]] for i in range(len(qids))]

    with open(savePath, 'wb') as f:
        pickle.dump(totalData, f)


if __name__ == '__main__':
    staqcPythonPath = './ulabel_data/python_staqc_qid2index_blocks_unlabeled.txt'
    staqcPythonSave = '../hnn_process/ulabel_data/staqc/python_staqc_unlabled_data.pkl'

    staqcSqlPath = './ulabel_data/sql_staqc_qid2index_blocks_unlabeled.txt'
    staqcSqlSave = './ulabel_data/staqc/sql_staqc_unlabled_data.pkl'

    # 处理Staqc Python语料
    main('python', 1000, staqcPythonPath, staqcPythonSave, multiproPythonContext, multiproPythonQuery,
         multiproPythonCode)

    # 处理Staqc SQL语料
    main('sql', 1000, staqcSqlPath, staqcSqlSave, multiproSqlangContext, multiproSqlangQuery, multiproSqlangCode)

    largePythonPath = './ulabel_data/large_corpus/multiple/python_large_multiple.pickle'
    largePythonSave = '../hnn_process/ulabel_data/large_corpus/multiple/python_large_multiple_unlable.pkl'

    largeSqlPath = './ulabel_data/large_corpus/multiple/sql_large_multiple.pickle'
    largeSqlSave = './ulabel_data/large_corpus/multiple/sql_large_multiple_unlable.pkl'

    # 处理大型Python语料
    main('python', 1000, largePythonPath, largePythonSave, multiproPythonContext, multiproPythonQuery,
         multiproPythonCode)

    # 处理大型SQL语料
    main('sql', 1000, largeSqlPath, largeSqlSave, multiproSqlangContext, multiproSqlangQuery, multiproSqlangCode)
