import requests
import sqlite3
import sys
import click
import os
import logging
from bs4 import BeautifulSoup

log = logging.getLogger("irma")
base_url = "https://irma.suunnistusliitto.fi/irma/public"
dbDir = os.environ["DB_DIR"]
CLUB="Falken"

class Irma:

    def __init__(self, year):
        dbFile=dbDir + "/res"+year +".db"
        self.dbFile=dbFile
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
                            VALUES(?,?,?)''', (i["id"],i["name"],i["club"],))
            else:
                cursor.execute('''UPDATE competitions SET club=? WHERE compId=?''', (i["club"],i["id"],))
        self.db.commit()

    def insertClub(self, i):
        cursor = self.db.cursor()
        cursor.execute('''SELECT name FROM clubs WHERE short=?''', (i["short_name"],))
        r = cursor.fetchone()
        if r == None:
            cursor.execute('''INSERT INTO clubs(name, short, region)
                        VALUES(?,?,?)''', (i["name"],i["short_name"],i["region"],))
        else:
            cursor.execute('''UPDATE clubs SET region=? WHERE name=?''', (i["region"],i["name"]))
        self.db.commit()

    def getClubs(self, region="FSO"):
        cursor = self.db.cursor()
        cursor.execute('''SELECT name, short, region FROM clubs WHERE region=?''', (region,))
        rows = cursor.fetchall()
        clubs = list()
        for r in rows:
            clubs.append({"name": r[0], "short": r[1]})
        return clubs


    def getStarts(self, club=CLUB):
        cursor = self.db.cursor()
        totalStarts=0
        classes = dict()
        cursor.execute('''SELECT class FROM runnerResults WHERE club=?''', (club,))
        rows = cursor.fetchall()
        for r in rows:
            try:
                classes[r[0][:3]] += 1
            except KeyError:
                classes[r[0][:3]] = 1
            totalStarts = totalStarts + 1
        return totalStarts, classes


    def getRunners(self, club=CLUB):
        cursor = self.db.cursor()
        cursor.execute('''SELECT DISTINCT runner, class FROM runnerResults WHERE club=?''', (club,))
        results = list()
        run = dict()
        rows = cursor.fetchall()
        for r in rows:
            log.debug(r)
            results.append(r[0])
            cl = r[1].lstrip()
            if len(r[1]) > 3:
               cl = cl[0:3]
            try:
                if r[0] in run[cl]["runners"]:
                    continue
                run[cl]["total"] += 1
                run[cl]["runners"][r[0]] = "exists"
            except:
                run[cl] = dict()
                run[cl]["total"] = 1
                run[cl]["runners"] = dict()
        results = list(dict.fromkeys(results))
        results.sort()
        return results, run

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
                results[com[0]] = {"class": r[2], "place": r[1], "arrangingClub": com[1], "compId": r[0]}
            m = cursor.execute('''SELECT COUNT(runner) FROM runnerResults WHERE compId=? AND class=?''', (str(r[0]), str(r[2]),))
            tot = n.fetchone()
            if tot != None:
                results[com[0]]["total"] = tot[0]
        return results

    def getCompetitionClass(self,compId, year, cl):
        cursor = self.db.cursor()
        results = list()
        cursor.execute('''SELECT runner, place FROM runnerResults WHERE compId=? AND class=? ORDER BY place''', (compId,cl,))
        rows = cursor.fetchall()
        for r in rows:
            results.append({"name": r[0], "place": r[1]})
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
        html = requests.get(base_url +"/competitioncalendar/view?year=" + self.year )
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
        res_url = base_url + '/competition/results?id=' + com["id"]
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

    def getRegionalResults(self, region,club=CLUB, person=False, notLike="", classNotLike=""):
        regional = dict()
        regional["total"] = 0
        regional["results"] = dict()
        for i in range(1,4):
            regional["results"][str(1)] = 0
        cursor = self.db.cursor()
        searchString = '''SELECT compId, name FROM competitions WHERE name LIKE "%{}%" '''
        if len(notLike) > 0:
            for l in notLike:
                searchString +=  ''' and name not like "%{}%"'''.format(l)
        cursor.execute(searchString.format(region))
        res = cursor.fetchall()
        for row in res:
            cursor.execute('''SELECT place,runner,class FROM runnerResults WHERE compId=? AND club=?''', (row[0],club,))
            for r in cursor:
                regional["total"] += 1
                p = str(r[0])
                try:
                    if int(r[0]) < 4:
                        if classNotLike != "":
                            if classNotLike in r[2]:
                                continue
                        if not p in  regional["results"].keys():
                            regional["results"][p] = 0
                        regional["results"][p] = regional["results"][p] + 1
                        if person:
                            log.info("CompId: {} Runner: {} Place: {}", row[0], r[1], r[0])
                except ValueError:
                    pass
        log.debug(regional)
        return regional

    def fetchClubs(self):
        html = requests.get(base_url +"/club/list")
        soup = BeautifulSoup(html.text, "html.parser", from_encoding="utf-8")
        table = soup.find("table", {'class': 'v-table'})
        rows = table.find_all("tr")
        ids = list()
        # Get competition IDs
        for row in rows:
            cells = row.find_all("td")
            if cells[1].text.strip() == "Lyhenne":
                continue
            try:
                clubUrl = cells[2].find_all("a")
                u = clubUrl[0].get("href")
                clubHtml = requests.get("https://irma.suunnistusliitto.fi" + u)
                clubSoup = BeautifulSoup(clubHtml.text, "html.parser", from_encoding="utf-8")
                clubTable = clubSoup.find_all("tr")
                region = "unknown"
                for r in clubTable:
                    c = r.find_all("td")
                    if c[0].text.strip() == "Alue":
                        region = c[2].text.strip()
                        break
                val =  {"name": cells[0].text.strip(), "short_name": cells[1].text.strip(), "region": region }
                self.insertClub(val)
                ids.append(val)
            except KeyError:
                print("")
        log.info(ids)
        return ids


    @staticmethod
    def createDb(dbFile):
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
                           CREATE TABLE runnerResults(id INTEGER PRIMARY KEY, compId INTEGER, class TEXT, runner TEXT, club TEXT, place INTEGER)
                       ''')
            cursor.execute('''
                           CREATE TABLE clubs(id INTEGER PRIMARY KEY,  name TEXT, short TEXT, region TEXT)
                       ''')
            db.commit()
        except sqlite3.OperationalError as e:
            log.info("DB exists" + str(e) )

    def openDb(self, dbFile):
        self.db = sqlite3.connect(dbFile)
