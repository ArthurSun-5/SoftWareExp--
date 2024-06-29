import pickle
from collections import Counter

# 加载pickle文件
def loadPickle(filename):
    with open(filename, 'rb') as f:
        data = pickle.load(f, encoding='iso-8859-1')
    return data

# 根据qids将数据拆分为single和multiple
def splitData(totalData, qids):
    result = Counter(qids)
    totalDataSingle = []
    totalDataMultiple = []
    for data in totalData:
        if result[data[0][0]] == 1:
            totalDataSingle.append(data)
        else:
            totalDataMultiple.append(data)
    return totalDataSingle, totalDataMultiple

# 处理staqc数据并保存
def dataStaqcProcessing(filepath, saveSinglePath, saveMultiplePath):
    with open(filepath, 'r') as f:
        totalData = eval(f.read())
    qids = [data[0][0] for data in totalData]
    totalDataSingle, totalDataMultiple = splitData(totalData, qids)

    with open(saveSinglePath, "w") as f:
        f.write(str(totalDataSingle))
    with open(saveMultiplePath, "w") as f:
        f.write(str(totalDataMultiple))

# 处理large数据并保存
def dataLargeProcessing(filepath, saveSinglePath, saveMultiplePath):
    totalData = loadPickle(filepath)
    qids = [data[0][0] for data in totalData]
    totalDataSingle, totalDataMultiple = splitData(totalData, qids)

    with open(saveSinglePath, 'wb') as f:
        pickle.dump(totalDataSingle, f)
    with open(saveMultiplePath, 'wb') as f:
        pickle.dump(totalDataMultiple, f)

# 将单标签未标注数据转为已标注
def singleUnlabeledToLabeled(inputPath, outputPath):
    totalData = loadPickle(inputPath)
    labels = [[data[0], 1] for data in totalData]
    totalDataSort = sorted(labels, key=lambda x: (x[0], x[1]))
    with open(outputPath, "w") as f:
        f.write(str(totalDataSort))

if __name__ == "__main__":
    # 处理staqc Python数据
    staqcPythonPath = './ulabel_data/python_staqc_qid2index_blocks_unlabeled.txt'
    staqcPythonSingleSave = './ulabel_data/staqc/single/python_staqc_single.txt'
    staqcPythonMultipleSave = './ulabel_data/staqc/multiple/python_staqc_multiple.txt'
    dataStaqcProcessing(staqcPythonPath, staqcPythonSingleSave, staqcPythonMultipleSave)

    # 处理staqc SQL数据
    staqcSqlPath = './ulabel_data/sql_staqc_qid2index_blocks_unlabeled.txt'
    staqcSqlSingleSave = './ulabel_data/staqc/single/sql_staqc_single.txt'
    staqcSqlMultipleSave = './ulabel_data/staqc/multiple/sql_staqc_multiple.txt'
    dataStaqcProcessing(staqcSqlPath, staqcSqlSingleSave, staqcSqlMultipleSave)

    # 处理large Python数据
    largePythonPath = './ulabel_data/python_codedb_qid2index_blocks_unlabeled.pickle'
    largePythonSingleSave = './ulabel_data/large_corpus/single/python_large_single.pickle'
    largePythonMultipleSave = './ulabel_data/large_corpus/multiple/python_large_multiple.pickle'
    dataLargeProcessing(largePythonPath, largePythonSingleSave, largePythonMultipleSave)

    # 处理large SQL数据
    largeSqlPath = './ulabel_data/sql_codedb_qid2index_blocks_unlabeled.pickle'
    largeSqlSingleSave = './ulabel_data/large_corpus/single/sql_large_single.pickle'
    largeSqlMultipleSave = './ulabel_data/large_corpus/multiple/sql_large_multiple.pickle'
    dataLargeProcessing(largeSqlPath, largeSqlSingleSave, largeSqlMultipleSave)

    # 将单标签未标注数据转为已标注
    largeSqlSingleLabelSave = './ulabel_data/large_corpus/single/sql_large_single_label.txt'
    largePythonSingleLabelSave = './ulabel_data/large_corpus/single/python_large_single_label.txt'
    singleUnlabeledToLabeled(largeSqlSingleSave, largeSqlSingleLabelSave)
    singleUnlabeledToLabeled(largePythonSingleSave, largePythonSingleLabelSave)
