import pickle
import numpy as np
from gensim.models import KeyedVectors

# 将词向量文件保存为二进制文件
def transBin(inputPath, outputPath):
    # 加载词向量文件
    wvFromText = KeyedVectors.load_word2vec_format(inputPath, binary=False)
    # 初始化词向量
    wvFromText.init_sims(replace=True)
    # 保存为二进制文件
    wvFromText.save(outputPath)

# 构建新的词典和词向量矩阵
def createWordVectors(vectorPath, wordPath, outputVectorPath, outputDictPath):
    # 加载词向量模型
    model = KeyedVectors.load(vectorPath, mmap='r')

    # 加载词汇表
    with open(wordPath, 'r') as f:
        words = eval(f.read())

    # 初始化词典和特殊标记
    wordList = ['PAD', 'SOS', 'EOS', 'UNK']
    failedWords = []

    rng = np.random.RandomState(None)
    padEmbedding = np.zeros(300)
    unkEmbedding = rng.uniform(-0.25, 0.25, 300)
    sosEmbedding = rng.uniform(-0.25, 0.25, 300)
    eosEmbedding = rng.uniform(-0.25, 0.25, 300)
    wordVectors = [padEmbedding, sosEmbedding, eosEmbedding, unkEmbedding]

    # 构建词向量和词典
    for word in words:
        try:
            wordVectors.append(model.wv[word])
            wordList.append(word)
        except KeyError:
            failedWords.append(word)

    # 转换为数组
    wordVectors = np.array(wordVectors)
    wordDict = {word: idx for idx, word in enumerate(wordList)}

    # 保存词向量和词典
    with open(outputVectorPath, 'wb') as file:
        pickle.dump(wordVectors, file)

    with open(outputDictPath, 'wb') as file:
        pickle.dump(wordDict, file)

    print("词向量和词典构建完成")

# 获取词在词典中的索引
def getIndex(dataType, text, wordDict):
    indices = []
    if dataType == 'code':
        indices.append(1)  # 添加起始标记
        if len(text) + 1 < 350:
            if len(text) == 1 and text[0] == '-1000':
                indices.append(2)  # 添加结束标记
            else:
                for word in text:
                    indices.append(wordDict.get(word, wordDict['UNK']))
                indices.append(2)  # 添加结束标记
        else:
            for word in text[:348]:
                indices.append(wordDict.get(word, wordDict['UNK']))
            indices.append(2)  # 添加结束标记
    else:
        if len(text) == 0 or text[0] == '-10000':
            indices.append(0)  # 添加填充标记
        else:
            for word in text:
                indices.append(wordDict.get(word, wordDict['UNK']))
    return indices

# 序列化训练、测试、验证语料
def serializeCorpus(wordDictPath, corpusPath, outputPath):
    # 加载词典
    with open(wordDictPath, 'rb') as f:
        wordDict = pickle.load(f)

    # 加载语料
    with open(corpusPath, 'r') as f:
        corpus = eval(f.read())

    serializedData = []

    # 序列化每条数据
    for entry in corpus:
        qid = entry[0]
        siWordList = getIndex('text', entry[1][0], wordDict)
        si1WordList = getIndex('text', entry[1][1], wordDict)
        tokenizedCode = getIndex('code', entry[2][0], wordDict)
        queryWordList = getIndex('text', entry[3], wordDict)
        blockLength = 4
        label = 0

        # 填充或截断至固定长度
        siWordList = siWordList[:100] + [0] * (100 - len(siWordList))
        si1WordList = si1WordList[:100] + [0] * (100 - len(si1WordList))
        tokenizedCode = tokenizedCode[:350] + [0] * (350 - len(tokenizedCode))
        queryWordList = queryWordList[:25] + [0] * (25 - len(queryWordList))

        # 组织序列化后的数据
        serializedEntry = [qid, [siWordList, si1WordList], [tokenizedCode], queryWordList, blockLength, label]
        serializedData.append(serializedEntry)

    # 保存序列化数据
    with open(outputPath, 'wb') as file:
        pickle.dump(serializedData, file)

    print("语料序列化完成")

if __name__ == '__main__':
    # 词向量文件路径
    pythonBinPath = '../hnn_process/embeddings/10_10/python_struc2vec.bin'
    sqlBinPath = '../hnn_process/embeddings/10_8_embeddings/sql_struc2vec.bin'

    # 最初基于Staqc的词典和词向量路径
    pythonWordPath = '../hnn_process/data/word_dict/python_word_vocab_dict.txt'
    pythonWordVecPath = '../hnn_process/embeddings/python/python_word_vocab_final.pkl'
    pythonWordDictPath = '../hnn_process/embeddings/python/python_word_dict_final.pkl'

    sqlWordPath = '../hnn_process/data/word_dict/sql_word_vocab_dict.txt'
    sqlWordVecPath = '../hnn_process/embeddings/sql/sql_word_vocab_final.pkl'
    sqlWordDictPath = '../hnn_process/embeddings/sql/sql_word_dict_final.pkl'

    # 创建词典和词向量矩阵
    # createWordVectors(pythonBinPath, pythonWordPath, pythonWordVecPath, pythonWordDictPath)
    # createWordVectors(sqlBinPath, sqlWordPath, sqlWordVecPath, sqlWordDictPath)

    # SQL待处理语料地址
    newSqlStaqc = '../hnn_process/ulabel_data/staqc/sql_staqc_unlabled_data.txt'
    newSqlLarge = '../hnn_process/ulabel_data/large_corpus/multiple/sql_large_multiple_unlable.txt'
    largeWordDictSql = '../hnn_process/ulabel_data/sql_word_dict.txt'

    # SQL最后的词典和对应的词向量
    sqlFinalWordVecPath = '../hnn_process/ulabel_data/large_corpus/sql_word_vocab_final.pkl'
    sqlFinalWordDictPath = '../hnn_process/ulabel_data/large_corpus/sql_word_dict_final.pkl'

    # 序列化SQL语料
    staqcSqlSerialized = '../hnn_process/ulabel_data/staqc/seri_sql_staqc_unlabled_data.pkl'
    largeSqlSerialized = '../hnn_process/ulabel_data/large_corpus/multiple/seri_sql_large_multiple_unlable.pkl'
    # serializeCorpus(sqlFinalWordDictPath, newSqlStaqc, staqcSqlSerialized)
    # serializeCorpus(sqlFinalWordDictPath, newSqlLarge, largeSqlSerialized)

    # Python待处理语料地址
    newPythonStaqc = '../hnn_process/ulabel_data/staqc/python_staqc_unlabled_data.txt'
    newPythonLarge = '../hnn_process/ulabel_data/large_corpus/multiple/python_large_multiple_unlable.txt'
    finalWordDictPython = '../hnn_process/ulabel_data/python_word_dict.txt'

    # Python最后的词典和对应的词向量
    pythonFinalWordVecPath = '../hnn_process/ulabel_data/large_corpus/python_word_vocab_final.pkl'
    pythonFinalWordDictPath = '../hnn_process/ulabel_data/large_corpus/python_word_dict_final.pkl'

    # 序列化Python语料
    staqcPythonSerialized = '../hnn_process/ulabel_data/staqc/seri_python_staqc_unlabled_data.pkl'
    largePythonSerialized = '../hnn_process/ulabel_data/large_corpus/multiple/seri_python_large_multiple_unlable.pkl'
    # serializeCorpus(pythonFinalWordDictPath, newPythonStaqc, staqcPythonSerialized)
    serializeCorpus(pythonFinalWordDictPath, newPythonLarge, largePythonSerialized)

    print('所有任务完成')
