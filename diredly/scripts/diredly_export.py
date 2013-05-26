"""
basic site export
"""
from webob import Request
from paste.deploy import loadapp
import os
import sys


def main():
    app_ini, export_dir = [os.path.abspath(i) for i in sys.argv[1:]]
    assert os.path.isfile(app_ini), "no ini file"

    if os.path.isdir(export_dir):
        raise ValueError("%s already exists" % export_dir)
    else:
        os.makedirs(export_dir)

    app = loadapp("config:%s" % app_ini)

    for file_item in Request.blank("/list").send(app).body.split("\n"):
        res = Request.blank(file_item).send(app)
        destination = os.path.join(export_dir, file_item[1:])
        print "%s --> %s" % (file_item, destination)
        if not os.path.isdir(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        with open(destination, "wb") as d:
            d.write(res.body)
