import sqlite3, os

conn = None
ids = set() # all ids of unl; for quick look up

def my_commit():
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint;")
    conn.execute("PRAGMA writable_schema=0;")
    os.sync()


def create_db():
    global conn
    conn = sqlite3.connect("output.sql", isolation_level=None)
    conn.execute('''PRAGMA foreign_keys = ON;''')
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute('''BEGIN;''')
    conn.execute('''CREATE TABLE IF NOT EXISTS unl ( -- UNL Dict
                    lru TEXT NOT NULL, -- Lexical Realisation Unit
                    rel TEXT, -- a Universal Relations used to link the LRU to the CLASSIFIER
                    cls TEXT, -- classifier, a category used to disambiguate and classify the LRU
                    num INTEGER, -- 
                    id INTEGER NOT NULL, -- the index of the concept in the knowledge base
                    fre INTEGER, -- The frequency of NLW in natural texts. 0 (less frequent) to 255 (most frequent)
                    pri INTEGER, -- The priority of the NLW. Used for natural language generation (UNL-NL). It can range from 0 to 255.
                    PRIMARY KEY (id),
                    UNIQUE(lru, rel, cls));''')
    conn.execute('''CREATE TABLE IF NOT EXISTS kb ( -- UNL Knowledge Base
                    rel TEXT NOT NULL, -- the name of one existing UNL relation
                    src INTEGER NOT NULL, -- the source node of the UNL relation
                    tgt INTEGER NOT NULL, -- the target node of the UNL relation
                    PRIMARY KEY (rel, src, tgt),
                    FOREIGN KEY (src) REFERENCES unl (id),
                    FOREIGN KEY (tgt) REFERENCES unl (id));''')
    conn.execute('''CREATE TABLE IF NOT EXISTS lng ( -- Lang Dict
                    lang TEXT NOT NULL, -- The three-character language code according to ISO 639-3
                    lru TEXT NOT NULL, -- Lexical Realisation Unit
                    num INTEGER NOT NULL, -- 
                    id INTEGER NOT NULL, -- the index of the concept in the knowledge base
                    fre INTEGER NOT NULL, -- The frequency of NLW in natural texts. 0 (less frequent) to 255 (most frequent)
                    pri INTEGER NOT NULL, -- The priority of the NLW. Used for natural language generation (UNL-NL). It can range from 0 to 255.
                    PRIMARY KEY (lang, num),
                    FOREIGN KEY (id) REFERENCES unl (id)
                    );''')
    conn.execute("COMMIT;")
    my_commit()


def escp_val(s):
    return s.replace("'", r"''")


def process_unl(unl_name):
    old_ids = len(ids)
    print("Processing", unl_name)
    unl = open(unl_name, "r")
    n = 0
    g = 0
    lex_end = ") <unl,"
    for j in unl:
        n += 1
        i = j.strip()
        if len(i) < 10 or i[0] != "[":
            print("Line", n, "is ignored:", repr(i))
            continue
        if i[-2:] != ">;":
            print("Line", n, "is ignored, bad end:", repr(i))
            continue
        i_lex_start = i.find('"(LEX', 5)
        if i_lex_start < 5:
            print("Line", n, "is ignored, 'LEX' not found:", repr(i))
            continue
        i_lex_end = i.rfind(lex_end, i_lex_start)
        i_fre_pri = i.find(",", i_lex_end+len(lex_end))
        if i_lex_end < i_lex_start or i_fre_pri < i_lex_end:
            print("Line", n, "i_lex_end", i_lex_end, "i_fre_pri", i_fre_pri, "is ignored:", repr(i))
            continue
        fre = 0 if i_lex_end+len(lex_end) == i_fre_pri else int(i[i_lex_end+len(lex_end):i_fre_pri])
        pri = int(i[i_fre_pri+1:-2])
        i_num_id = i.rfind('}"', 1, i_lex_start)
        if i_num_id < 1:
            print("Line", n, "i_num_id", i_num_id, "is ignored:", repr(i))
            continue
        id = int(i[i_num_id+2:i_lex_start])
        i_lru_rel = i.find("(", 1, i_lex_start)
        if i_lru_rel == -1:
            i_cls_num = i.find("]{", 1, i_num_id)
            if i_cls_num < 1:
                print("Line", n, "i_cls_num", i_cls_num, "is ignored:", repr(i))
                continue
            lru = escp_val(i[1:i_cls_num])
            rel = "NULL"
            cls = "NULL"
            num = int(i[i_cls_num+2:i_num_id])
        else:
            i_cls_num = i.find(")]{", i_lru_rel + 2, i_num_id)
            if  i_cls_num < i_lru_rel + 2:
                print("Line", n, "i_cls_num", i_cls_num, "i_lru_rel", i_lru_rel, "i_num_id", i_num_id, "i_lex_start", i_lex_start, "is ignored:", repr(i))
                continue
            i_rel_cls = i.find(">", i_lru_rel, i_cls_num)
            if i_rel_cls < i_lru_rel + 1:
                rel = "'*'"
                cls = "'" + i[i_lru_rel+1:i_cls_num] + "'"
            else:
                rel = "'" + i[i_lru_rel+1:i_rel_cls] + "'"
                cls = "'" + escp_val(i[i_rel_cls+1:i_cls_num]) + "'"
            lru = escp_val(i[1:i_lru_rel])
            num = int(i[i_cls_num+3:i_num_id])
        st = "INSERT INTO unl (lru, rel, cls, num, id, fre, pri) VALUES ('" + lru + "', " + rel + ", " + cls + ", " + str(num) + ", " + str(id) + ", " + str(fre) + ", " + str(pri) + ");"
        try:
            conn.execute(st)
            ids.add(id)
            g += 1
        except sqlite3.OperationalError as e:
            print("Line", n, ", lru = ", lru, ", rel = ", rel, ", cls = ", cls, ", num = ", num, ", id =", id, "failed (" + str(e) + "):", repr(i))
            print(st)
        except sqlite3.IntegrityError as e:
            print("Line", n, ", lru = ", lru, ", rel = ", rel, ", cls = ", cls, ", num = ", num, ", id =", id, "is ignored (" + str(e) + "):", repr(i))
    unl = None
    print(unl_name + " - Total lines:", n, "accepted", g, "ignored", n-g, "new ids", len(ids)-old_ids)
    my_commit()

def add_nonexistent(id, lru, rel, cls, linenum, r):
        st = "INSERT INTO unl (lru, rel, cls, id) VALUES ('" + lru + "', '" + rel + "', '" + cls + "', " + str(id) + ");"
        try:
            conn.execute(st)
            ids.add(id)
        except sqlite3.OperationalError as e:
            print("Line", linenum, ", non-existent lru = ", lru, ", rel = ", rel, ", cls = ", cls, ", id =", id, "failed (" + str(e) + "):", repr(r))
            print(st)
        except sqlite3.IntegrityError as e:
            print("Line", linenum, ", non-existent lru = ", lru, ", rel = ", rel, ", cls = ", cls, ", id =", id, "is ignored (" + str(e) + "):", repr(r))

def process_kb(kb_name):
    old_ids = len(ids)
    print("Processing", kb_name)
    kb = open(kb_name, "r")
    n = 0
    g = 0
    for i in kb:
        n += 1
        s1 = i.find("([[", 1)
        s2 = i.find("]];[[", s1)
        s3 = i.find("]])=1;\n", s2)
        if s1 < 1 or s2 < 2 or s3 < 3:
            print("Line", n, "is ignored:", repr(i))
            continue
        rel = i[:s1]
        src = int(i[s1+3:s2])
        if src not in ids:
            add_nonexistent(src, str(src), '+', 'KB', n, i)
        tgt = int(i[s2+5:s3])
        if tgt not in ids:
            add_nonexistent(tgt, str(tgt), '+', 'KB', n, i)
        try:
            conn.execute("INSERT INTO kb (rel, src, tgt) VALUES ('" +
                    rel + "', " + str(src) + ", " + str(tgt) + ");")
            g += 1
        except sqlite3.IntegrityError as e:
            print("Line", n, ", rel = ", rel, ", src = ", src, ", tgt =", tgt, "is ignored (" + str(e) + "):", repr(i))
    kb = None
    print("Total lines:", n, "accepted", g, "ignored", n-g, "new ids", len(ids)-old_ids)
    my_commit()


def process_lang(lng, fname):
    k = ")<" + lng + ","
    print("Processing", fname, "- lang", lng)
    f = open(fname, "r")
    n = 0
    g = 0
    for j in f:
        n += 1
        i = j.strip()
        if len(i) < 10 or i[0] != "[":
            print("Line", n, "is ignored:", repr(i))
            continue
        if i[-2:] != ">;":
            print("Line", n, ", bad end:", repr(i))
            continue
        s1 = i.find("]{", 1)
        s2 = i.find('}"', s1)
        s3 = i.find('"(LEMMA', s2)
        s4 = i.rfind(k, s3)
        s5 = i.find(",", s4+len(k))
        if s1 < 1 or s2 < 2 or s3 < 3 or s4 < 5:
            print("Line", n, ", s1 =", s1, ", s2 =", s2, ", s3 =", s3, ", s4 =", s4, ", lng =", lng, "is ignored:", repr(i))
            continue
        try:
            lru = escp_val(i[1:s1])
            num = int(i[s1+2:s2])
            id = int(i[s2+2:s3])
            fre = int(i[s4+len(k):s5])
            pri = int(i[s5+1:-2])
        except ValueError as e:
            print("Line", n, ", s1 =", s1, ", s2 =", s2, ", s3 =", s3, "is ignored (" + str(e) + "):", repr(i))
            continue
        if id not in ids:
            add_nonexistent(id, lru, '=', lng, n, i)
        st = "INSERT INTO lng (lang, lru, num, id, fre, pri) VALUES ('" + lng + "', '" + lru + "', " + str(num) + ", " + str(id) + ", " + str(fre) + ", " + str(pri) + ");"
        try:
            conn.execute(st)
            g += 1
        except sqlite3.OperationalError as e:
            print("Line", n, ", lru = ", lru, ", num = ", num, ", id =", id, "failed (" + str(e) + "):", repr(i))
            print(st)
        except sqlite3.IntegrityError as e:
            print("Line", n, ", lru = ", lru, ", num = ", num, ", id =", id, "is ignored (" + str(e) + "):", repr(i))
    unl = None
    print("Total lines:", n, "accepted", g, "ignored", n-g)
    my_commit()


if __name__ == '__main__':
    create_db()
    process_unl("unl-unabridged.txt")
    process_unl("unl-temporary.txt")
    process_kb("unl-KB.txt")
    process_lang("en", "eng-Common_Words-Unabridged-Generative-UCL/en_gen_u_c_ucl_1.txt")
    process_lang("en", "eng-Common_Words-Unabridged-Generative-UCL/en_gen_u_c_ucl_2.txt")
    process_lang("ru", "rus-Common_Words-Unabridged-Generative-UCL/ru_gen_u_c_ucl_1.txt")
    process_lang("fr", "fra-Common_Words-Unabridged-Generative-UCL/fr_gen_u_c_ucl_1.txt")
    process_lang("fr", "fra-Common_Words-Unabridged-Generative-UCL/fr_gen_u_c_ucl_2.txt")
    process_lang("es", "spa-Common_Words-Unabridged-Generative-UCL/es_gen_u_c_ucl_1.txt")
    process_lang("de", "gen-Common_Words-Unabridged-Generative-UCL/de_gen_u_c_ucl_1.txt")
    process_lang("it", "ita-Common_Words-Unabridged-Generative-UCL/it_gen_u_c_ucl_1.txt")

    my_commit()
    conn.close()
