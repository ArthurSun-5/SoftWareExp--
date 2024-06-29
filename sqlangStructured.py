import re
import sqlparse # 引入sqlparse模块用于SQL解析
import inflection # 引入inflection模块用于单词格式转换
from nltk import pos_tag # 引入nltk中的pos_tag用于词性标注
from nltk.stem import WordNetLemmatizer # 引入WordNetLemmatizer用于词形还原
wnler = WordNetLemmatizer() # 初始化WordNetLemmatizer
from nltk.corpus import wordnet # 引入nltk中的wordnet

# 定义常量，各种token类型
OTHER = 0
FUNCTION = 1
BLANK = 2
KEYWORD = 3
INTERNAL = 4
TABLE = 5
COLUMN = 6
INTEGER = 7
FLOAT = 8
HEX = 9
STRING = 10
WILDCARD = 11
SUBQUERY = 12
DUD = 13

# token类型对应的名称
tTypes = {0: "OTHER", 1: "FUNCTION", 2: "BLANK", 3: "KEYWORD", 4: "INTERNAL", 5: "TABLE", 6: "COLUMN", 7: "INTEGER",
          8: "FLOAT", 9: "HEX", 10: "STRING", 11: "WILDCARD", 12: "SUBQUERY", 13: "DUD", }

# 定义正则表达式的扫描器，用于将字符串分解为tokens
scanner = re.Scanner([(r"\[[^\]]*\]", lambda scanner, token: token), (r"\+", lambda scanner, token: "REGPLU"),
                      (r"\*", lambda scanner, token: "REGAST"), (r"%", lambda scanner, token: "REGCOL"),
                      (r"\^", lambda scanner, token: "REGSTA"), (r"\$", lambda scanner, token: "REGEND"),
                      (r"\?", lambda scanner, token: "REGQUE"),
                      (r"[\.~``;_a-zA-Z0-9\s=:\{\}\-\\]+", lambda scanner, token: "REFRE"),
                      (r'.', lambda scanner, token: None), ])


# 将字符串s使用scanner进行tokenize
def tokenizeRegex(s):
    results = scanner.scan(s)[0]
    return results

# SQL语言解析器类
class SqlangParser():
    # 静态方法，用于对输入的SQL语句进行清理和规范化
    @staticmethod
    def sanitizeSql(sql):
        s = sql.strip().lower() # 去除首尾空格并转换为小写
        if not s[-1] == ";":
            s += ';' # 如果末尾没有分号，则添加分号
        s = re.sub(r'\(', r' ( ', s) # 在左括号前后添加空格
        s = re.sub(r'\)', r' ) ', s) # 在右括号前后添加空格
        words = ['index', 'table', 'day', 'year', 'user', 'text']
        for word in words:
            s = re.sub(r'([^\w])' + word + '$', r'\1' + word + '1', s)
            s = re.sub(r'([^\w])' + word + r'([^\w])', r'\1' + word + '1' + r'\2', s)
        s = s.replace('#', '') # 去除字符串中的#
        return s

    # 解析字符串类型的token
    def parseStrings(self, tok):
        if isinstance(tok, sqlparse.sql.TokenList):
            for c in tok.tokens:
                self.parseStrings(c)
        elif tok.ttype == STRING:
            if self.regex:
                tok.value = ' '.join(tokenizeRegex(tok.value))
            else:
                tok.value = "CODSTR"

    # 重命名标识符
    def renameIdentifiers(self, tok):
        if isinstance(tok, sqlparse.sql.TokenList):
            for c in tok.tokens:
                self.renameIdentifiers(c)
        elif tok.ttype == COLUMN:
            if str(tok) not in self.idMap["COLUMN"]:
                colname = "col" + str(self.idCount["COLUMN"])
                self.idMap["COLUMN"][str(tok)] = colname
                self.idMapInv[colname] = str(tok)
                self.idCount["COLUMN"] += 1
            tok.value = self.idMap["COLUMN"][str(tok)]
        elif tok.ttype == TABLE:
            if str(tok) not in self.idMap["TABLE"]:
                tabname = "tab" + str(self.idCount["TABLE"])
                self.idMap["TABLE"][str(tok)] = tabname
                self.idMapInv[tabname] = str(tok)
                self.idCount["TABLE"] += 1
            tok.value = self.idMap["TABLE"][str(tok)]

        elif tok.ttype == FLOAT:
            tok.value = "CODFLO"
        elif tok.ttype == INTEGER:
            tok.value = "CODINT"
        elif tok.ttype == HEX:
            tok.value = "CODHEX"

    # 计算哈希值
    def __hash__(self):
        return hash(tuple([str(x) for x in self.tokensWithBlanks]))

    # 初始化函数，对输入的SQL语句进行解析和标记
    def __init__(self, sql, regex=False, rename=True):

        self.sql = SqlangParser.sanitizeSql(sql) # 清理和规范化SQL语句

        self.idMap = {"COLUMN": {}, "TABLE": {}} # 初始化标识符映射表和计数器
        self.idMapInv = {}
        self.idCount = {"COLUMN": 0, "TABLE": 0}
        self.regex = regex

        self.parseTreeSentinel = False
        self.tableStack = []

        self.parse = sqlparse.parse(self.sql) # 使用sqlparse对SQL语句进行解析
        self.parse = [self.parse[0]]

        self.removeWhitespaces(self.parse[0]) # 移除token中的空白token
        self.identifyLiterals(self.parse[0]) # 标识token中的字面量
        self.parse[0].ptype = SUBQUERY
        self.identifySubQueries(self.parse[0]) # 标识子查询
        self.identifyFunctions(self.parse[0]) # 标识函数
        self.identifyTables(self.parse[0]) # 标识表格

        self.parseStrings(self.parse[0]) # 解析字符串类型的token

        if rename:
            self.renameIdentifiers(self.parse[0]) # 重命名标识符

        self.tokens = SqlangParser.getTokens(self.parse) # 获取所有token

    # 获取所有token
    @staticmethod
    def getTokens(parse):
        flatParse = []
        for expr in parse:
            for token in expr.flatten():
                if token.ttype == STRING:
                    flatParse.extend(str(token).split(' '))
                else:
                    flatParse.append(str(token))
        return flatParse

    # 移除token中的空白token
    def removeWhitespaces(self, tok):
        if isinstance(tok, sqlparse.sql.TokenList):
            tmpChildren = []
            for c in tok.tokens:
                if not c.is_whitespace:
                    tmpChildren.append(c)

            tok.tokens = tmpChildren
            for c in tok.tokens:
                self.removeWhitespaces(c)

    # 标识子查询
    def identifySubQueries(self, tokenList):
        isSubQuery = False

        for tok in tokenList.tokens:
            if isinstance(tok, sqlparse.sql.TokenList):
                subQuery = self.identifySubQueries(tok)
                if (subQuery and isinstance(tok, sqlparse.sql.Parenthesis)):
                    tok.ttype = SUBQUERY
            elif str(tok) == "select":
                isSubQuery = True
        return isSubQuery

        # 标识文本中的字面量
        def identifyLiterals(self, tokenList):
            # 定义空白标记和标识符类型
            blankTokens = [tokens.Name, tokens.Name.Placeholder]
            blankTokenTypes = [sql.Identifier]

            for tok in tokenList.tokens:
                if isinstance(tok, sql.TokenList):
                    tok.ptype = INTERNAL
                    self.identifyLiterals(tok)
                elif (tok.ttype == tokens.Keyword or str(tok) == "select"):
                    tok.ttype = KEYWORD
                elif (tok.ttype == tokens.Number.Integer or tok.ttype == tokens.Literal.Number.Integer):
                    tok.ttype = INTEGER
                elif (tok.ttype == tokens.Number.Hexadecimal or tok.ttype == tokens.Literal.Number.Hexadecimal):
                    tok.ttype = HEX
                elif (tok.ttype == tokens.Number.Float or tok.ttype == tokens.Literal.Number.Float):
                    tok.ttype = FLOAT
                elif (
                        tok.ttype == tokens.String.Symbol or tok.ttype == tokens.String.Single or tok.ttype == tokens.Literal.String.Single or tok.ttype == tokens.Literal.String.Symbol):
                    tok.ttype = STRING
                elif (tok.ttype == tokens.Wildcard):
                    tok.ttype = WILDCARD
                elif (tok.ttype in blankTokens or isinstance(tok, blankTokenTypes[0])):
                    tok.ttype = COLUMN

        # 标识函数
        def identifyFunctions(self, tokenList):
            for tok in tokenList.tokens:
                if (isinstance(tok, sql.Function)):
                    self.parseTreeSentinel = True
                elif (isinstance(tok, sql.Parenthesis)):
                    self.parseTreeSentinel = False
                if self.parseTreeSentinel:
                    tok.ttype = FUNCTION
                if isinstance(tok, sql.TokenList):
                    self.identifyFunctions(tok)

        # 标识表
        def identifyTables(self, tokenList):
            if tokenList.ptype == SUBQUERY:
                self.tableStack.append(False)

            for i in range(len(tokenList.tokens)):
                prevtok = tokenList.tokens[i - 1]
                tok = tokenList.tokens[i]

                if (str(tok) == "." and tok.ttype == tokens.Punctuation and prevtok.ttype == COLUMN):
                    prevtok.ttype = TABLE
                elif (str(tok) == "from" and tok.ttype == tokens.Keyword):
                    self.tableStack[-1] = True
                elif ((str(tok) == "where" or str(tok) == "on" or str(tok) == "group" or str(tok) == "order" or str(
                        tok) == "union") and tok.ttype == tokens.Keyword):
                    self.tableStack[-1] = False

                if isinstance(tok, sql.TokenList):
                    self.identifyTables(tok)
                elif (tok.ttype == COLUMN):
                    if self.tableStack[-1]:
                        tok.ttype = TABLE

            if tokenList.ptype == SUBQUERY:
                self.tableStack.pop()

        def __str__(self):
            return ' '.join([str(tok) for tok in self.tokens])

        def parseSql(self):
            return [str(tok) for tok in self.tokens]

    # 缩略词处理函数
    def revert_abbrev(line):
        pat_is = re.compile("(it|he|she|that|this|there|here)(\"s)", re.I)
        pat_s1 = re.compile("(?<=[a-zA-Z])\"s")
        pat_s2 = re.compile("(?<=s)\"s?")
        pat_not = re.compile("(?<=[a-zA-Z])n\"t")
        pat_would = re.compile("(?<=[a-zA-Z])\"d")
        pat_will = re.compile("(?<=[a-zA-Z])\"ll")
        pat_am = re.compile("(?<=[I|i])\"m")
        pat_are = re.compile("(?<=[a-zA-Z])\"re")
        pat_ve = re.compile("(?<=[a-zA-Z])\"ve")

        line = pat_is.sub(r"\1 is", line)
        line = pat_s1.sub("", line)
        line = pat_s2.sub("", line)
        line = pat_not.sub(" not", line)
        line = pat_would.sub(" would", line)
        line = pat_will.sub(" will", line)
        line = pat_am.sub(" am", line)
        line = pat_are.sub(" are", line)
        line = pat_ve.sub(" have", line)

        return line

    # 获取词性函数
    def get_wordpos(tag):
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

    # 处理自然语言句子的函数
    def process_nl_line(line):
        line = revert_abbrev(line)
        line = re.sub('\t+', '\t', line)
        line = re.sub('\n+', '\n', line)
        line = line.replace('\n', ' ')
        line = line.replace('\t', ' ')
        line = re.sub(' +', ' ', line)
        line = line.strip()
        line = inflection.underscore(line)

        space = re.compile(r"\([^\(|^\)]+\)")
        line = re.sub(space, '', line)
        line = line.strip()
        return line

    # 分词函数
    def process_sent_word(line):
        line = re.findall(r"[\w]+|[^\s\w]", line)
        line = ' '.join(line)

        decimal = re.compile(r"\d+(\.\d+)+")
        line = re.sub(decimal, 'TAGINT', line)

        string = re.compile(r'\"[^\"]+\"')
        line = re.sub(string, 'TAGSTR', line)

        decimal = re.compile(r"0[xX][A-Fa-f0-9]+")
        line = re.sub(decimal, 'TAGINT', line)

        number = re.compile(r"\s?\d+\s?")
        line = re.sub(number, ' TAGINT ', line)

        other = re.compile(r"(?<![A-Z|a-z|_|])\d+[A-Za-z]+")
        line = re.sub(other, 'TAGOER', line)

        cut_words = line.split(' ')
        cut_words = [x.lower() for x in cut_words]
        word_tags = pos_tag(cut_words)
        tags_dict = dict(word_tags)
        word_list = []
        for word in cut_words:
            word_pos = get_wordpos(tags_dict[word])
            if word_pos in ['a', 'v', 'n', 'r']:
                word = wnler.lemmatize(word, pos=word_pos)
            word = wordnet.morphy(word) if wordnet.morphy(word) else word
            word_list.append(word)
        return word_list

    # 过滤所有无效字符函数
    def filter_all_invachar(line):
        line = re.sub('[^(0-9|a-z|A-Z|\-|_|\'|\"|\-|\(|\)|\n)]+', ' ', line)
        line = re.sub('-+', '-', line)
        line = re.sub('_+', '_', line)
        line = line.replace('|', ' ').replace('¦', ' ')
        return line

    # 过滤部分无效字符函数
    def filter_part_invachar(line):
        line = re.sub('[^(0-9|a-z|A-Z|\-|#|/|_|,|\'|=|>|<|\"|\-|\\|\(|\)|\?|\.|\*|\+|\[|\]|\^|\{|\}|\n)]+', ' ', line)
        line = re.sub('-+', '-', line)
        line = re.sub('_+', '_', line)
        line = line.replace('|', ' ').replace('¦', ' ')
        return line
# 处理包含SQL代码的输入字符串，将其转换为一个标准化的token列表
def sqlang_code_parse(line):
    line = filter_part_invachar(line)  # 过滤非常用符号
    line = re.sub('\.+', '.', line)    # 多个点替换为单个点
    line = re.sub('\t+', '\t', line)   # 多个制表符替换为单个制表符
    line = re.sub('\n+', '\n', line)   # 多个换行符替换为单个换行符
    line = re.sub(' +', ' ', line)     # 多个空格替换为单个空格

    line = re.sub('>>+', '', line)     # 删除多个连续的>>
    line = re.sub(r"\d+(\.\d+)+",'number',line)  # 替换小数为特殊标记"number"

    line = line.strip('\n').strip()    # 去除开头和结尾的换行符和空格
    line = re.findall(r"[\w]+|[^\s\w]", line)  # 分词
    line = ' '.join(line)              # 重新组合成字符串

    try:
        query = SqlangParser(line, regex=True)  # 使用SqlangParser解析字符串
        typedCode = query.parseSql()     # 解析SQL语句
        typedCode = typedCode[:-1]       # 去除最后一个元素
        # 骆驼命名转下划线
        typedCode = inflection.underscore(' '.join(typedCode)).split(' ')  # 骆驼命名转下划线分割为列表

        cut_tokens = [re.sub("\s+", " ", x.strip()) for x in typedCode]  # 去除多余空格
        # 全部小写化
        token_list = [x.lower() for x in cut_tokens]  # 转为小写
        # 列表里包含 '' 和' '
        token_list = [x.strip() for x in token_list if x.strip() != '']  # 去除空字符串
        # 返回列表
        return token_list  # 返回处理后的token列表
    # 存在为空的情况，词向量要进行判断
    except:
        return '-1000'  # 解析失败返回'-1000'

# 将输入的句子进行预处理和分词，返回一个标准化的单词列表
def sqlang_query_parse(line):
    line = filter_all_invachar(line)  # 过滤非常用符号
    line = process_nl_line(line)      # 处理句子的预处理
    word_list = process_sent_word(line)  # 处理句子的分词
    # 分完词后,再去掉 括号
    for i in range(0, len(word_list)):
        if re.findall('[\(\)]', word_list[i]):
            word_list[i] = ''
    # 列表里包含 '' 或 ' '
    word_list = [x.strip() for x in word_list if x.strip() != '']  # 去除空字符串
    # 解析可能为空

    return word_list  # 返回处理后的单词列表

# 处理包含上下文信息的输入字符串，将其预处理并分词，返回一个标准化的单词列表
def sqlang_context_parse(line):
    line = filter_part_invachar(line)  # 过滤非常用符号
    line = process_nl_line(line)       # 处理句子的预处理
    word_list = process_sent_word(line)  # 处理句子的分词
    # 列表里包含 '' 或 ' '
    word_list = [x.strip() for x in word_list if x.strip() != '']  # 去除空字符串
    # 解析可能为空
    return word_list  # 返回处理后的单词列表


if __name__ == '__main__':
    print(sqlang_code_parse('""geometry": {"type": "Polygon" , 111.676,"coordinates": [[[6.69245274714546, 51.1326962505233], [6.69242714158622, 51.1326908883821], [6.69242919794447, 51.1326955158344], [6.69244041615532, 51.1326998744549], [6.69244125953742, 51.1327001609189], [6.69245274714546, 51.1326962505233]]]} How to 123 create a (SQL  Server function) to "join" multiple rows from a subquery into a single delimited field?'))
    print(sqlang_query_parse("change row_height and column_width in libreoffice calc use python tagint"))
    print(sqlang_query_parse('MySQL Administrator Backups: "Compatibility Mode", What Exactly is this doing?'))
    print(sqlang_code_parse('>UPDATE Table1 \n SET Table1.col1 = Table2.col1 \n Table1.col2 = Table2.col2 FROM \n Table2 WHERE \n Table1.id =  Table2.id'))
    print(sqlang_code_parse("SELECT\n@supplyFee:= 0\n@demandFee := 0\n@charedFee := 0\n"))
    print(sqlang_code_parse('@prev_sn := SerialNumber,\n@prev_toner := Remain_Toner_Black\n'))
    print(sqlang_code_parse(' ;WITH QtyCTE AS (\n  SELECT  [Category] = c.category_name\n          , [RootID] = c.category_id\n          , [ChildID] = c.category_id\n  FROM    Categories c\n  UNION ALL \n  SELECT  cte.Category\n          , cte.RootID\n          , c.category_id\n  FROM    QtyCTE cte\n          INNER JOIN Categories c ON c.father_id = cte.ChildID\n)\nSELECT  cte.RootID\n        , cte.Category\n        , COUNT(s.sales_id)\nFROM    QtyCTE cte\n        INNER JOIN Sales s ON s.category_id = cte.ChildID\nGROUP BY cte.RootID, cte.Category\nORDER BY cte.RootID\n'))
    print(sqlang_code_parse("DECLARE @Table TABLE (ID INT, Code NVARCHAR(50), RequiredID INT);\n\nINSERT INTO @Table (ID, Code, RequiredID)   VALUES\n    (1, 'Physics', NULL),\n    (2, 'Advanced Physics', 1),\n    (3, 'Nuke', 2),\n    (4, 'Health', NULL);    \n\nDECLARE @DefaultSeed TABLE (ID INT, Code NVARCHAR(50), RequiredID INT);\n\nWITH hierarchy \nAS (\n    --anchor\n    SELECT  t.ID , t.Code , t.RequiredID\n    FROM @Table AS t\n    WHERE t.RequiredID IS NULL\n\n    UNION ALL   \n\n    --recursive\n    SELECT  t.ID \n          , t.Code \n          , h.ID        \n    FROM hierarchy AS h\n        JOIN @Table AS t \n            ON t.RequiredID = h.ID\n    )\n\nINSERT INTO @DefaultSeed (ID, Code, RequiredID)\nSELECT  ID \n        , Code \n        , RequiredID\nFROM hierarchy\nOPTION (MAXRECURSION 10)\n\n\nDECLARE @NewSeed TABLE (ID INT IDENTITY(10, 1), Code NVARCHAR(50), RequiredID INT)\n\nDeclare @MapIds Table (aOldID int,aNewID int)\n\n;MERGE INTO @NewSeed AS TargetTable\nUsing @DefaultSeed as Source on 1=0\nWHEN NOT MATCHED then\n Insert (Code,RequiredID)\n Values\n (Source.Code,Source.RequiredID)\nOUTPUT Source.ID ,inserted.ID into @MapIds;\n\n\nUpdate @NewSeed Set RequiredID=aNewID\nfrom @MapIds\nWhere RequiredID=aOldID\n\n\n/*\n--@NewSeed should read like the following...\n[ID]  [Code]           [RequiredID]\n10....Physics..........NULL\n11....Health...........NULL\n12....AdvancedPhysics..10\n13....Nuke.............12\n*/\n\nSELECT *\nFROM @NewSeed\n"))