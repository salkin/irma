from flask import Flask, render_template,request
from waitress import serve
from src.irma import Irma
import logging
import os
import urllib
from datetime import date, datetime
import operator

log = logging.getLogger("irmaweb")
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

maxYear = date.today().year + 1
maxYearStr = str(maxYear)
thisYear = str(date.today().year)
app = Flask(__name__)

@app.route('/')
def clubstarts():
    base_url = request.url_root
    year = request.args.get("year", default=thisYear)
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
                           club=club,
                           year=year,
                           maxYear=maxYear)

@app.route('/competition')
def competition(year=None):
    compId = request.args.get("compId", default=thisYear)
    year = request.args.get("year")
    cl = request.args.get("class")
    irm = Irma(year)
    results = irm.getCompetitionClass(compId, year, cl)
    return render_template("competition.html", results=results)

@app.route('/district')
def district(year=None):
    year = request.args.get("year", default=thisYear)
    irm = Irma(year)
    clubs = irm.getClubs()
    return render_template("district.html")


@app.route('/runners')
def runners():
    base_url = request.url_root
    year = request.args.get("year", default=thisYear)
    club = request.args.get("club", default="Falken")
    irm = Irma(year)
    res,classes = irm.getRunners(club)
    #sort_class =  sorted(classes.items(), key=lambda item:item[1]["total"])
    sort_class = sorted(classes)
    return render_template("runners.html", runners=res,
                           sorted_class=sort_class,
                           classes=classes,
                           maxYear=maxYear,
                           club=club )


@app.route('/competitor')
def competitior():
    name = request.args.get("name")
    year = request.args.get("year", default=thisYear)
    nam = urllib.parse.unquote(name)
    irm = Irma(year)
    res = irm.getRunnerResults(nam, year)
    return render_template("competitor_res.html", results=res,
                           maxYear=maxYear)


@app.route('/competitor_stat')
def competitior_stat():
    name = request.args.get("name")
    nam = urllib.parse.unquote(name)
    res = dict()
    irm = Irma(thisYear)
    for i in range(2012,maxYear):
        res_y = irm.getRunnerResults(nam, i)
        res[i] = res_y
    return render_template("competitor_stats.html", res=res,
                           maxYear=maxYear)


@app.route('/clubs')
def fillClubs():
    year = request.args.get("year", default=thisYear)
    irm = Irma(year)
    clubs = irm.getClubs()
    club_results=dict()
    club_starts=dict()
    for c in clubs:
        res, run = irm.getRunners(c["short"])
        club_results[c["short"]] = res
        starts,ll = irm.getStarts(c["short"])
        club_starts[c["short"]]  = starts
    sort = list()
    starts_sort = list()
    for cl in  sorted(club_results, key=lambda k: len(club_results[k])):
        sort.append({ "short": cl, "runners": club_results[cl] })
    for cl in  sorted(club_starts, key=lambda k: club_starts[k]):
        starts_sort.append({ "short": cl, "starts": club_starts[cl] })

    return render_template("district.html", clubs=clubs,
                           club_results=sort,
                           maxYear=maxYear,
                           club_starts=starts_sort)



if __name__ == "__main__":
    serve(app, listen='*:5000')
