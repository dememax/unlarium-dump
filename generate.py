import html, codecs, sqlite3, bisect

N = 100

conn = sqlite3.connect("output.sql", isolation_level=None)

lru_rel_cls2id = dict() # 1-to-1, by definition
id2lru_rel_cls = dict() # 1-to-1, by definition
cls2ids = dict()
lru2ids = dict()
s = conn.execute("select id, lru, rel, cls from unl")
for i in s:
    id = int(i[0])
    lru, rel, cls = i[1], i[2], i[3]
    lru_rel_cls = (lru, rel, cls, )
    id2lru_rel_cls[id] = lru_rel_cls
    lru_rel_cls2id[lru_rel_cls] = id
    if lru not in lru2ids:
        lru2ids[lru] = set()
    lru2ids[lru].add(id)
    if cls not in cls2ids:
        cls2ids[cls] = set()
    cls2ids[cls].add(id)
    if len(lru_rel_cls2id) % 100 == 0:
        print(id, len(lru_rel_cls2id))
s.close()
s = None

src2rel_tgt = dict()
tgt2rel_src = dict()
s = conn.execute("select src, rel, tgt from kb")
for i in s:
    src = int(i[0])
    rel = str(i[1])
    tgt = int(i[2])
    if src not in src2rel_tgt:
        src2rel_tgt[src] = list()
    bisect.insort(src2rel_tgt[src], (rel, id2lru_rel_cls[tgt], tgt, ))
    if tgt not in tgt2rel_src:
        tgt2rel_src[tgt] = list()
    bisect.insort(tgt2rel_src[tgt], (rel, id2lru_rel_cls[src], src, ))
    if len(src2rel_tgt) % 100 == 0:
        print(id, len(src2rel_tgt))
s.close()
s = None

id2lang2pri2lru_ = dict() # _num_fre
lang2lru2num_ = dict() # _id_fre_pri
lru2langs = dict()
s = conn.execute("select lang, lru, num, id, fre, pri from lng")
for i in s:
    lang = str(i[0])
    lru = str(i[1])
    num = int(i[2])
    id = int(i[3])
    fre = int(i[4])
    pri = int(i[5])
    if id not in id2lang2pri2lru_:
        id2lang2pri2lru_[id] = dict()
    if lang not in id2lang2pri2lru_[id]:
        id2lang2pri2lru_[id][lang] = dict()
    if pri not in id2lang2pri2lru_[id][lang]:
        id2lang2pri2lru_[id][lang][pri] = list()
    bisect.insort(id2lang2pri2lru_[id][lang][pri], (lru, num, fre, ))
    if lang not in lang2lru2num_:
        lang2lru2num_[lang] = dict()
    if lru not in lang2lru2num_[lang]:
        lang2lru2num_[lang][lru] = set()
    lang2lru2num_[lang][lru].add((num, id, fre, pri, ))
    if lru not in lru2langs:
        lru2langs[lru] = list()
    if lang not in lru2langs[lru]:
        bisect.insort(lru2langs[lru], lang)
    if len(id2lang2pri2lru_) % 100 == 0:
        print(id, len(id2lang2pri2lru_))
s.close()
s = None

lang_num2name = dict()
def pre_gen4llru(index, ls):
    name = "l" + str(index)
    for i in ls:
        for lang in lru2langs[i]:
            for num, id, fre, pri in lang2lru2num_[lang][i]:
                lang_num2name[(lang, num, )] = name


llrus = list(lru2langs.keys())
llrus.sort()
ld = int((len(llrus) + N -1)/ N)
for i in range(ld):
    r = llrus[N*i:N*(i+1)]
    name = r[0]
    print(name)
    pre_gen4llru(i, r)

def write_head(f, name):
    f.write("""<html>
<head>
<title>""" + html.escape(name) + """</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
</head>
<body>
<p align=center>
    <a href="content.html">Lexical Realisation Units</a> |
    <a href="ids.html">IDs</a> |
    <a href="lrus.html">LRUs</a>
</p>
<hr>
""")

def write_tail(f):
    f.write("""
<hr>
<p align=center><a href="content.html">Lexical Realisation Units</a> | <a href="ids.html">IDs</a></p>
</body>
</html>
""")

id2fname = dict()
lru2fname = dict()
def pre_gen4lru(ls):
    """Generates ``id2fname`` and ``lru2fname`` for ``gen4lru()``."""
    name = ls[0]
    for i in ls:
        lru2fname[i] = name
        for id in lru2ids[i]:
            if id in id2fname:
                raise RuntimeError("id2fname already contains " + str(id) + " (" + str(id2fname[id]) + ", " + str(name) + ")")
            id2fname[id] = name

def gen_title(id):
    res = ''
    if id in id2lang2pri2lru_:
        langs = list(id2lang2pri2lru_[id].keys())
        langs.sort()
        for ll in langs:
            pris = list(id2lang2pri2lru_[id][ll].keys())
            pris.sort()
            for pri in pris:
                if res:
                    res += "; "
                res += ll + ": "
                words = ''
                for lru, num, fre in id2lang2pri2lru_[id][ll][pri]:
                    if words:
                        words += ", "
                    words += lru
                res += words
                break
    if not res:
        return str(id)
    return html.escape(str(id) + ": " + res)

id2link = dict() # cache
def write_link4id(f, id):
    if id not in id2link:
        lru, rel, cls = id2lru_rel_cls[id]
        with_link = id in id2fname
        res = ''
        if with_link:
            res += "<a href='%s.html#%d' title='%s'>" % (html.escape(id2fname[id]), id, gen_title(id))
        else:
            res += str(id) + ": "
        res += html.escape(lru)
        if rel and cls:
            res += html.escape("(" + rel + ">" + cls) + ")"
        if with_link:
            res += "</a>"
        id2link[id] = res
    f.write(id2link[id])

def gen4lru(ls):
    """Generates "name(s) to details" pages where ``ls`` is a range of names.
        Uses ``id2fname`` and ``lru2fname`` generated by ``pre_gen4lru()``.
    """
    name = ls[0]
    f = codecs.open(name + ".html", 'w', "utf-8-sig")
    write_head(f, name + " - " + ls[-1])
    for i in ls:
        f.write("<hr>\n<a name='" + html.escape(i) + "'><h2>" + html.escape(i) + "</h2></a>\n")
        # cls for
        if i in cls2ids:
            f.write("<p>")
            for id in cls2ids[i]:
                write_link4id(f, id)
                f.write(' |\n')
            f.write(" (" + str(len(cls2ids[i])) + ")</p>\n")
        for id in lru2ids[i]:
            lru, rel, cls = id2lru_rel_cls[id]
            f.write("<h3><a name=" + str(id) + ">" + str(id) + "</a>:")
            slru = lru.split()
            if len(slru) == 1:
                f.write(' ' + html.escape(lru))
            else:
                for j in slru:
                    f.write(' ')
                    if j in lru2fname:
                        f.write("<a href='" + html.escape(lru2fname[j] + ".html#" + j) + "'>" + html.escape(j) + "</a>")
                        f.write(" (" + str(len(lru2ids[j])) + ")")
                    else:
                        f.write(html.escape(j) + ' ')
            f.write("</h3>\n")
            # cls here
            if rel and cls:
                f.write("<p>" + html.escape(rel + ">"))
                if cls in lru2fname:
                    f.write("<a href='" + html.escape(lru2fname[cls] + ".html#" + cls) + "'>" + html.escape(cls) + "</a>")
                    f.write(" (" + str(len(lru2ids[cls])) + ")")
                else:
                    f.write(html.escape(cls))
                f.write("</p>\n")
            # UNL Knowledge Base
            f.write("<dl>\n")
            # src
            if id in src2rel_tgt:
                f.write("<dt>src</dt><dd><ol>\n")
                for rel, aaa, tgt in src2rel_tgt[id]:
                    f.write("<li><b>" + html.escape(rel) +  "</b>\n")
                    write_link4id(f, tgt)
                    f.write("</li>\n")
                f.write("</ol></dd>\n")
            # tgt
            if id in tgt2rel_src:
                f.write("<dt>tgt</dt><dd><ol>\n")
                for rel, aaa, src in tgt2rel_src[id]:
                    f.write("<li><b>" + html.escape(rel) +  "</b>\n")
                    write_link4id(f, src)
                    f.write("</li>\n")
                f.write("</ol></dd>\n")
            if id in id2lang2pri2lru_:
                langs = list(id2lang2pri2lru_[id].keys())
                langs.sort()
                is_first = True
                for ll in langs:
                    if is_first:
                        is_first = False
                    else:
                        f.write("</ul></dd>\n")
                    f.write("<dt>" + ll + "</dt><dd><ol>\n")
                    pris = list(id2lang2pri2lru_[id][ll].keys())
                    pris.sort()
                    for pri in pris:
                        for lru, num, fre in id2lang2pri2lru_[id][ll][pri]:
                            f.write("<li><a href='" + html.escape(lang_num2name[(ll, num, )] + ".html#" + ll + "_" + str(num)) + "'>")
                            f.write(html.escape(lru) + "</a> (" + str(fre) + "," + str(pri) + ")</li>\n")
                f.write("</ol></dd>\n")
            s = conn.execute("select fre, pri from unl where id=" + str(id))
            for j in s:
                f.write("<dt>fre</dt><dd><ul>" + str(j[0]) + "</ul></dd>\n")
                f.write("<dt>pri</dt><dd><ul>" + str(j[1]) + "</ul></dd>\n")
            s.close()
            s = None
            f.write("</dl>\n")
    write_tail(f)
    f.close()

lrus = list(lru2ids.keys())
lrus.sort()
d = int((len(lrus) + N -1) / N)
for i in range(d):
    r = lrus[N*i:N*(i+1)]
    name = r[0]
    print(name)
    pre_gen4lru(r)
c = codecs.open("content.html", 'w', "utf-8-sig")
write_head(c, "Content")
for i in range(d):
    r = lrus[N*i:N*(i+1)]
    name = r[0]
    print(name)
    gen4lru(r)
    c.write("<p><a href='" + html.escape(name) + ".html'>" + name + "</a></p>\n")
write_tail(c)
c.close()
c = None

def gen4ids(ls):
    """Generates "id(s) to names" pages where ``ls`` is a range of names.
        Uses ``id2fname`` and ``lru2fname`` generated by ``pre_gen4lru()``.
    """
    name = str(ls[0])
    f = codecs.open(name + ".html", 'w', "utf-8-sig")
    write_head(f, name + " - " + str(ls[-1]))
    f.write("<dl>\n")
    for id in ls:
        sid = str(id)
        f.write("<dt><a name='" + sid + "'>" + sid + "</dt>\n<dd>")
        write_link4id(f, id)
        f.write("</dd>\n")
    f.write("</dl>\n")
    write_tail(f)
    f.close()

ids = list(id2lru_rel_cls.keys())
ids.sort()
d = int(len(ids) / N)
c = codecs.open("ids.html", 'w', "utf-8-sig")
write_head(c, "IDs")
for i in range(d):
    r = ids[N*i:N*(i+1)]
    name = str(r[0])
    print(name)
    gen4ids(r)
    c.write("<p><a href='" + html.escape(name) + ".html'>" + name + "</a></p>\n")
write_tail(c)
c.close()
c = None


def gen4llru(index, ls):
    name = "l" + str(index)
    f = codecs.open(name + ".html", 'w', "utf-8-sig")
    write_head(f, ls[0] + " - " + ls[-1])
    f.write("<dl>\n")
    for i in ls:
        f.write("<dt>" + html.escape(i) + "</dt><dd><dl>\n")
        for lang in lru2langs[i]:
            f.write("<dt>" + html.escape(lang) + "</dt><dd><ol>\n")
            for num, id, fre, pri in lang2lru2num_[lang][i]:
                f.write("<li><a name='" + html.escape(lang + "_" + str(num)) + "'>")
                f.write(str(num) + "</a> (" + str(fre) + "," + str(pri) + "): ")
                write_link4id(f, id)
                f.write("</li>\n")
            f.write("</ol></dd>\n")
        f.write("</dl></dd>\n")
    f.write("</dl>\n")
    write_tail(f)
    f.close()


llrus = list(lru2langs.keys())
llrus.sort()
ld = int(len(llrus) / N)
c = codecs.open("lrus.html", 'w', "utf-8-sig")
write_head(c, "LRUs")
for i in range(ld):
    r = llrus[N*i:N*(i+1)]
    name = r[0]
    print(name)
    gen4llru(i, r)
    c.write("<p><a href='" + html.escape("l" + str(i)) + ".html'>" + html.escape(name) + "</a></p>\n")
write_tail(c)
c.close()
c = None
