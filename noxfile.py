"""noxfile for dirsnapshot."""

import tempfile
from typing import Any

import nox
from nox_poetry import session

nox.options.reuse_existing_virtualenvs = True
# nox.options.sessions = "lint", "safety", "mypy", "pytype", "tests"


@nox.session(python=["3.8", "3.9", "3.10"])
def mypy(session):
    session.run("poetry", "install", external=True)
    session.run("mypy", "dirsnapshot")


@session(python=["3.10"])
def docs(session):
    session.run("poetry", "install", external=True)
    session.run("pdoc3", "--html", "-o", "docs", "--force", "dirsnapshot")


@session(python=["3.8", "3.9", "3.10"])
def tests(session):
    session.run("poetry", "install", external=True)
    session.run("pytest")
