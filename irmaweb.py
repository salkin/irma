from flask import Flask, render_template,request
from irma import Irma
import logging
import os
import urllib

log = logging.getLogger("irmaweb")
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

app = Flask(__name__)

@app.route('/')
def hello(name=None):
    return render_template('competitions.html', name=name)

@app.route('/competition/<year>')
def competition(year=None):
    irm = Irma(year)
    starts = irm.getStarts()
    return render_template("starts.html", competition=starts)


@app.route('/runners')
def runners():
    base_url = request.url_root
    club = request.args.get("club", default="Falken")
    irm = Irma("2019")
    res = irm.getRunners(club)
    return render_template("runners.html", runners=res)


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


if __name__ == "__main__":
    fillDbs()
    app.run(host="0.0.0.0")
