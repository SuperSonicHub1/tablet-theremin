import sys

from .app import Application


def main():
    app = Application()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


__all__ = ['main']
