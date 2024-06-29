import re
import ast
from nltk.corpus import wordnet
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer

# 使用NLTK的词形还原器
wnLemmatizer = WordNetLemmatizer()

# 正则表达式模式：用于匹配赋值语句的模式
patternVarEqual = re.compile("(\s*[_a-zA-Z][_a-zA-Z0-9]*\s*)(,\s*[_a-zA-Z][_a-zA-Z0-9]*\s*)*=")
# 正则表达式模式：用于匹配for循环语句的模式
patternVarFor = re.compile("for\s+[_a-zA-Z][_a-zA-Z0-9]*\s*(,\s*[_a-zA-Z][_a-zA-Z0-9]*)*\s+in")

# 修复交互式Python代码的输入输出格式
def repairProgramIo(code):
    patternCase1In = re.compile("In ?\[\d+]: ?")    # 输入标志
    patternCase1Out = re.compile("Out ?\[\d+]: ?")  # 输出标志
    patternCase1Cont = re.compile("( )+\.+: ?")     # 续行标志

    patternCase2In = re.compile(">>> ?")            # 输入标志
    patternCase2Cont = re.compile("\.\.\. ?")       # 续行标志

    patterns = [patternCase1In, patternCase1Out, patternCase1Cont,
                patternCase2In, patternCase2Cont]

    lines = code.split("\n")
    linesFlags = [0 for _ in range(len(lines))]

    codeList = []  # 修复后的代码块列表

    # 匹配输入输出标志
    for lineIdx in range(len(lines)):
        line = lines[lineIdx]
        for patternIdx in range(len(patterns)):
            if re.match(patterns[patternIdx], line):
                linesFlags[lineIdx] = patternIdx + 1
                break
    linesFlagsString = "".join(map(str, linesFlags))

    boolRepaired = False

    if linesFlags.count(0) == len(linesFlags):  # 没有需要修复的情况
        repairedCode = code
        codeList = [code]
        boolRepaired = True

    # 根据标志修复代码
    elif re.match(re.compile("(0*1+3*2*0*)+"), linesFlagsString) or \
            re.match(re.compile("(0*4+5*0*)+"), linesFlagsString):
        repairedCode = ""
        preIdx = 0
        subBlock = ""
        if linesFlags[0] == 0:
            flag = 0
            while (flag == 0):
                repairedCode += lines[preIdx] + "\n"
                preIdx += 1
                flag = linesFlags[preIdx]
            subBlock = repairedCode
            codeList.append(subBlock.strip())
            subBlock = ""

        for idx in range(preIdx, len(linesFlags)):
            if linesFlags[idx] != 0:
                repairedCode += re.sub(patterns[linesFlags[idx] - 1], "", lines[idx]) + "\n"

                if len(subBlock.strip()) and (idx > 0 and linesFlags[idx - 1] == 0):
                    codeList.append(subBlock.strip())
                    subBlock = ""
                subBlock += re.sub(patterns[linesFlags[idx] - 1], "", lines[idx]) + "\n"

            else:
                if len(subBlock.strip()) and (idx > 0 and linesFlags[idx - 1] != 0):
                    codeList.append(subBlock.strip())
                    subBlock = ""
                subBlock += lines[idx] + "\n"

        if len(subBlock.strip()):
            codeList.append(subBlock.strip())

        if len(repairedCode.strip()) != 0:
            boolRepaired = True

    if not boolRepaired:  # 如果不是典型情况，则只移除每个Out后的0标志行
        repairedCode = ""
        subBlock = ""
        boolAfterOut = False
        for idx in range(len(linesFlags)):
            if linesFlags[idx] != 0:
                if linesFlags[idx] == 2:
                    boolAfterOut = True
                else:
                    boolAfterOut = False
                repairedCode += re.sub(patterns[linesFlags[idx] - 1], "", lines[idx]) + "\n"

                if len(subBlock.strip()) and (idx > 0 and linesFlags[idx - 1] == 0):
                    codeList.append(subBlock.strip())
                    subBlock = ""
                subBlock += re.sub(patterns[linesFlags[idx] - 1], "", lines[idx]) + "\n"

            else:
                if not boolAfterOut:
                    repairedCode += lines[idx] + "\n"

                if len(subBlock.strip()) and (idx > 0 and linesFlags[idx - 1] != 0):
                    codeList.append(subBlock.strip())
                    subBlock = ""
                subBlock += lines[idx] + "\n"

    return repairedCode, codeList

# 从AST树中获取所有变量名
def getVars(astRoot):
    return sorted(
        {node.id for node in ast.walk(astRoot) if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load)})

# 启发式方法获取代码中的所有变量名
def getVarsHeuristics(code):
    varNames = set()
    codeLines = [_ for _ in code.split("\n") if len(_.strip())]

    start = 0
    end = len(codeLines) - 1
    boolSuccess = False
    # 尝试从代码的起始部分解析AST树
    while not boolSuccess:
        try:
            root = ast.parse("\n".join(codeLines[start:end]))
        except:
            end -= 1
        else:
            boolSuccess = True

    varNames = varNames.union(set(getVars(root)))

    # 处理剩余部分的代码行
    for line in codeLines[end:]:
        line = line.strip()
        try:
            root = ast.parse(line)
        except:
            # 匹配赋值语句的正则表达式模式
            patternVarEqualMatched = re.match(patternVarEqual, line)
            if patternVarEqualMatched:
                match = patternVarEqualMatched.group()[:-1]  # 去掉末尾的"="
                varNames = varNames.union(set([_.strip() for _ in match.split(",")]))

            # 匹配for循环语句的正则表达式模式
            patternVarForMatched = re.search(patternVarFor, line)
            if patternVarForMatched:
                match = patternVarForMatched.group()[3:-2]  # 去掉开头的"for"和结尾的"in"
                varNames = varNames.union(set([_.strip() for _ in match.split(",")]))

        else:
            varNames = varNames.union(getVars(root))

    return varNames

# 解析Python代码，获取词汇标记和处理失败标志
def PythonParser(code):
    boolFailedVar = False
    boolFailedToken = False

    try:
        root = ast.parse(code)
        varNames = set(getVars(root))
    except:
        repairedCode, _ = repairProgramIo(code)
        try:
            root = ast.parse(repairedCode)
            varNames = set(getVars(root))
        except:
            boolFailedVar = True
            varNames = getVarsHeuristics(code)

    tokenizedCode = []

    def firstTrial(_code):
        if len(_code) == 0:
            return True
        try:
            g = tokenize.generate_tokens(StringIO(_code).readline)
            next(g)
        except:
            return False
        else:
            return True

    boolFirstSuccess = firstTrial(code)
    while not boolFirstSuccess:
        code = code[1:]
        boolFirstSuccess = firstTrial(code)

    g = tokenize.generate_tokens(StringIO(code).readline)
    term = next(g)

    boolFinished = False
    while not boolFinished:
        termType = term[0]
        lineno = term[2][0] - 1
        posno = term[3][1] - 1
        if token.tok_name[termType] in {"NUMBER", "STRING", "NEWLINE"}:
            tokenizedCode.append(token.tok_name[termType])
        elif not token.tok_name[termType] in {"COMMENT", "ENDMARKER"} and len(term[1].strip()):
            candidate = term[1].strip()
            if candidate not in varNames:
                tokenizedCode.append(candidate)
            else:
                tokenizedCode.append("VAR")

        boolSuccessNext = False
        while not boolSuccessNext:
            try:
                term = next(g)
            except StopIteration:
                boolFinished = True
                break
            except:
                boolFailedToken = True
                codeLines = code.split("\n")
                if lineno > len(codeLines) - 1:
                    print(sys.exc_info())
                else:
                    failedCodeLine = codeLines[lineno]
                    if posno < len(failedCodeLine) - 1:
                        failedCodeLine = failedCodeLine[posno:]
                        tokenizedFailedCodeLine = wordpunct_tokenize(failedCodeLine)
                        tokenizedCode += tokenizedFailedCodeLine
                    if lineno < len(codeLines) - 1:
                        code = "\n".join(codeLines[lineno + 1:])
                        g = tokenize.generate_tokens(StringIO(code).readline)
                    else:
                        boolFinished = True
                        break
            else:
                boolSuccessNext = True
    return tokenizedCode, boolFailedVar, boolFailedToken

# 将缩写还原为完整形式
def revertAbbrev(line):
    patIs = re.compile("(it|he|she|that|this|there|here)(\"s)", re.I)
    patS1 = re.compile("(?<=[a-zA-Z])\"s")
    patS2 = re.compile("(?<=s)\"s?")
    patNot = re.compile("(?<=[a-zA-Z])n\"t")
    patWould = re.compile("(?<=[a-zA-Z])\"d")
    patWill = re.compile("(?<=[a-zA-Z])\"ll")
    patAm = re.compile("(?<=[I|i])\"m")
    patAre = re.compile("(?<=[a-zA-Z])\"re")
    patVe = re.compile("(?<=[a-zA-Z])\"ve")

    line = patIs.sub(r"\1 is", line)
    line = patS1.sub("", line)
    line = patS2.sub("", line)
    line = patNot.sub(" not", line)
    line = patWould.sub(" would", line)
    line = patWill.sub(" will", line)
    line = patAm.sub(" am", line)
    line = patAre.sub(" are", line)
    line = patVe.sub(" have", line)

    return line

# 获取词性的WordNet常量值
def getWordPos(tag):
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return None


# 句子预处理函数，包括缩写还原、空白符处理、骆驼命名转下划线等
def processNlLine(line):
    line = revertAbbrev(line)  # 缩写还原
    line = re.sub('\t+', '\t', line)  # 处理多个制表符为一个
    line = re.sub('\n+', '\n', line)  # 处理多个换行符为一个
    line = line.replace('\n', ' ')  # 换行符替换为空格
    line = re.sub(' +', ' ', line)  # 多个空格替换为一个空格
    line = line.strip()  # 去除句子两端空格
    line = inflection.underscore(line)  # 骆驼命名转下划线

    # 去除括号内的内容
    space = re.compile(r"\([^(|^)]+\)")
    line = re.sub(space, '', line)
    line = line.strip()  # 再次去除可能出现的首尾空格
    return line

# 句子分词处理函数，包括特定模式的词替换、词性标注、词性还原和词干提取
def processSentWord(line):
    # 找单词
    line = re.findall(r"\w+|[^\s\w]", line)
    line = ' '.join(line)

    # 替换小数
    decimal = re.compile(r"\d+(\.\d+)+")
    line = re.sub(decimal, 'TAGINT', line)

    # 替换字符串
    string = re.compile(r'\"[^\"]+\"')
    line = re.sub(string, 'TAGSTR', line)

    # 替换十六进制
    decimal = re.compile(r"0[xX][A-Fa-f0-9]+")
    line = re.sub(decimal, 'TAGINT', line)

    # 替换数字
    number = re.compile(r"\s?\d+\s?")
    line = re.sub(number, ' TAGINT ', line)

    # 替换字符
    other = re.compile(r"(?<![A-Z|a-z_])\d+[A-Za-z]+")
    line = re.sub(other, 'TAGOER', line)

    cutWords = line.split(' ')
    # 全部小写化
    cutWords = [x.lower() for x in cutWords]

    # 词性标注
    wordTags = posTag(cutWords)
    tagsDict = dict(wordTags)
    wordList = []
    for word in cutWords:
        wordPos = getWordPos(tagsDict[word])
        if wordPos in ['a', 'v', 'n', 'r']:
            # 词性还原
            word = wnler.lemmatize(word, pos=wordPos)
        # 词干提取
        word = wordnet.morphy(word) if wordnet.morphy(word) else word
        wordList.append(word)
    return wordList

# 过滤句子中的非法字符，保留数字、字母、下划线和中横线
def filterAllInvachar(line):
    line = re.sub('[^(0-9|a-zA-Z\-_\'\")\n]+', ' ', line)
    line = re.sub('-+', '-', line)  # 处理多个中横线为一个
    line = re.sub('_+', '_', line)  # 处理多个下划线为一个
    line = line.replace('|', ' ').replace('¦', ' ')  # 替换特定符号为空格
    return line

# 过滤句子中的非法字符，保留数字、字母、下划线和中横线
def filterPartInvachar(line):
    line = re.sub('[^(0-9|a-zA-Z\-_\'\")\n]+', ' ', line)
    line = re.sub('-+', '-', line)
    line = re.sub('_+', '_', line)
    line = line.replace('|', ' ').replace('¦', ' ')
    return line

# Python代码解析主函数，包括代码的过滤、处理和转换成tokens列表
def pythonCodeParse(line):
    line = filterPartInvachar(line)
    line = re.sub('\.+', '.', line)
    line = re.sub('\t+', '\t', line)
    line = re.sub('\n+', '\n', line)
    line = re.sub('>>+', '', line)
    line = re.sub(' +', ' ', line)
    line = line.strip('\n').strip()
    line = re.findall(r"[\w]+|[^\s\w]", line)
    line = ' '.join(line)

    try:
        typedCode, failedVar, failedToken = pythonParser(line)
        typedCode = inflection.underscore(' '.join(typedCode)).split(' ')

        cutTokens = [re.sub("\s+", " ", x.strip()) for x in typedCode]
        tokenList = [x.lower() for x in cutTokens]
        tokenList = [x.strip() for x in tokenList if x.strip() != '']
        return tokenList
    except:
        return '-1000'

# Python查询语句解析主函数，包括查询语句的预处理、分词处理和tokens生成
def pythonQueryParse(line):
    line = filterAllInvachar(line)
    line = processNlLine(line)
    wordList = processSentWord(line)
    for i in range(0, len(wordList)):
        if re.findall('[()]', wordList[i]):
            wordList[i] = ''
    wordList = [x.strip() for x in wordList if x.strip() != '']
    return wordList

# Python上下文语句解析主函数，包括上下文语句的过滤、预处理、分词处理和tokens生成
def pythonContextParse(line):
    line = filterPartInvachar(line)
    line = processNlLine(line)
    wordList = processSentWord(line)
    wordList = [x.strip() for x in wordList if x.strip() != '']
    return wordList

if __name__ == '__main__':
    print(python_query_parse("change row_height and column_width in libreoffice calc use python tagint"))
    print(python_query_parse('What is the standard way to add N seconds to datetime.time in Python?'))
    print(python_query_parse("Convert INT to VARCHAR SQL 11?"))
    print(python_query_parse(
        'python construct a dictionary {0: [0, 0, 0], 1: [0, 0, 1], 2: [0, 0, 2], 3: [0, 0, 3], ...,999: [9, 9, 9]}'))

    print(python_context_parse(
        'How to calculateAnd the value of the sum of squares defined as \n 1^2 + 2^2 + 3^2 + ... +n2 until a user specified sum has been reached sql()'))
    print(python_context_parse('how do i display records (containing specific) information in sql() 11?'))
    print(python_context_parse('Convert INT to VARCHAR SQL 11?'))

    print(python_code_parse(
        'if(dr.HasRows)\n{\n // ....\n}\nelse\n{\n MessageBox.Show("ReservationAnd Number Does Not Exist","Error", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);\n}'))
    print(python_code_parse('root -> 0.0 \n while root_ * root < n: \n root = root + 1 \n print(root * root)'))
    print(python_code_parse('root = 0.0 \n while root * root < n: \n print(root * root) \n root = root + 1'))
    print(python_code_parse('n = 1 \n while n <= 100: \n n = n + 1 \n if n > 10: \n  break print(n)'))
    print(python_code_parse(
        "diayong(2) def sina_download(url, output_dir='.', merge=True, info_only=False, **kwargs):\n    if 'news.sina.com.cn/zxt' in url:\n        sina_zxt(url, output_dir=output_dir, merge=merge, info_only=info_only, **kwargs)\n  return\n\n    vid = match1(url, r'vid=(\\d+)')\n    if vid is None:\n        video_page = get_content(url)\n        vid = hd_vid = match1(video_page, r'hd_vid\\s*:\\s*\\'([^\\']+)\\'')\n  if hd_vid == '0':\n            vids = match1(video_page, r'[^\\w]vid\\s*:\\s*\\'([^\\']+)\\'').split('|')\n            vid = vids[-1]\n\n    if vid is None:\n        vid = match1(video_page, r'vid:\"?(\\d+)\"?')\n    if vid:\n   sina_download_by_vid(vid, output_dir=output_dir, merge=merge, info_only=info_only)\n    else:\n        vkey = match1(video_page, r'vkey\\s*:\\s*\"([^\"]+)\"')\n        if vkey is None:\n            vid = match1(url, r'#(\\d+)')\n            sina_download_by_vid(vid, output_dir=output_dir, merge=merge, info_only=info_only)\n            return\n        title = match1(video_page, r'title\\s*:\\s*\"([^\"]+)\"')\n        sina_download_by_vkey(vkey, title=title, output_dir=output_dir, merge=merge, info_only=info_only)"))

    print(python_code_parse("d = {'x': 1, 'y': 2, 'z': 3} \n for key in d: \n  print (key, 'corresponds to', d[key])"))
    print(python_code_parse(
        '  #       page  hour  count\n # 0     3727441     1   2003\n # 1     3727441     2    654\n # 2     3727441     3   5434\n # 3     3727458     1    326\n # 4     3727458     2   2348\n # 5     3727458     3   4040\n # 6   3727458_1     4    374\n # 7   3727458_1     5   2917\n # 8   3727458_1     6   3937\n # 9     3735634     1   1957\n # 10    3735634     2   2398\n # 11    3735634     3   2812\n # 12    3768433     1    499\n # 13    3768433     2   4924\n # 14    3768433     3   5460\n # 15  3768433_1     4   1710\n # 16  3768433_1     5   3877\n # 17  3768433_1     6   1912\n # 18  3768433_2     7   1367\n # 19  3768433_2     8   1626\n # 20  3768433_2     9   4750\n'))