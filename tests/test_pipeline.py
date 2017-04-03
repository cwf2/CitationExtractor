# -*- coding: utf-8 -*-
# author: Matteo Romanello, matteo.romanello@gmail.com

import os
import pdb
import pytest
import logging
import pkg_resources
from citation_extractor.pipeline import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_read_ann_file_new():
	dir = pkg_resources.resource_filename('citation_extractor','data/aph_corpus/goldset/ann/')
	files = [file.replace('-doc-1.ann','') for file in pkg_resources.resource_listdir('citation_extractor','data/aph_corpus/goldset/ann/') if '.ann' in file]
	for file in files[:10]:
		logger.debug(file)
		entities,relations,annotations = read_ann_file_new(file,dir)
		logger.debug("Entities: %s"%entities)
		for rel_id in relations:
			logger.debug(relations[rel_id])
			for entity_id in relations[rel_id]["arguments"]:
				assert entities.has_key(entity_id)
		logger.debug(annotations)
		for annotation in annotations:
			assert (relations.has_key(annotation["anchor"]) or entities.has_key(annotation["anchor"])) 
def test_tokenize_string(aph_title, postaggers):
	lang = detect_language(aph_title)
	postagged_string = postaggers[lang].tag(aph_title) 
	logger.debug(postagged_string)
	assert postagged_string is not None
def test_preprocessing(processing_directories, postaggers):
	"""
	Test the pre-processing step of the pipeline (against selected APh documents in the devset).
	"""
	inp_dir = processing_directories["input"]
	docids = ["75-00557.txt", "75-00351.txt", "75-00087.txt", "75-00060.txt", "75-00046.txt"]
	abbreviations = pkg_resources.resource_filename('citation_extractor', 'data/aph_corpus/extra/abbreviations.txt')
	interm_dir = processing_directories["txt"]
	out_dir = processing_directories["iob"]
	for docid in docids:
		logger.info(preproc_document(docid, inp_dir, interm_dir, out_dir, abbreviations, postaggers, False))
	assert len(os.listdir(out_dir)) > 0
def test_do_ner(processing_directories, crf_citation_extractor):
	"""
	Test the Named Entity Recognition step of the pipeline.
	"""
	brat_script_path = pkg_resources.resource_filename('citation_extractor', 'Utils/conll02tostandoff.py')
	inp_dir = processing_directories["iob"]
	interm_dir = processing_directories["iob_ne"]
	out_dir = processing_directories["ann"]
	docids = os.listdir(inp_dir)
	for docid in docids:
		logger.info(do_ner(docid, inp_dir, interm_dir, out_dir, crf_citation_extractor, brat_script_path))
	assert len(os.listdir(out_dir)) > 0
def test_do_relex_rulebased(processing_directories):
	"""
	Test the Relation Extraction step of the pipeline.
	"""
	inp_dir = processing_directories["ann"]
	docids = [file.replace('-doc-1.ann','') for file in os.listdir(inp_dir) if '.ann' in file]
	logger.info(docids)
	for docid in docids:
		docid, success, data = do_relex(docid, inp_dir)
		logger.info(data)
		assert success
def test_do_ned(processing_directories, citation_matcher):
	"""
	Test the Named Entity Disambiguation step of the pipeline (baseline).
	"""
	inp_dir = processing_directories["ann"]
	docids = [file.replace('-doc-1.ann','') for file in os.listdir(inp_dir) if '.ann' in file]
	for docid in docids:
		docid, success, n_disambiguations = do_ned(docid, inp_dir, citation_matcher, True, 0, False)
		assert success
