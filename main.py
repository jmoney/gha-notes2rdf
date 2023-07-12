import argparse
import glob
import os

from datetime import datetime, timedelta
from pathlib import Path
from rdflib import XSD, Graph, Namespace
from rdflib.namespace import DCTERMS, RDF
from rdflib.term import Literal, URIRef


NOTES_NS = Namespace('https://www.jmoney.dev/notes#')

class BinderGraph:
    graph: Graph
    uri: str

    def __init__(self, graph: Graph, uri: str):
        self.graph = graph
        self.uri = uri
        self.graph.bind('notes', NOTES_NS)

    def add(self, node):
        self.graph.add(node)

    def get(self, iri):
        return self.nodes.get(iri)

    def serialize(self, format):
        return self.graph.serialize(format=format)

class Binder(BinderGraph):
    iri: URIRef
    name: str

    def __init__(self, graph: Graph, uri: str, name: str):
        super().__init__(graph, uri)
        self.iri = self.coin(name)
        self.name = slugify(name)

        super().add((self.iri, RDF.type, self.type()))
        super().add((self.iri, NOTES_NS.name, Literal(self.name, datatype=XSD.string)))

    def coin(self, key):
        return URIRef(f'{self.uri}Binder{slugify(key)}')

    def type(self):
        return NOTES_NS.Binder

class Divider(BinderGraph):
    iri: URIRef
    binder: Binder
    name: str

    def __init__(self, graph: Graph, uri: str, binder: Binder, name: str):
        super().__init__(graph, uri)
        self.iri = self.coin(name)
        self.binder = binder
        self.name = slugify(name)

        super().add((self.iri, RDF.type, self.type()))
        super().add((self.iri, NOTES_NS.name, Literal(self.name, datatype=XSD.string)))
        super().add((self.iri, DCTERMS.isPartOf, self.binder.iri))

    def coin(self, key: str):
        return URIRef(f'{self.uri}Divider{slugify(key)}')

    def type(self):
        return NOTES_NS.Divider

class Note(BinderGraph):
    iri: URIRef
    title: str
    divider: Divider
    filename: str

    def __init__(self, graph: Graph, uri: str, divider: Divider, path: Path):
        super().__init__(graph, uri)
        self.iri = self.coin(path.stem)
        self.title = self.title(path.stem)
        self.divider = divider
        self.filename = path

        super().add((self.iri, RDF.type, self.type()))
        super().add((self.iri, NOTES_NS.title, Literal(self.title, datatype=XSD.string)))
        super().add((self.iri, NOTES_NS.filename, Literal(self.filename, datatype=XSD.string)))
        super().add((self.iri, DCTERMS.isPartOf, self.divider.iri))

    def coin(self, key):
        return URIRef(f'{self.uri}Note{slugify(key)}')

    def type(self):
        return NOTES_NS.Note

    def title(self, key: str):
        return slugify(key)

class DailyNote(Note):
    today: str
    previous: URIRef
    next: URIRef

    def __init__(self, graph: Graph, uri: str, path: Path, divider: Divider, find_previous: bool = True, find_next: bool = True):
        super().__init__(graph, uri, divider, path)
        # date-i-fy
        # later when this literal is added to the graph, it will be converted to a date. If it's not a xsd:date, like 2021-01-01, it will have "something" done.  I could not determine what that something
        # was but it was not what I wanted.  So I'm doing this.
        self.today = path.stem.replace("_", "-")
        current = datetime.strptime(self.today, '%Y-%m-%d')

        if find_previous:
            # find the previous day
            _previous = current - timedelta(days=1)
            while os.path.isfile(f'{path.parent}/{_previous.strftime("%Y_%m_%d")}.md') is False:
                _previous = _previous - timedelta(days=1)

            self.previous = URIRef(f'{graph.base}Daily{slugify(_previous.strftime("%Y-%m-%d"))}')
            super().add((self.iri, NOTES_NS.previous, self.previous))

        if find_next:
            # find the previous day
            _next = current + timedelta(days=1)
            while os.path.isfile(f'{path.parent}/{_next.strftime("%Y_%m_%d")}.md') is False:
                _next = _next + timedelta(days=1)

            self.next = URIRef(f'{graph.base}Daily{slugify(_next.strftime("%Y-%m-%d"))}')
            super().add((self.iri, NOTES_NS.next, self.next))



    def coin(self, key):
        return URIRef(f'{self.uri}Daily{slugify(key)}')

    def type(self):
        return NOTES_NS.Daily

    def title(self, key: str):
        return key

def slugify(value: str):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens
    """
    return value.title().replace(" ", "").replace("_", "-").replace("-", "")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                    prog='notes2rdf',
                    description='Converts a specific directory structure of markdown files to RDF',
                    epilog='Peronsal project by @jmoney')

    parser.add_argument('--format', action='store', dest='format', default='ttl')
    parser.add_argument('--root', action='store', dest='root')
    parser.add_argument('--uri', action='store', dest='uri', default="")

    args = parser.parse_args()
    uri = f'{args.uri}#'
    notes = Graph()
    binder = Binder(notes, uri, os.getenv('GITHUB_REPOSITORY').split("/")[-1])

    daily_notes = sorted(glob.glob(f'{args.root}/daily-status/*.md'))
    for path in sorted(glob.glob(f'{args.root}/**/*.md', recursive=True)):
        markdown = Path(path)
        divder = Divider(notes, uri, binder, markdown.parent.name)

        note = None
        if markdown.parent.name == 'daily-status':
            note = DailyNote(notes, uri, markdown, divder, find_previous=(Path(daily_notes[0]) != markdown), find_next=(Path(daily_notes[-1]) != markdown))
        else:
            note = Note(notes, uri, divder, markdown)

    print(notes.serialize(format=args.format))
