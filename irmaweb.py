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
def clubstarts():
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
                           club=club,
                           year=year)

@app.route('/competition')
def competition(year=None):
    compId = request.args.get("compId", default="2019")
    year = request.args.get("year")
    cl = request.args.get("class")
    irm = Irma(year)
    results = irm.getCompetitionClass(compId, year, cl)
    return render_template("competition.html", results=results)

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
    year = request.args.get("year", default="2019")
    nam = urllib.parse.unquote(name)
    irm = Irma(year)
    res = irm.getRunnerResults(nam)
    return render_template("competitor_res.html", results=res)


@app.route('/clubs')
def fillClubs():
    year = request.args.get("year", default="2019")
    irm = Irma(year)
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
    app.run(host="0.0.0.0")
