"""noxfile for dirsnapshot."""

import nox
from nox_poetry import session

nox.options.reuse_existing_virtualenvs = True


@session(python=["3.10"])
def docs(session):
    session.install("pdoc3")
    session.run("poetry", "install", external=True)
    session.run("pdoc3", "--html", "-o", "docs", "--force", "dirsnapshot")


@session(python=["3.8", "3.9", "3.10"])
def tests(session):
    session.run("poetry", "install", external=True)
    session.run("pytest")
