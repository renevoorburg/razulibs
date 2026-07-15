from __future__ import annotations  # unquoted forward references in Python < 3.14

from razu_idgenerator.database import Database
from razu_idgenerator.generator import IdentifierGenerator
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, XSD, SKOS, OWL

"""
CFG PARAMS to organize
"https://data.razu.nl/id/object/"
"""
# put this somewhere else
LDTO = Namespace("https://data.razu.nl/def/ldto/")

"""
TODO: 
- include manifest stuff
- more config params at the edepot level
- ...
"""


class Edepot:

    def __init__(self, maintainer: str, storage_location: str) -> None:
        self.maintainer = maintainer
        self.storage_location = storage_location
    
    def create_sip(self, producer: str, dataset_id: str) -> Sip:
        return Sip(edepot=self, producer=producer, dataset_id=dataset_id)


class Sip:

    def __init__(self, edepot: Edepot, producer: str, dataset_id: str) -> None:
        self.producer = producer
        self.dataset_id = dataset_id
        self.edepot = edepot
        self.id_generator = IdentifierGenerator(Database())

    def create_resource(
        self,
        resource_type: str,
        aggregation_level: str,
        inventory_code: str | None = None,
        filepath: str | None = None,
    ) -> RDFResource:
        return RDFResource(
            sip=self,
            resource_type=resource_type,
            aggregation_level=aggregation_level,
            inventory_code=inventory_code,
            filepath=filepath,
        )
    
    @property
    def maintainer(self) -> str:
        return self.edepot.maintainer

class RDFResource:

    def __init__(
        self,
        sip: Sip,
        resource_type: str,
        aggregation_level: str,
        inventory_code: str | None = None,
        filepath: str | None = None,
    ) -> None:
        self.sip = sip
        self.edepot = sip.edepot
        self.identifier, self.is_new, self.stepped_dir = sip.id_generator.generate(
            sip.producer,
            sip.dataset_id,
            resource_type,
            aggregation_level,
            inventory_code,
            filepath,
        )
        self.uri = URIRef("https://data.razu.nl/id/object/"+self.identifier) #TODO !
        self.filename = self.edepot.storage_location + self.stepped_dir + self.identifier + ".meta.json" #TODO !
        self.graph = Graph()
        self.add_property(RDF.type, URIRef(LDTO.Informatieobject))

    def add_property(self, predicate: URIRef, object):
        if isinstance(object, RDFResource):
            self.graph.add((self.uri, predicate, object.uri))
            self.graph += object.graph
        elif isinstance(object, URIRef):
            self.graph.add((self.uri, predicate, object))

    def save(self, format=None) -> bool:
        if format is None:
            format = 'json-ld'
        if True:  # self.is_modified:
            try:
                Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as file:
                    file.write(self.graph.serialize(format=format))
                self.is_modified = False
                return True
            except IOError as e:
                print(f"Error saving file {self.filename}: {e}")
        return False 


depot = Edepot(maintainer="nl-wbdrazu", storage_location="./")
sip = depot.create_sip(producer="g0422", dataset_id="123")
resource = sip.create_resource(resource_type="Informatieobject", aggregation_level="Archief")
resource.save()



# tests
print(sip.maintainer)  # expect "nl-wbdrazu"
print(resource.identifier)
print(resource.is_new)
print(resource.stepped_dir)
print(resource.filename)



