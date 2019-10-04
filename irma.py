import requests
import sqlite3
import sys
import click
from bs4 import BeautifulSoup


def insertCompetitions(db, ids):
    cursor = db.cursor()
    for i in ids:
        print(str(i))
        cursor.execute('''SELECT compId,name FROM competitions WHERE compId=?''', (i["id"],))
        r = cursor.fetchone()
        if r == None:
            cursor.execute('''INSERT INTO competitions(compId, name)
                        VALUES(?,?)''', (i["id"],i["name"]))
    db.commit()



def addEmptyComp(db, id, sarja):
    cursor = db.cursor()
    cursor.execute('''INSERT INTO compResults(compId, class, competitors) VALUES(?,?,?)''', (id, sarja, 0,))
    db.commit()

def addRunnderResult(db, id, name, sarja,place):
    cursor = db.cursor()
    cursor.execute('''INSERT INTO runnerResults(compId, class, runner, place) VALUES(?,?,?,?)''', (id, sarja, name, place,))
    db.commit()

def addCompetitior(db, id, sarja):
    cursor = db.cursor()
    cursor.execute("SELECT competitors FROM compResults WHERE compId=? AND class=?", (id, sarja,))
    r = cursor.fetchone()
    if r == None:
        cursor.execute('''INSERT INTO compResults(compId, class, competitors) VALUES(?,?,?)''', (id, sarja, 1,))
    else:
        cursor.execute('''UPDATE compResults SET competitors=competitors+1 WHERE compId=? AND class=?''', (id, sarja,))
    db.commit()


def getCompetitions(year):
    html = requests.get(base_url +"competitioncalendar/view?year=" + year )
    soup = BeautifulSoup(html.text, "html.parser", from_encoding="utf-8")
    table = soup.find("table", {'class': 'v-table v-mainpage-table'})
    rows = table.find_all("tr")
    ids = list()
    # Get competition IDs
    for row in rows:
        cells = row.find_all("td")
        c = cells[1]
        if cells[2].text.strip() == "Seurat":
            continue
        try:
            val =  {"id": cells[3].text.strip(), "name": c.text.strip(), "club": cells[2].text.strip(), "discipline": cells[4].text.strip()}
            ids.append(val)
        except KeyError:
            print("")
    return ids

def getCompetition(com):
    if isCompProcessed(db, com["id"]):
        print(com["name"] + " processed")
        return
    res_url = base_url + 'competition/results?id=' + com["id"]
    resp = requests.get(res_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    text = soup.get_text()
    found = text.find(CLUB)
    if found == -1:
        addEmptyComp(db,com["id"],"H21")
        try:
            meta = soup.find("meta", {"name" : "header"})
            print(meta["content"] + " 0 starts")
            return
        except Exception:
            return
    table = soup.find_all("table")
    compStarts = 0

    for i in range(0,len(table)):
        t = table[i]
        r =  t.find_all("tr")
        cells = r[0].find_all("td")
        if cells[0].text == "Sarja":
            #Skip first table
            if cells[1].text == "Alue":
                continue
            sarja = cells[1].text.strip()
            comp = table[i+1]
            printSarja = True
            rows =  comp.find_all("tr")
            for r in rows:
                cells = r.find_all("td")
                if cells[0].text == "Sija":
                    continue
                try:
                    if cells[2].text == CLUB:
                        addCompetitior(db, com["id"], sarja)
                        addRunnderResult(db, com["id"], cells[1].text.strip(), sarja, cells[0].text.strip())
                        compStarts += 1
                except IndexError:
                    continue
        else:
            continue

    meta = soup.find("meta", {"name" : "header"})
    print(meta["content"] + " " + str(compStarts) + " starts")


def isCompProcessed(db, id):
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM compResults WHERE compId=?''', (id,))
    row = cursor.fetchone()
    if row == None:
        return False
    return True

def getRegionalResults(db, region, person=False, notLike="", classNotLike=""):
    regional = dict()
    regional["total"] = 0
    regional["results"] = {"1": 0, "2":0, "3":0}
    cursor = db.cursor()
    searchString = '''SELECT compId, name FROM competitions WHERE name LIKE "%{}%" '''
    if len(notLike) > 0:
        for l in notLike:
            searchString +=  ''' and name not like "%{}%"'''.format(l)
    cursor.execute(searchString.format(region))
    res = cursor.fetchall()
    for row in res:
        cursor.execute('''SELECT compId,class,competitors FROM compResults WHERE compId=?''', (row[0],))
        for r in cursor:
            regional["total"] = regional["total"] + r[2]
        cursor.execute('''SELECT place,runner,class FROM runnerResults where compId=?''', (row[0],))
        for r in cursor:
            p = str(r[0])
            try:
                if int(r[0]) < 4:
                    if classNotLike != "":
                        if classNotLike in r[2]:
                            continue
                    regional["results"][p] = regional["results"][p] + 1
                    if person:
                        print("CompId: {} Runner: {} Place: {}", row[0], r[1], r[0])
            except ValueError:
                pass


    return regional
def openDb(dbFile):
    db = sqlite3.connect(dbFile)
    cursor = db.cursor()
    try:
        cursor.execute('''
                       CREATE TABLE competitions(id INTEGER PRIMARY KEY, compId INTEGER, name TEXT, club TEXT, discipline TEXT)
                   ''')
        cursor.execute('''
                       CREATE TABLE compResults(id INTEGER PRIMARY KEY, compId INTEGER, class TEXT, competitors INTEGER)
                   ''')
        cursor.execute('''
                       CREATE TABLE runnerResults(id INTEGER PRIMARY KEY, compId INTEGER, class TEXT, runner TEXT, place INTEGER)
                   ''')
        db.commit()
    except sqlite3.OperationalError as e:
        print("DB exists" + str(e) )
    return db

