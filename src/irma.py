import requests
import sys
import click
import os
import logging
from datetime import datetime
import mysql.connector as mariadb
from bs4 import BeautifulSoup

log = logging.getLogger("irma")
base_url = "https://irma.suunnistusliitto.fi/irma/public"
dbDir = os.environ["DB_DIR"]
mariadb_host = os.environ["MARIADB_HOST"]
thisYear=2020
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
        self.mariadb_connection.close()

    def insertCompetitions(self, ids):
        cursor = self.mariadb_connection.cursor()
        for i in ids:
            log.info(str(i))
            cursor.execute('''SELECT compId,name,club FROM competitions WHERE compId=%s''', (i["id"],))
            r = cursor.fetchone()
            d = datetime.strptime(i["date"], "%d.%m.%Y")
            mday = d.strftime("%Y-%m-%d")
            if r == None:
                cursor.execute('''INSERT INTO competitions(compId, name, club, date)
                            VALUES(%s,%s,%s,%s)''', (i["id"],i["name"],i["club"],mday,))
        self.mariadb_connection.commit()

    def insertClub(self, i):
        cursor = self.mariadb_connection.cursor()
        cursor.execute('''SELECT name FROM clubs WHERE short="%s"''' % (i["short_name"],))
        r = cursor.fetchone()
        if r == None:
            cursor.execute('''INSERT INTO clubs(name, short, region)
                        VALUES("%s","%s","%s")''' % (i["name"],i["short_name"],i["region"]))
        else:
            cursor.execute('''UPDATE clubs SET region="%s" WHERE name="%s"''' % (i["region"],i["name"]))
        self.mariadb_connection.commit()

    def getClubs(self, region="FSO"):
        cursor = self.mariadb_connection.cursor()
        cursor.execute('''SELECT name, short, region FROM clubs WHERE region="%s"''' % (region))
        rows = cursor.fetchall()
        clubs = list()
        for r in rows:
            clubs.append({"name": r[0], "short": r[1]})
        return clubs


    def getStarts(self, club=CLUB):
        cursor = self.mariadb_connection.cursor()
        totalStarts=0
        classes = dict()
        cursor.execute('''SELECT class, runnerResults.compId FROM (SELECT class,compId FROM runnerResults WHERE club="%s") runnerResults
                       INNER JOIN %s ON (runnerResults.compId = competitions.compId)'''% (club, self.getInnerJoinYear()))
        rows = cursor.fetchall()
        for r in rows:
            try:
                classes[r[0][:3]] += 1
            except KeyError:
                classes[r[0][:3]] = 1
            totalStarts = totalStarts + 1
        return totalStarts, classes


    def getCompStarts(self, compId, club=CLUB):
        cursor = self.mariadb_connection.cursor()
        totalStarts=0
        classes = dict()
        cursor.execute('''SELECT class FROM runnerResults WHERE compId=%s AND club=%s''', (compId, club,))
        rows = cursor.fetchall()
        for r in rows:
            try:
                classes[r[0][:3]] += 1
            except KeyError:
                classes[r[0][:3]] = 1
            totalStarts = totalStarts + 1
        return totalStarts, classes

    def getInnerJoinYear(self):
        startYear = self.year + "-01-01"
        endYear = self.year + "-12-31"
        yearStr = '''(SELECT compId FROM competitions WHERE date > "%s" AND date < "%s") competitions''' % (startYear, endYear)
        return yearStr

    def getRunners(self, club=CLUB):
        cursor = self.mariadb_connection.cursor()
        query = '''SELECT DISTINCT runner, class,runnerResults.compId FROM (SELECT * FROM runnerResults WHERE club="%s") runnerResults
                       INNER JOIN %s ON (runnerResults.compId = competitions.compId)''' % (club, self.getInnerJoinYear())
        logging.info(query)
        cursor.execute(query)
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
        cursor = self.mariadb_connection.cursor()
        cursor.execute('''INSERT INTO compResults(compId, class, competitors) VALUES(%d,%s,%d)'''% (id, sarja, 0,))
        self.mariadb_connection.commit()

    def addRunnderResult(self, id, name, sarja,place, club, comp_time):
        cursor = self.mariadb_connection.cursor()
        ctime = self.formatCompTime(comp_time)
        try:
            query = '''INSERT INTO runnerResults(compId, class, runner, club, place, comp_time) VALUES(%d,'%s','%s','%s',%d, '%s')'''% (int(id), sarja, name, club, int(place), ctime)
        except ValueError:
            logging.error("Invalid runner result: Runner: %s, place%s" % (name, place))
            return
        try:
            cursor.execute(query)
            self.mariadb_connection.commit()
        except Exception as e:
            logging.error("Failed query" + query + ". Exception" + str(e))

    def formatCompTime(self, comp_time):
        sp_time = comp_time.split(".")
        if len(sp_time) == 3:
            return ":".join(sp_time)
        else:
            d = ":".join(sp_time)
            return "0:"+d


    def getRunnerResults(self, name, year=thisYear):
        cursor = self.mariadb_connection.cursor()
        results = dict()
        yearStart = str(year) + "-01-01"
        yearEnd = str(year) + "-12-21"
        formatString = "%Y-%m-%d"
        query ='''SELECT runnerResults.compId,place,class,comp_time from (SELECT * FROM runnerResults WHERE runnerResults.runner="%s") runnerResults
                  INNER JOIN (SELECT compId FROM competitions WHERE STR_TO_DATE(date, "%s") > "%s" and STR_TO_DATE(date, "%s") < "%s") competitions
                  ON (runnerResults.compId = competitions.compId)''' % (name, formatString, yearStart, formatString, yearEnd)
        cursor.execute(query)
        rows = cursor.fetchall()
        for r in rows:
            query='''SELECT name,club FROM competitions WHERE compId=%d''' % (r[0])
            cursor.execute(query)
            com = cursor.fetchone()
            if com != None:
                results[com[0]] = {"class": r[2], "place": r[1], "arrangingClub": com[1], "compId": r[0], "compTime": r[3]}
            cursor.execute('''SELECT COUNT(runner) FROM runnerResults WHERE compId="%d" AND class="%s"''' % (r[0], str(r[2])))
            tot = cursor.fetchone()
            if tot != None:
                results[com[0]]["total"] = tot[0]
        return results

    def getCompetitionClass(self,compId, year, cl):
        cursor = self.mariadb_connection.cursor()
        results = list()
        cursor.execute('''SELECT runner, place, comp_time FROM runnerResults WHERE compId="%s" AND class="%s" ORDER BY place''' % (compId,cl))
        rows = cursor.fetchall()
        for r in rows:
            results.append({"name": r[0], "place": r[1], "compTime": r[2]})
        return results


    def addCompetitior(self, id, sarja):
        cursor = self.mariadb_connection.cursor()
        cursor.execute("SELECT competitors FROM compResults WHERE compId=%s AND class=%s", (id, sarja,))
        r = cursor.fetchone()
        if r == None:
            cursor.execute('''INSERT INTO compResults(compId, class, competitors) VALUES(%s,%s,%s)''', (id, sarja, 1,))
        else:
            cursor.execute('''UPDATE compResults SET competitors=competitors+1 WHERE compId=%s AND class=%s''', (id, sarja,))
        self.mariadb_connection.commit()


    def getCompetitions(self):
        html = requests.get(base_url +"/competitioncalendar/view?year=" + self.year, verify=False )
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
                val =  {"id": cells[3].text.strip(), "name": c.text.strip(), "club": cells[2].text.strip(),
                        "discipline": cells[4].text.strip(), "date": cells[0].text.strip()}
                ids.append(val)
            except KeyError:
                print("")
        return ids

    def getCompetition(self, com):
        if self.isCompProcessed( com["id"]):
            log.info(com["name"] + " processed")
            return
        res_url = base_url + '/competition/results?id=' + com["id"]
        resp = requests.get(res_url, verify=False)
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
                            self.addRunnderResult( com["id"], cells[1].text.strip(), sarja, cells[0].text.strip(), cells[2].text.strip(), cells[3].text.strip())
                            compStarts += 1
                    except IndexError:
                        continue
            else:
                continue

        meta = soup.find("meta", {"name" : "header"})
        log.info(meta["content"] + " " + str(compStarts) + " starts")


    def isCompProcessed(self, id):
        cursor = self.mariadb_connection.cursor(buffered=True)
        cursor.execute('''SELECT * FROM compResults WHERE compId=%s''', (id,))
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
        cursor = self.mariadb_connection.cursor()
        yearSelect = '''date > "%s-01-01" AND date < "%s-12-31"''' % (str(self.year), str(self.year))
        searchString = '''SELECT compId, name FROM competitions WHERE %s AND name LIKE "%s" ''' % (yearSelect, "%" + region + "%")
        log.info(searchString)
        if len(notLike) > 0:
            for l in notLike:
                searchString +=  ''' and name not like "%{}%"'''.format(l)
        cursor.execute(searchString)
        res = cursor.fetchall()
        for row in res:
            cursor.execute('''SELECT place,runner,class FROM runnerResults WHERE compId=%s AND club=%s''', (row[0],club,))
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
        # get clubs
        html = requests.get(base_url +"/club/list", verify=False)
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
                clubHtml = requests.get("https://irma.suunnistusliitto.fi" + u, verify=False)
                clubSoup = BeautifulSoup(clubHtml.text, "html.parser", from_encoding="utf-8")
                clubTable = clubSoup.find_all("tr")
                region = "unknown"
                for r in clubTable:
                    c = r.find_all("td")
                    if len(c) > 0:
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
    def createDb():
        mariadb_connection = mariadb.connect(user='nwik', password='nwik', database='irma', host=mariadb_host)
        cursor = mariadb_connection.cursor()
        try:
            cursor.execute('''
                           CREATE TABLE competitions(compId INTEGER PRIMARY KEY, name TEXT, club TEXT,
                                                     discipline TEXT,
                                                     date DATE)
                       ''')
            cursor.execute('''
                           CREATE TABLE compResults(id INTEGER PRIMARY KEY auto_increment, compId INTEGER, class TEXT, competitors INTEGER)
                       ''')
            cursor.execute('''
                           CREATE TABLE runnerResults(id INTEGER PRIMARY KEY auto_increment, compId INTEGER, class TEXT, runner TEXT, club TEXT, comp_time TIME, place INTEGER)
                       ''')
            cursor.execute('''
                           CREATE TABLE clubs(id INTEGER PRIMARY KEY auto_increment,  name TEXT, short TEXT, region TEXT)
                       ''')
            db.commit()
        except Exception as me:
            log.info("Table exists" + str(me) )

    def openDb(self, dbFile):
        self.mariadb_connection = mariadb.connect(user='nwik', password='nwik', database='irma',  host=mariadb_host)

