#!/usr/bin/env python3
# coding: utf8

import requests
import sqlite3
import sys
import urllib
import click
import irma
from bs4 import BeautifulSoup

base_url = "https://irma.suunnistusliitto.fi/irma/public/"

pass_irma = click.make_pass_decorator(irma.Irma, ensure=False)


@click.group()
@click.pass_context
@click.option("-y", "--year", default="2019")
def irmacli(ctx, year):
    db = irma.Irma(year)
    ctx.obj = db

@irmacli.command()
@pass_irma
def collect(ir):
    printNames = False
    totalStarts = 0
    stats = dict()

    ids = ir.getCompetitions()
    ir.insertCompetitions(ids)
    ir.printCompetitions()

    for i in ids:
        ir.getCompetition(i)

@irmacli.command()
@pass_irma
def printStats(ir):
    ir.printStarts()

@irmacli.command()
@pass_irma
def printCompStats(ir):
    res = ir.getRegionalResults( "ÖID")
    print(res)
    print("FM")
    res = ir.getRegionalResults( "SM-", notLike=("karsinta", "esikisa"), person=True, classNotLike="B")
    print(res)
    pass

if __name__ == "__main__":
    irmacli()
