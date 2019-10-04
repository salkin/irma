#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import requests
import sqlite3
import sys
import urllib
import click
import irma
from bs4 import BeautifulSoup

YEAR="2019"
DB="res"+YEAR +".db"
#Club for which results are collected
CLUB = "Falken"
base_url = "https://irma.suunnistusliitto.fi/irma/public/"



def printCompetitions(db):
    cursor = db.cursor()
    cursor.execute('''SELECT id,name FROM competitions''')
    rows = cursor.fetchall()
    for r in rows:
        print(str(r[0])),
        print(" " + r[1])

def printStarts(db):
    cursor = db.cursor()
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
    print("TotalStarts: " + str(totalStarts))
    print("Class starts:")
    print("<table>")
    print("<tr>")
    cells = 0
    for k,v in sorted(classes.items()):
        print("<td> " + k + " " + str(v) + " </td>")
        if cells == 3:
            print("</tr>")
            print("<tr>")
            cells=0
        cells+=1
    print("</tr>")
    print("</table>")

@click.group()
def irmacli():
    pass

@irmacli.command()
def collect():
    printNames = False
    totalStarts = 0
    stats = dict()

    ids = getCompetitions(YEAR)
    insertCompetitions(db, ids)
    printCompetitions(db)

    for i in ids:
        getCompetition(i)

@irmacli.command()
def printStats():
    printStarts(db)

@irmacli.command()
def printCompStats():
    res = irma.getRegionalResults(db, "ÖID")
    print(res)
    print("FM")
    res = irma.getRegionalResults(db, "SM-", notLike=("karsinta", "esikisa"), person=True, classNotLike="B")
    print(res)
    pass

if __name__ == "__main__":
    db = irma.openDb(DB)
    irmacli()
    db.close()
