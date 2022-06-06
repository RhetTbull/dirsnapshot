"""noxfile for dirsnapshot."""

import nox
from nox_poetry import session

nox.options.reuse_existing_virtualenvs = True
# nox.options.sessions = "lint", "safety", "mypy", "pytype", "tests"

SUPPORTED_PYTHON_VERSIONS = ["3.8", "3.9", "3.10"]
LATEST_VERSION = ["3.10"]


@nox.session(python=SUPPORTED_PYTHON_VERSIONS)
def mypy(session):
    session.run("poetry", "install", external=True)
    session.run("mypy", "dirsnapshot")


@session(python=LATEST_VERSION)
def docs(session):
    session.run("poetry", "install", external=True)
    session.run("pdoc3", "--html", "-o", "docs", "--force", "dirsnapshot")


@session(python=SUPPORTED_PYTHON_VERSIONS)
def tests(session):
    session.run("poetry", "install", external=True)
    session.run("pytest")
