#!/usr/bin/python
# -*- coding: utf-8 -*-
# author: Matteo Romanello, matteo.romanello@gmail.com

# NB
# since `pyCAS` runs only with python3, this module can be integrated into
# the master branch only once the codebase is ported to py3. For now it
# can be run more or less standalone.


from __future__ import print_function, with_statement

import codecs
import json
import os
import re

from knowledge_base import KnowledgeBase
from citation_extractor.Utils.IO import file_to_instances, write_iob_file
from citation_extractor.Utils.IO import _find_newlines, read_ann_file_new
from pyCTS import CTS_URN

INPUT_ENCODING = "UTF-8"
OUTPUT_ENCODING = "UTF-8"


# TODO: make static method of DocumentConverter
def quote(s):
    """Checks if a string is a quotation sign"""
    return s in ('"', )


# TODO: make static method of DocumentConverter
def space(t1, t2, quote_count=None):
    """Checkes whether a space should occur between two tokens"""
    # Helper for reconstructing sentence text. Given the text of two
    # consecutive tokens, returns a heuristic estimate of whether a
    # space character should be placed between them.

    if re.match(r'^[\(]$', t1):
        return False
    if re.match(r'^[.,\)\?\!]$', t2):
        return False
    if quote(t1) and quote_count is not None and quote_count % 2 == 1:
        return False
    if quote(t2) and quote_count is not None and quote_count % 2 == 1:
        return False
    return True


# TODO: move to `io.brat`
def read_text(fileid, ann_dir, suffix="-doc-1.txt"):
    """Reads text from a brat file."""
    path = os.path.join(ann_dir, fileid)
    ann_file = "{}{}".format(path, suffix)

    with codecs.open(ann_file, 'r', 'utf-8') as f:
        data = f.read()

    lines = [
        line
        for line in data.split('\n')
        if line != ""
    ]

    return "\n".join(lines)


def urn2uri(kb, input_urn):
    resource = kb.get_resource_by_urn(input_urn)
    return str(resource.subject)


class DocumentConverter(object):
    """DocumentConverter transforms legacy data into UIMA/XML format.

    TODO: explain assumptions about data format.

    Usage:
    >>> iob_file = ''
    >>> standoff_dir = ''
    >>> typesystem_path = ''
    >>> doc_conv = DocumentConverter()
    >>> doc_conv.load(iob_file, standoff_dir)
    >>> doc_conv.to_xmi('', typesystem_path)
    """
    def __init__(self, knowledge_base=None):
        if knowledge_base is not None:
            self._kb = knowledge_base
        else:
            raise  # TODO: raise a custom exception (?)
        return

    def load(self, iob_file_path, standoff_dir):
        self.document_id = os.path.basename(iob_file_path)
        self.document_name = os.path.basename(iob_file_path).split('.')[0]
        self._iob_file_path = iob_file_path
        self._standoff_dir = standoff_dir

        self._iob_data = self._parse_iob(self._iob_file_path)
        self._iob_standoff = self._get_start_end(self._iob_data)
        self._pos_tags = [
            [
                token[1]
                for token in sentence
            ]
            for sentence in file_to_instances(self._iob_file_path)
        ]
        self.tokens = [
            {
                'surface': token[0],
                'start_offset': token[1],
                'end_offset': token[2],
                'pos_tag': self._pos_tags[sentence_n][token_n]
            }
            for sentence_n, sentence in enumerate(self._iob_standoff)
            for token_n, token in enumerate(sentence)
        ]

        so_entities, so_relations, so_annotations = read_ann_file_new(
            self.document_id,
            self._standoff_dir
        )

        self.entities = {
            ent_id: {
                'ann_id': so_entities[ent_id]["ann_id"],
                'entity_type': so_entities[ent_id]["entity_type"],
                'surface': so_entities[ent_id]["surface"],
                'start_offset': int(so_entities[ent_id]["offset_start"]),
                'end_offset': int(so_entities[ent_id]["offset_end"]),
            }
            for ent_id in so_entities
        }

        self.relations = so_relations
        self.disambiguations = {
            ann['anchor']: ann
            for ann in so_annotations
        }

        text = read_text(self.document_id, self._standoff_dir)
        self.text = text

        self._line_breaks = _find_newlines(text)
        self._convert_disambiguations()
        return

    def _convert_disambiguations(self):

        for entity_id in self.entities:
            entity = self.entities[entity_id]

            if entity_id not in self.disambiguations:
                continue

            disambiguation = self.disambiguations[entity_id]
            urn = CTS_URN(disambiguation['text'])

            entity['urn'] = str(urn)
            uri = urn2uri(
                self._kb,
                urn.get_urn_without_passage()
            )

            if entity['entity_type'] == 'AAUTHOR':
                entity['author_uri'] = uri
            else:
                entity['work_uri'] = uri

        for relation in self.relations:

            if relation not in self.disambiguations:
                continue

            disambiguation = self.disambiguations[relation]
            args = self.relations[relation]['arguments']
            arg1 = self.entities[args[0]]
            arg2 = self.entities[args[1]]

            # transfer the scope from the relation onto the entity
            urn = CTS_URN(disambiguation['text'])
            scope = urn.passage_component
            arg2['norm_scope'] = scope

            # transfer the disambiguation to the corresponding entity
            uri = urn2uri(
                self._kb,
                urn.get_urn_without_passage()
            )
            if arg1['entity_type'] == 'AAUTHOR':
                arg1['author_uri'] = uri
            else:
                arg1['work_uri'] = uri
        return

    def _parse_iob(self, fn):
        """TODO."""
        docnum = 1
        sentences = []

        assert fn is not None

        with codecs.open(fn, encoding=INPUT_ENCODING) as f:

            # store (token, BIO-tag, type) triples for sentence
            current = []

            lines = f.readlines()

            for ln, l in enumerate(lines):
                l = l.strip()

                if re.match(r'^\s*$', l):
                    # blank lines separate sentences
                    if len(current) > 0:
                        sentences.append(current)
                    current = []
                    continue
                elif (re.match(r'^===*\s+O\s*$', l) or
                      re.match(r'^-DOCSTART-', l)):
                    # special character sequence separating documents
                    #if len(sentences) > 0:
                    #    output(fn, docnum, sentences)
                    sentences = []
                    docnum += 1
                    continue

                if (ln + 2 < len(lines) and
                    re.match(r'^\s*$', lines[ln+1]) and
                    re.match(r'^-+\s+O\s*$', lines[ln+2])):
                    # heuristic match for likely doc before current line
                    #if len(sentences) > 0:
                    #    output(fn, docnum, sentences)
                    sentences = []
                    docnum += 1
                    # go on to process current normally

                # Assume it's a normal line. The format for spanish is
                # is word and BIO tag separated by space, and for dutch
                # word, POS and BIO tag separated by space. Try both.
                m = re.match(r'^(\S+)\s(\S+)$', l)
                if not m:
                    m = re.match(r'^(\S+)\s\S+\s(\S+)$', l)
                assert m, "Error parsing line %d: %s" % (ln+1, l)
                token, tag = m.groups()

                # parse tag
                m = re.match(r'^([BIO])((?:-[A-Za-z_]+)?)$', tag)
                assert m, "ERROR: failed to parse tag '%s' in %s" % (tag, fn)
                ttag, ttype = m.groups()
                if len(ttype) > 0 and ttype[0] == "-":
                    ttype = ttype[1:]

                current.append((token, ttag, ttype))

            # process leftovers, if any
            if len(current) > 0:
                sentences.append(current)
        return sentences

    def _get_start_end(self, sentences):
        """TODO."""
        offset, idnum = 0, 1
        doctext = ""
        sents = []
        for si, sentence in enumerate(sentences):

            prev_token = None
            prev_tag = "O"
            curr_start, curr_type = None, None
            quote_count = 0
            sent = []
            for token, ttag, ttype in sentence:

                if (
                    prev_token is not None and
                    space(prev_token, token, quote_count)
                ):
                    doctext = doctext + ' '
                    offset += 1

                curr_start = offset

                if curr_type is None and ttag != "O":
                    # a new tagged sequence begins here
                    curr_start, curr_type = offset, ttype

                doctext = doctext + token
                offset += len(token)

                if quote(token):
                    quote_count += 1

                prev_token = token
                prev_tag = ttag
                assert token == doctext[curr_start:offset]
                sent.append((token, curr_start, offset))
            sents.append(sent)

            if si + 1 != len(sentences):
                doctext = doctext + '\n'
                offset += 1
        return sents

    # NB: not for now
    def to_xmi(self, output_dir, typesystem):

        # if output_dir does not exist, create it!

        # call create_xmi()

        pass

    def to_json(self, output_dir=None):
        """Serializes the converted document to JSON.

        :param output_dir: the destination directory
        :type output_dir: str
        """

        output = {
            'text': self.text,
            'doc_id': self.document_id,
            'doc_name': self.document_name,
            # TODO: add `postag`
            'tokens': self.tokens,
            'linebreaks': self._line_breaks,
            'relations': self.relations,
            'entities': self.entities,
            'disambiguations': self.disambiguations
        }
        filename = "{}.json".format(output['doc_name'])

        if output_dir is not None:
            with open(os.path.join(output_dir, filename), 'w') as outfile:
                json.dump(output, outfile, indent=3)

        return json.dumps(output)

    def to_iob(self, output_dir, extension='iob'):
        """Serialize the converted document as an IOB file.

        :param output_dir:
        :type output_dir: str
        :param: extension:
        :type extension: str
        :returns: a list of lists
        """
        iob_data = []
        fname = "{}.{}".format(self.document_name, extension)
        fpath = os.path.join(output_dir, fname)

        start_pos = 0

        # read the document sentence by sentence (using sentence offsets)
        for lb, next_pos in self._line_breaks:

            sentence_data = []

            # retain only the tokens belonging to the current sentence
            tokens = [
                token
                for token in self.tokens
                if token['start_offset'] >= start_pos and
                token['end_offset'] <= lb
            ]

            for token in tokens:
                start = token['start_offset']
                end = token['end_offset']
                nes = [
                    e
                    for e in self.entities.values()
                    if start >= e['start_offset'] and end <= e['end_offset']
                ]
                if len(nes) > 0:
                    e = nes[0]
                    prefix = "I" if start > e['start_offset'] else "B"
                    ne_tag = "{}-{}".format(prefix, e["entity_type"])
                else:
                    ne_tag = 'O'
                sentence_data.append(
                    (token["surface"], token["pos_tag"], ne_tag)
                )

            # append the sentece to the output
            iob_data.append(sentence_data)
            start_pos = next_pos

        return write_iob_file(iob_data, fpath)


def main():
    kb = KnowledgeBase('/Users/rromanello/Documents/ClassicsCitations/hucit_kb/knowledge_base/config/virtuoso.ini')
    standoff_dir = '/Users/rromanello/Documents/ClassicsCitations/epibau/processing/data/ann/'
    iob_file = '/Users/rromanello/Documents/ClassicsCitations/epibau/processing/data/iob_ne/Behm__Cities.docx.txt'
    out_dir = "/Users/rromanello/Downloads/converted_docs/"
    doc_conv = DocumentConverter(kb)
    doc_conv.load(iob_file, standoff_dir)
    # doc_conv.to_json(out_dir)
    iob = doc_conv.to_iob(out_dir)


if __name__ == '__main__':
    main()
