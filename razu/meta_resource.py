import os
from rdflib import URIRef, Literal, BNode
from typing import Callable, Any

from razu.incrementer import Incrementer
from razu.config import Config
from razu.identifiers import Identifiers
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, LDTO, DCT, PREMIS, XSD, SKOS
from razu.concept_resolver import ConceptResolver
import razu.util as util


class MetaResource(RDFResource):
    """
    An RDF Resource tailored in the context of an RAZU edepot SIP.
    Provides load(), save() and identifier logic.
    """
    _counter = Incrementer(0)
    _context = None
    _id_factory = None

    @classmethod
    def _get_context(cls):
        if cls._context is None:
            cls._context = Config.get_instance()
            cls._id_factory = Identifiers(cls._context)
        return cls._context

    def __init__(self, id: str | None = None, uri: str | None = None):
        MetaResource._get_context()
        self.id = id if id else str(MetaResource._counter.next())
        resolved_uri = uri if uri else MetaResource._id_factory.make_uri_from_id(self.id)
        super().__init__(uri=resolved_uri)
        self.is_modified = True
        self.is_from_existing = False

    @property
    def uid(self) -> str:
        return MetaResource._id_factory.make_uid_from_id(self.id)

    @property
    def filename(self) -> str:
        cfg = Config.get_instance()
        return f"{self.id}.{cfg.metadata_suffix}.{cfg.metadata_extension}"
    
    @property
    def local_file_path(self) -> str:
        return os.path.join(Config.get_instance().sip_directory, self.filename)

    def filestore_key(self) -> str:
        return self._id_factory.make_s3_key_from_id(self.id)
 
    def save(self, format=None) -> bool:
        if format is None :
            format = 'json-ld'
        if self.is_modified:
            try:
                with open(self.local_file_path, 'w', encoding='utf-8') as file:
                    file.write(self.graph.serialize(format=format))
                self.is_modified = False
                return True
            except IOError as e:
                print(f"Error saving file {self.local_file_path}: {e}")
        return False 

    def load(self) -> None:
        self.graph = MetaGraph()
        with open(self.local_file_path, 'r', encoding='utf-8') as file:
            self.graph.parse(data=file.read(), format="json-ld")
        self.is_modified = False
        self.is_from_existing = True


class StructuredMetaResource(MetaResource):
    """
    Provides RDF structure templates for filling MetaResource,
    and properties for easy access to key parts of the graph data.
    """

    _actoren = None
    _aggregatieniveaus = None
    _algoritmes = None
    _beperkingen_openbaarheid = None
    _bestandsformaten = None
    _dekkingintijdtypen = None
    _eventtypen = None
    _licenties = None
    _waarderingen = None

    @classmethod
    def _get_resolvers(cls):
        if cls._actoren is None:
            cls._actoren = ConceptResolver("actor")
            cls._aggregatieniveaus = ConceptResolver("aggregatieniveau")
            cls._algoritmes = ConceptResolver("algoritme")
            cls._beperkingen_openbaarheid = ConceptResolver("openbaarheid")
            cls._bestandsformaten = ConceptResolver("bestandsformaat")
            cls._dekkingintijdtypen = ConceptResolver("dekkingintijdtype")
            cls._eventtypen = ConceptResolver("eventtype")
            cls._licenties = ConceptResolver("licentie")
            cls._waarderingen = ConceptResolver("waardering")

    def __init__(self, id: str | None = None, uri: str | None = None):
        super().__init__(id, uri=uri)
        StructuredMetaResource._get_resolvers()
        self.based_on_sources = set()

    @property
    def filename(self) -> str:
        cfg = Config.get_instance()
        return f"{self.id}.{cfg.metadata_suffix}.{cfg.metadata_extension}"

    def add(self, predicate: URIRef, obj, transformer: Callable = Literal) -> None:
        """Add a triple to the graph and mark as modified."""
        super().add_property(predicate, obj, transformer)
        self.is_modified = True
    
    def add_properties(self, rdf_properties: dict) -> None:
        """Add properties to the graph and mark as modified."""
        super().add_properties(rdf_properties)
        self.is_modified = True

    def add_list_from_string(self, predicate: URIRef, item_list: str, separator: str, transformer: Callable = Literal) -> None:
        """Add a list of values from a string and mark as modified."""
        super().add_properties_from_string(predicate, item_list, separator, transformer)
        self.is_modified = True

    @property
    def is_based_on_sources(self) -> bool:
        return bool(self.based_on_sources)

    @property
    def has_referenced_file(self) -> bool:
        return self._get_object_value(LDTO.URLBestand, self.uri) is not None

    @property
    def referenced_file_uri(self) -> str | None:
        value = self._get_object_value(LDTO.URLBestand, self.uri)
        return value if value is not None else None
    
    @property
    def referenced_file_filename(self) -> str:
        return os.path.basename(str(self.referenced_file_uri))

    @property
    def referenced_file_original_filename(self) -> str:
        return str(self._get_object_value(PREMIS.originalName, URIRef(self.referenced_file_uri)))

    @property
    def referenced_file_md5checksum(self) -> str:
        return str(self._get_object_value(LDTO.checksumWaarde))

    @property
    def referenced_file_checksum_datetime(self) -> str:
        return str(self._get_object_value(LDTO.checksumDatum))

    @property
    def reference_file_fileformat(self) -> str:
        return str(self._get_object_value(LDTO.bestandsformaat, self.uri))
    
    def set_type(self, rdf_type: URIRef) -> None:   
        self.add_properties({RDF.type: rdf_type})

    def set_archive_creator(self) -> None:
        self.add_properties({LDTO.archiefvormer: Config.get_instance().archive_creator_uri})

    def set_name(self, name: str) -> None:
        self.add_properties({LDTO.naam: name})

    def set_classification(self, classification_uri: URIRef) -> None:
        self.add_properties({LDTO.classificatie: classification_uri})

    def set_keywords(self, keywords: str, separator: str = ";") -> None:
        self.add_list_from_string(LDTO.trefwoord, keywords, separator)

    def set_applicable_period(self, start_date: str, end_date: str) -> None:
        self.add_properties({
            LDTO.dekkingInTijd: { 
                RDF.type: LDTO.DekkingInTijdGegevens,
                LDTO.dekkingInTijdBeginDatum: util.date_type(start_date),
                LDTO.dekkingInTijdEindDatum: util.date_type(end_date),
                LDTO.dekkingInTijdType: URIRef(StructuredMetaResource._dekkingintijdtypen.get_concept_uri("Van toepassing"))
            }
        })

    def set_event_with_actor(self, event_type: str, event_date: str, event_actor: str) -> None:
        self.add_properties({
            LDTO.event: {
                RDF.type: LDTO.EventGegevens,
                LDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri(event_type)),
                LDTO.eventTijd: util.date_type(event_date),
                LDTO.eventVerantwoordelijkeActor: URIRef(StructuredMetaResource._actoren.get_concept_uri(event_actor))
            } 
        })

    def set_publication_date(self, publication_date: str) -> None:
        self.add_properties({
            LDTO.event: {
                RDF.type: LDTO.EventGegevens,
                LDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri("Publicatie")),
                LDTO.eventTijd: util.date_type(publication_date)
            } 
        })

    def set_md5_properties(self, md5checksum, checksum_datetime) -> None:
        self.add_properties({
            LDTO.checksum: {
                RDF.type: LDTO.ChecksumGegevens,
                LDTO.checksumAlgoritme: StructuredMetaResource._algoritmes.get_concept("MD5").get_uri(),
                LDTO.checksumDatum: Literal(checksum_datetime, datatype=XSD.dateTime),
                LDTO.checksumWaarde: md5checksum
            }
        })

    def set_fileproperties_by_puid(self, puid, cdn_base_uri: str) -> None:
        ext_file_fileformat_uri = StructuredMetaResource._bestandsformaten.get_concept(puid).get_uri()
        file_extension = StructuredMetaResource._bestandsformaten.get_concept(puid).get_value(SKOS.notation)
        ext_filename = f"{self.id}.{file_extension}"
        url = f"{cdn_base_uri}{ext_filename}"
        self.add_properties({
            LDTO.bestandsformaat: ext_file_fileformat_uri,
            LDTO.URLBestand: Literal(url, datatype=XSD.anyURI),
        })
        self.add_triple(URIRef(url), RDF.type, PREMIS.File)

    def set_filesize(self, filesize: int) -> None:
        self.add_properties({LDTO.omvang: Literal(filesize, datatype=XSD.integer)})

    def set_original_filename(self, ext_file_original_filename: str) -> None:
        self.add_triple(URIRef(self.referenced_file_uri), PREMIS.originalName, Literal(ext_file_original_filename))

    def set_aggregation_level(self, aggregation_term) -> None:
        self.add_properties({LDTO.aggregatieniveau: StructuredMetaResource._aggregatieniveaus.get_concept(aggregation_term).get_uri()})

    def set_restrictions_public_availability(self, beperking_term) -> None:
        self.add_properties({
            LDTO.beperkingGebruik: StructuredMetaResource._beperkingen_openbaarheid.get_concept(beperking_term).get_uri()
        })

    def set_license(self, license_term) -> None:
        self.add_properties({
            LDTO.beperkingGebruik: StructuredMetaResource._licenties.get_concept(license_term).get_uri()
        })

    def add_based_on_source(self, source) -> None:
        self.based_on_sources.add(source)

    def _get_object_value(self, predicate, subject=None) -> Any:
        if subject is not None:
            for s, p, o in self.graph.triples((subject, predicate, None)):
                return o
        else:
            for s, p, o in self.graph.triples((None, predicate, None)):
                if isinstance(s, BNode):
                    return o
        return None

    def validate_referenced_file_md5checksum(self) -> bool:
        return util.calculate_md5(os.path.join(Config.get_instance().sip_directory, self.referenced_file_filename)) == self.referenced_file_md5checksum

    def _init_rdf_properties(self, rdf_type, metadata_file_uri: str | None = None) -> None:
        properties = {
            RDF.type: rdf_type,
            LDTO.identificatie: {
                RDF.type: LDTO.IdentificatieGegevens,
                LDTO.identificatieBron: "e-Depot RAZU",
                LDTO.identificatieKenmerk: self.uri
            }
        }
        if metadata_file_uri:
            properties[DCT.hasFormat] = URIRef(metadata_file_uri)
        self.add_properties(properties)
        if rdf_type == LDTO.Informatieobject:
            self.add_properties({
                LDTO.waardering: StructuredMetaResource._waarderingen.get_concept('B').get_uri(),
                LDTO.archiefvormer: StructuredMetaResource._actoren.get_concept(Config.get_instance().archive_creator_id).get_uri()
            })
        if metadata_file_uri:
            self.add_triple(URIRef(metadata_file_uri), RDF.type, PREMIS.File)
