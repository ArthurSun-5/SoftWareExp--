import pickle

# 获取两个语料库中所有的词汇集合
def GetVocab(corpus1, corpus2):
    word_vocab = set()
    for corpus in [corpus1, corpus2]:
        for i in range(len(corpus)):
            word_vocab.update(corpus[i][1][0])
            word_vocab.update(corpus[i][1][1])
            word_vocab.update(corpus[i][2][0])
            word_vocab.update(corpus[i][3])
    print(len(word_vocab))
    return word_vocab

# 加载pickle文件
def LoadPickle(filename):
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data


# 处理词汇的相关操作，包括加载文件、获取词汇集合、保存结果
def VocabProcessing(filepath1, filepath2, save_path):
    with open(filepath1, 'r') as f:
        total_data1 = set(eval(f.read()))
    with open(filepath2, 'r') as f:
        total_data2 = eval(f.read())

    word_set = GetVocab(total_data1, total_data2)

    excluded_words = total_data1.intersection(word_set)
    word_set = word_set - excluded_words

    print(len(total_data1))
    print(len(word_set))

    with open(save_path, 'w') as f:
        f.write(str(word_set))


if __name__ == "__main__":
    python_hnn = './data/python_hnn_data_teacher.txt'
    python_staqc = './data/staqc/python_staqc_data.txt'
    python_word_dict = './data/word_dict/python_word_vocab_dict.txt'

    sql_hnn = './data/sql_hnn_data_teacher.txt'
    sql_staqc = './data/staqc/sql_staqc_data.txt'
    sql_word_dict = './data/word_dict/sql_word_vocab_dict.txt'

    new_sql_staqc = './ulabel_data/staqc/sql_staqc_unlabled_data.txt'
    new_sql_large = './ulabel_data/large_corpus/multiple/sql_large_multiple_unlable.txt'
    large_word_dict_sql = './ulabel_data/sql_word_dict.txt'

    VocabProcessing(sql_word_dict, new_sql_large, large_word_dict_sql)
