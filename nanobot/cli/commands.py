import typer


app = typer.Typer(help="nanobot - lightweight AI assistant")


@app.command()
def version():
    from nanobot import __version__
    print(__version__)
