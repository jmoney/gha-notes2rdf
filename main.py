import argparse
import glob
import os
import sys

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from rdflib import XSD, Graph, Namespace
from rdflib.namespace import RDF
from rdflib.term import Literal, URIRef


NOTES_NS = Namespace('https://www.jmoney.dev/notes#')

class TopicGraph:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.graph.bind('notes', NOTES_NS)
        self.nodes = {}

    def add(self, node):
        self.nodes[node[0]] = node
        self.graph.add(node)

    def get(self, iri):
        return self.nodes.get(iri)

    def serialize(self, format):
        return self.graph.serialize(format=format)
    
class Topic(TopicGraph):
    iri: URIRef
    topic: str
    contains: list
    path: str

    def __init__(self, graph: Graph, path: Path):
        super().__init__(graph)
        self.iri = self.coin(path.parent.name)
        self.path = path.parent
        self.topic = slugify(path.parent.name)
        self.contains = []

        super().add((self.iri, RDF.type, self.type()))
        super().add((self.iri, NOTES_NS.Path, Literal(self.path, datatype=XSD.string)))
        super().add((self.iri, NOTES_NS.topic, Literal(self.topic, datatype=XSD.string)))
    
    def coin(self, key):
        return URIRef(f'{self.graph.base}Topic{slugify(key)}')
    
    def type(self):
        return NOTES_NS.Topic

    def will_contain(self, note):
        self.contains.append(note)
        super().add((self.iri, NOTES_NS.contains, note))

class Note(TopicGraph):
    iri: URIRef
    title: str
    filename: str

    def __init__(self, graph: Graph, path: Path):
        super().__init__(graph)
        self.iri = self.coin(path.stem)
        self.title = self.title(path.stem)
        self.filename = path.name

        super().add((self.iri, RDF.type, self.type()))
        super().add((self.iri, NOTES_NS.title, Literal(self.title, datatype=XSD.string)))
        super().add((self.iri, NOTES_NS.filename, Literal(self.filename, datatype=XSD.string)))

    def coin(self, key):
        return URIRef(f'{self.graph.base}Note{slugify(key)}')
    
    def type(self):
        return NOTES_NS.Note
    
    def title(self, title: str):
        return slugify(title)

class DailyNote(Note):
    today: str
    previous: any

    def __init__(self, graph: Graph, path: Path, find_previous: bool = True):
        super().__init__(graph, path)
        # date-i-fy
        # later when this literal is added to the graph, it will be converted to a date. If it's not a xsd:date, like 2021-01-01, it will have "something" done.  I could not determine what that something
        # was but it was not what I wanted.  So I'm doing this.
        self.today = path.stem.replace("_", "-")
        _today = datetime.strptime(self.today, '%Y-%m-%d')

        if find_previous:
            # find the previous day
            yesterday = _today - timedelta(days=1)
            while os.path.isfile(f'{path.parent}/{yesterday.strftime("%Y_%m_%d")}.md') is False:
                yesterday = yesterday - timedelta(days=1)

            self.previous = URIRef(f'{graph.base}Daily{slugify(yesterday.strftime("%Y-%m-%d"))}')
            super().add((self.iri, NOTES_NS.previous, self.previous))

    def coin(self, key):
        return URIRef(f'{self.graph.base}Daily{slugify(key)}')

    def type(self):
        return NOTES_NS.Daily
    
    def title(self, title: str):
        return title

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

    notes = Graph(base=f'{args.uri}#')

    daily_notes = sorted(glob.glob(f'{args.root}/daily-status/*.md'))
    for path in sorted(glob.glob(f'{args.root}/**/*.md', recursive=True)):
        markdown = Path(path)
        note = None
        if markdown.parent.name == 'daily-status':
            note = DailyNote(notes, markdown, find_previous=(Path(daily_notes[0]) != markdown))
        else:
            note = Note(notes, markdown)

        topic = Topic(notes, markdown)
        if notes.items(topic.iri) is None:
            notes.add(topic)
        topic.will_contain(note.iri)
    
    print(notes.serialize(format=args.format))