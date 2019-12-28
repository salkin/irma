from flask import Flask, render_template,request
from irma import Irma
import logging
import os
import urllib
import operator

log = logging.getLogger("irmaweb")
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

app = Flask(__name__)

@app.route('/')
def clubstarts(name=None):
    base_url = request.url_root
    year = request.args.get("year", default="2019")
    club = request.args.get("club", default="Falken")
    irm = Irma(year)
    log.info("Fetching club %s" % club)
    oid = irm.getRegionalResults( "ÖID", club=club)
    total, classes = irm.getStarts(club=club)
    sorted_classes=sorted(classes)
    return render_template('competitions.html', totalStarts=total,
                           classes=classes,
                           sorted_classes=sorted_classes,
                           oid=oid,
                           club=club)

@app.route('/competition/<year>')
def competition(year=None):
    irm = Irma(year)
    starts, classes = irm.getStarts()
    return render_template("starts.html", competition=starts)

@app.route('/district')
def district(year=None):
    year = request.args.get("year", default="2019")
    irm = Irma(year)
    clubs = irm.getClubs()
    return render_template("district.html")


@app.route('/runners')
def runners():
    base_url = request.url_root
    year = request.args.get("year", default="2019")
    club = request.args.get("club", default="Falken")
    irm = Irma(year)
    res,classes = irm.getRunners(club)
    #sort_class =  sorted(classes.items(), key=lambda item:item[1]["total"])
    sort_class = sorted(classes)
    return render_template("runners.html", runners=res, sorted_class=sort_class,classes=classes )


@app.route('/competitor')
def competitior():
    name = request.args.get("name")
    nam = urllib.parse.unquote(name)
    irm = Irma("2019")
    res = irm.getRunnerResults(nam)
    return render_template("competitor_res.html", results=res)


def fillDbs():
    for i in range(2019, 2020):
        irm = Irma(str(i))
        ids = irm.getCompetitions()
        irm.insertCompetitions(ids)
        for j in ids:
            irm.getCompetition(j)

@app.route('/clubs')
def fillClubs():
    irm = Irma("2019")
    #ids = irm.fetchClubs()
    #for c in ids:
    #    irm.insertClub(c)
    clubs = irm.getClubs()
    club_results=dict()
    for c in clubs:
        res, run = irm.getRunners(c["short"])
        club_results[c["short"]] = res

    sort = list()
    for cl in  sorted(club_results, key=lambda k: len(club_results[k])):
        sort.append({ "short": cl, "runners": club_results[cl] })

    return render_template("district.html", clubs=clubs, club_results=sort)



if __name__ == "__main__":
    #fillDbs()
    app.run(host="0.0.0.0")
