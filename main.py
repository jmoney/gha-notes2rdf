import argparse
import glob
import os
import re

from datetime import datetime, timedelta
from pathlib import Path
from rdflib import XSD, Graph, Namespace
from rdflib.namespace import DCTERMS, RDF
from rdflib.term import BNode, Literal, URIRef


NOTES_NS = Namespace('https://www.jmoney.dev/notes#')
unfinished = re.compile('\*\s\[\s\](?P<task>.+)')
finished = re.compile('\*\s\[X\](?P<task>.+)')
task = re.compile('\*\s\[(?P<complete>X|\s)\]\s(?P<task>.+)')

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

    parser.add_argument('--format', action='store', dest='format', default='turtle')
    parser.add_argument('--root', action='store', dest='root')
    parser.add_argument('--uri', action='store', dest='uri', default="")

    args = parser.parse_args()
    uri = f'{args.uri}#'
    notes = Graph()
    binder = Binder(notes, uri, os.getenv('GITHUB_REPOSITORY').split("/")[-1])

    for path in sorted(glob.glob(f'{args.root}/**/*.md', recursive=True)):
        markdown = Path(path)
        divder = Divider(notes, uri, binder, markdown.parent.name)
        note = Note(notes, uri, divder, markdown)

    print(notes.serialize(format=args.format))
