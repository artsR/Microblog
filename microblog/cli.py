import os
import click
""" 'update', 'init'
'k _l' - first of all, the lazy_gettext as _l should be added to 'main __init__'
"""
# I cannot use 'current_app' instead of referring to the 'app' because below
# commands are registered at start up, not during the 'handling request'
# (which is the only time when 'current_app' can be used).
# Therefore as a solution I should define function that takes 'app instance'
# as an argument:   (this function will be called during __init__ 'app instance')
def register(app):
    # Building groups of commands with parent of 'translate' using 'Click':
    @app.cli.group()
    def translate(): # this will be a parent command that only will exist to provide
                    # a base for the sub-commands therefore 'pass' - does not need
                    # to do anything.
        """Translation and localization commands."""
        pass

    # Below functions ('pybabel ...') returns 0 if executed properly.

    @translate.command() # look at 'flaskr' '@click.command('init-db')'
    def update():
        """Update all languages."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
                                                # '-k _l' - assumes that lazy_gettext was imported as '_l'
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d microblog/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    def compile():
        """Compile all languages."""
        if os.system('pybabel compile -d microblog/translations'):
            raise RuntimeError('compile command failed')

    @translate.command()
    @click.argument('lang') # Click passes the value provided in the command to the
                            # handler function as an argument, and then it is incorporated
                            # into the 'init' command:
    def init(lang):
        """Initialize a new language."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot'):
                                                # '-k _l' - assumes that lazy_gettext was imported as '_l'
            raise RuntimeError('extract command failed')
        if os.system('pybabel init -i messages.pot -d microblog/translations -l ' + lang):
            raise RuntimeError('init command failed')
        os.remove('messages.pot')
