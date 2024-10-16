import os
import shutil

from datetime import datetime
from rdflib import URIRef, BNode

from razuconfig import RazuConfig
from concept_resolver import ConceptResolver
from meta_resource import StructuredMetaResource
from meta_graph import MetaGraph
from manifest import Manifest

import util as util


class Sip:
    def __init__(self, sip_dir, archive_creator_id, dataset_id: str) -> None:
        self.sip_dir = sip_dir
        self.archive_creator_id = archive_creator_id
        self.dataset_id = dataset_id
        self.meta_resources = {}

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=archive_creator_id, archive_id=dataset_id, save_dir=sip_dir, save=True)

        if not os.path.exists(self.sip_dir):
            os.makedirs(self.sip_dir)
            print(f"Created empty SIP at {self.sip_dir}.")

        self.manifest = Manifest(self.sip_dir, self.cfg.manifest_filename)
        self._load_graph()

        # if newest_id is None:
        #     self.newest_id = self.manifest.newest_id
        #     if self.manifest.newest_id > 0:
        #         self._load_graph()
        # else:
        #     if self.manifest.newest_id > 0:
        #         print ("Existing files will be overwritten.")
        #     self.newest_id = newest_id

    def _load_graph(self):
        for filename in self.manifest.get_filenames():
            if filename.endswith(f"{self.cfg.metadata_suffix}.json"):
                file_path = os.path.join(self.sip_dir, filename)
                id = util.extract_id_from_filename(file_path)
                self.meta_resources[id] = StructuredMetaResource(id=id)
                self.meta_resources[id].load(file_path)

    def save_graph(self):
        """
        For each entity in the graph with a URI, create a MetaObject, fill it with the relevant
        properties, and save it as a JSON-LD file.
        """
        def add_related_triples_to_meta_object(meta_object, node):
            """ Recursively add triples related to the given node (including blank nodes) to the MetaObject. """
            for predicate, obj in self.graph.predicate_objects(node):
                meta_object.add(predicate, obj)
                if isinstance(obj, BNode):
                    add_related_triples_to_meta_object(meta_object, obj)

        for subject in self.graph.subjects():
            if isinstance(subject, URIRef): 
                meta_object = StructuredMetaResource(uri=subject)
                add_related_triples_to_meta_object(meta_object, subject)
                self.store_object(meta_object)

    def create_object(self, **kwargs):
        # TODO: identifiers kunnen de mist in gaan als zowel een uri wordt meegegeven als soms ook vertrouwd wordt op
        # automatische toekenning met self.newest_id
        valid_kwargs = {}
        if 'entity_id' not in kwargs:
            self.newest_id += 1
            valid_kwargs['entity_id'] = self.newest_id
        else:
            valid_kwargs['entity_id'] = kwargs['entity_id']

        if 'rdf_type' in kwargs:
            valid_kwargs['rdf_type'] = kwargs['rdf_type']
        return StructuredMetaResource(**valid_kwargs)

    def store_object(self, object: StructuredMetaResource, source_dir = None):
        # process the metadata-file:
        self.graph += object
        object.save()
        md5checksum = self.manifest.calculate_md5(object.meta_file_path)
        md5date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.manifest.add_entry(object.meta_filename, md5checksum, md5date) 
        self.manifest.update_entry(object.meta_filename, {
            "ObjectUID": object.object_identifier,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id
        })
        
        # process the (optional) referenced file:
        if source_dir is not None:
            origin_filepath = os.path.join(source_dir, object.original_filename)
            dest_filepath  = os.path.join(self.sip_dir, object.filename)
            shutil.copy2(origin_filepath, dest_filepath)

            self.manifest.add_entry(object.filename, object.md5checksum, object.checksum_datetime) 
            self.manifest.update_entry(object.filename, {
                "ObjectUID": object.object_identifier,
                "Source": self.archive_creator_uri,
                "Dataset": self.dataset_id,
                "FileFormat": object.fileformat_uri,
                "OriginalFilename": object.original_filename
            })
        self.manifest.save()

    def validate(self):
        self.manifest.verify()
