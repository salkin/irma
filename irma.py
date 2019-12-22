import requests
import sqlite3
import sys
import click
import os
import logging
from bs4 import BeautifulSoup

log = logging.getLogger("irma")
base_url = "https://irma.suunnistusliitto.fi/irma/public/"
dbDir = os.environ["DB_DIR"]
CLUB="Falken"

class Irma:

    def __init__(self, year):
        dbFile=dbDir + "/res"+year +".db"
        self.openDb(dbFile)
        self.year = year
        self.club = "Falken"
        self.collectAll = True

    def __del__(self):
        self.db.close()

    def insertCompetitions(self, ids):
        cursor = self.db.cursor()
        for i in ids:
            log.info(str(i))
            cursor.execute('''SELECT compId,name,club FROM competitions WHERE compId=?''', (i["id"],))
            r = cursor.fetchone()
            if r == None:
                cursor.execute('''INSERT INTO competitions(compId, name, club)
                            VALUES(?,?)''', (i["id"],i["name"]))
            else:
                cursor.execute('''UPDATE competitions SET club=? WHERE compId=?''', (i["club"],i["id"]))
        self.db.commit()

    def getCompetitior(self, name):
        pass

    def printCompetitions(self):
        cursor = self.db.cursor()
        cursor.execute('''SELECT id,name FROM competitions''')
        rows = cursor.fetchall()
        for r in rows:
            log.info(str(r[0])),
            log.info(" " + r[1])

    def getStarts(self):
        cursor = self.db.cursor()
        totalStarts=0
        classes = dict()
        cursor.execute('''SELECT class, competitors FROM compResults''')
        rows = cursor.fetchall()
        for r in rows:
            try:
                classes[r[0][:3]] += r[1]
            except KeyError:
                classes[r[0][:3]] = r[1]
        return classes


    def printStarts(self):
        cursor = self.db.cursor()
        totalStarts=0
        classes = dict()
        cursor.execute('''SELECT class, competitors FROM compResults''')
        rows = cursor.fetchall()
        for r in rows:
            try:
                classes[r[0][:3]] += r[1]
            except KeyError:
                classes[r[0][:3]] = r[1]

            totalStarts = totalStarts + r[1]
        log.info("TotalStarts: " + str(totalStarts))
        log.info("Class starts:")
        log.info("<table>")
        log.info("<tr>")
        cells = 0
        for k,v in sorted(classes.items()):
            print("<td> " + k + " " + str(v) + " </td>")
            if cells == 3:
                print("</tr>")
                print("<tr>")
                cells=0
            cells+=1
        log.info("</tr>")
        log.info("</table>")

    def getRunners(self, club=CLUB):
        cursor = self.db.cursor()
        cursor.execute('''SELECT DISTINCT runner FROM runnerResults WHERE club=?''', (club,))
        results = list()
        rows = cursor.fetchall()
        for r in rows:
            log.debug(r)
            results.append(r[0])
        results.sort()
        return results

    def addEmptyComp(self, id, sarja):
        cursor = self.db.cursor()
        cursor.execute('''INSERT INTO compResults(compId, class, competitors) VALUES(?,?,?)''', (id, sarja, 0,))
        self.db.commit()

    def addRunnderResult(self, id, name, sarja,place, club):
        cursor = self.db.cursor()
        cursor.execute('''INSERT INTO runnerResults(compId, class, runner, club, place) VALUES(?,?,?,?,?)''', (id, sarja, name, club, place,))
        self.db.commit()

    def getRunnerResults(self, name):
        cursor = self.db.cursor()
        results = dict()
        cursor.execute('''SELECT compId, place, class FROM runnerResults WHERE runner=?''', (name,))
        rows = cursor.fetchall()
        for r in rows:
            n = cursor.execute('''SELECT name,club FROM competitions WHERE compId=?''', (str(r[0]),))
            com = n.fetchone()
            if com != None:
                results[com[0]] = {"class": r[2], "place": r[1], "arrangingClub": com[1]}
        return results


    def addCompetitior(self, id, sarja):
        cursor = self.db.cursor()
        cursor.execute("SELECT competitors FROM compResults WHERE compId=? AND class=?", (id, sarja,))
        r = cursor.fetchone()
        if r == None:
            cursor.execute('''INSERT INTO compResults(compId, class, competitors) VALUES(?,?,?)''', (id, sarja, 1,))
        else:
            cursor.execute('''UPDATE compResults SET competitors=competitors+1 WHERE compId=? AND class=?''', (id, sarja,))
        self.db.commit()


    def getCompetitions(self):
        html = requests.get(base_url +"competitioncalendar/view?year=" + self.year )
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

    def getCompetition(self, com):
        if self.isCompProcessed( com["id"]):
            log.info(com["name"] + " processed")
            return
        res_url = base_url + 'competition/results?id=' + com["id"]
        resp = requests.get(res_url)
        soup = BeautifulSoup(resp.content, "html.parser")
        text = soup.get_text()
        found = text.find(self.club)
        if found == -1 and not self.collectAll:
            self.addEmptyComp(com["id"],"H21")
            try:
                meta = soup.find("meta", {"name" : "header"})
                log.info(meta["content"] + " 0 starts")
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
                        if cells[2].text == self.club or self.collectAll:
                            self.addCompetitior( com["id"], sarja )
                            self.addRunnderResult( com["id"], cells[1].text.strip(), sarja, cells[0].text.strip(), cells[2].text.strip())
                            compStarts += 1
                    except IndexError:
                        continue
            else:
                continue

        meta = soup.find("meta", {"name" : "header"})
        log.info(meta["content"] + " " + str(compStarts) + " starts")


    def isCompProcessed(self, id):
        cursor = self.db.cursor()
        cursor.execute('''SELECT * FROM compResults WHERE compId=?''', (id,))
        row = cursor.fetchone()
        if row == None:
            return False
        return True

    def getRegionalResults(self, region, person=False, notLike="", classNotLike=""):
        regional = dict()
        regional["total"] = 0
        regional["results"] = {"1": 0, "2":0, "3":0}
        cursor = self.db.cursor()
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
                            log.info("CompId: {} Runner: {} Place: {}", row[0], r[1], r[0])
                except ValueError:
                    pass
        return regional

    def openDb(self, dbFile):
        self.db = sqlite3.connect(dbFile)
        cursor = self.db.cursor()
        try:
            cursor.execute('''
                           CREATE TABLE competitions(id INTEGER PRIMARY KEY, compId INTEGER, name TEXT, club TEXT, discipline TEXT)
                       ''')
            cursor.execute('''
                           CREATE TABLE compResults(id INTEGER PRIMARY KEY, compId INTEGER, class TEXT, competitors INTEGER)
                       ''')
            cursor.execute('''
                           CREATE TABLE runnerResults(id INTEGER PRIMARY KEY, compId INTEGER, class TEXT, runner TEXT, club TEXT, place INTEGER)
                       ''')
            self.db.commit()
        except sqlite3.OperationalError as e:
            log.info("DB exists" + str(e) )
