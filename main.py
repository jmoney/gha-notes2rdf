import argparse
import glob
import os

from pathlib import Path
from rdflib import XSD, Graph, Namespace
from rdflib.namespace import RDF
from rdflib.term import Literal, URIRef


NOTES_NS = Namespace('https://www.jmoney.dev/notes#')

class Topic:
    iri: URIRef
    contains: list
    path: Literal

    def __init__(self, iri, path):
        self.iri = iri
        self.contains = []
        self.path = path

    def will_contain(self, note):
        self.contains.append(note.iri)

    def add_to_graph(self, graph):
        graph.add((self.iri, RDF.type, NOTES_NS.Topic))
        graph.add((self.iri, NOTES_NS.Path, Literal(markdown.parent, datatype=XSD.string)))
        for note in self.contains:
            graph.add((self.iri, NOTES_NS.contains, note))

class Note:
    iri: URIRef
    title: Literal
    filename: Literal

    def __init__(self, iri, title, filename):
        self.iri = iri
        self.title = title
        self.filename = filename

    def add_to_graph(self, graph: Graph):
        graph.add((self.iri, RDF.type, NOTES_NS.Note))
        graph.add((self.iri, NOTES_NS.title, Literal(self.title, datatype=XSD.string)))
        graph.add((self.iri, NOTES_NS.filename, Literal(self.filename, datatype=XSD.string)))

def slugify(value: str):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens
    """
    return value.title().replace(" ", "").replace("_", "-").replace("-", "")

def create_topic(base_uri: str, markdown: Path):
    iri = URIRef(f'{base_uri}#Topic{slugify(markdown.parent.name)}')
    return Topic(iri, markdown)

def create_note(base_uri: str, markdown: Path):
    iri = URIRef(f'{base_uri}#Note{slugify(markdown.stem)}')
    return Note(iri, markdown.stem, markdown.name)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                    prog='notes2rdf',
                    description='Converts a specific directory structure of markdown files to RDF',
                    epilog='Peronsal project by @jmoney')
    
    parser.add_argument('--root', action='store', dest='root')
    parser.add_argument('--uri', action='store', dest='uri', default="")

    args = parser.parse_args()

    notes = Graph(base=f'{args.uri}#')
    notes.bind('notes', NOTES_NS)
    nodes = {}

    for path in sorted(glob.glob(f'{args.root}/**/*.md', recursive=True)):
        markdown = Path(path)
        
        note = create_note(args.uri, markdown)
        nodes[note.iri] = note
        topic = create_topic(args.uri, markdown)
        if nodes.get(topic.iri) is None:
            nodes[topic.iri] = topic
        nodes[topic.iri].will_contain(note)
    
    for triple in nodes.values():
        triple.add_to_graph(notes)

print(notes.serialize(format='ttl'))