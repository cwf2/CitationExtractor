"""Tests for the module `citation_extractor.ned`."""
# -*- coding: utf-8 -*-
# author: Matteo Romanello, matteo.romanello@gmail.com

import ipdb as pdb
import pytest
import logging
import pickle
from citation_extractor.pipeline import NIL_URN
from citation_extractor.ned.candidates import CandidatesGenerator
from citation_extractor.ned.ml import LinearSVMRank
from citation_extractor.ned.matchers import MLCitationMatcher
import random

logger = logging.getLogger(__name__)


# TODO: move this test somewhere else
@pytest.mark.skip
def test_pickle_kb(knowledge_base):
    """Tests whether instances of `KnowledgeBase` can be pickled."""
    pickled_kb = pickle.dumps(knowledge_base)
    unpickled_kb = pickle.loads(pickled_kb)
    logger.info(
        "The KnowledgeBase contains %i author names" % len(
            unpickled_kb.author_names
        )
    )


@pytest.mark.skip
def test_pickle_citation_matcher(citation_matcher):
    """Test whether instances of `CitationMatcher` can be pickled."""
    pickled_citation_matcher = pickle.dumps(citation_matcher)
    unpickled_citation_matcher = pickle.loads(pickled_citation_matcher)


def test_extract_features(feature_extractor_quick, aph_testset_dataframe):
    fe = feature_extractor_quick
    test_df_data = aph_testset_dataframe

    logger.debug(test_df_data.info())

    for id_row, row in test_df_data.iterrows():
        if row["urn"] != NIL_URN:
            # TODO: should be called on the candidates!
            # and `fv` should be a list
            fv = fe.extract(
                row["surface_norm"],
                row["scope"],
                row["type"],
                row["doc_title_mentions"],
                row["doc_title_norm"],
                row["doc_text"],
                row["other_mentions"],
                row["urn_clean"]
            )
            logger.info(
                "Feature vector for {} {}: {}".format(
                    row["surface_norm"],
                    row["scope"],
                    fv
                )
            )
            nfv = fe.extract_nil(row["type"], row["scope"], [fv])
            logger.info(
                "Feature vector (nil) for {} {}: {}".format(
                    row["surface_norm"],
                    row["scope"],
                    nfv
                )
            )
        else:
            logger.debug("Skipped {}".format(row))


def test_candidate_generator(
    feature_extractor_quick,
    knowledge_base,
    aph_testset_dataframe
):

    fe = feature_extractor_quick
    _kb_norm_authors = fe._kb_norm_authors
    _kb_norm_works = fe._kb_norm_works

    cg = CandidatesGenerator(
        knowledge_base,
        kb_norm_authors=_kb_norm_authors,
        kb_norm_works=_kb_norm_works
    )

    for mention_id, row in aph_testset_dataframe.iterrows():

        surface = row['surface_norm_dots']
        scope = row['scope']
        entity_type = row['type']

        candidates = cg.generate_candidates(surface, entity_type, scope)
        logger.info(
            'Generated {} candidates for {}'.format(
                len(candidates),
                mention_id
            )
        )


def test_generate_candidates_parallel(
    feature_extractor_quick,
    knowledge_base,
    aph_testset_dataframe
):
    fe = feature_extractor_quick
    _kb_norm_authors = fe._kb_norm_authors
    _kb_norm_works = fe._kb_norm_works

    cg = CandidatesGenerator(
        knowledge_base,
        kb_norm_authors=_kb_norm_authors,
        kb_norm_works=_kb_norm_works
    )

    candidates = cg.generate_candidates_parallel(
        aph_testset_dataframe
    )
    logger.debug(candidates)


@pytest.mark.skip
def test_ml_citation_matcher(
    feature_extractor_quick,
    aph_testset_dataframe,
    aph_goldset_dataframe
):
    cm = MLCitationMatcher(feature_extractor_quick, aph_goldset_dataframe)
    # TODO: finish




def test_svm_rank():
    lowb, upperb, shift = 0, 1, 1

    # Generate two groups with 3 points each
    X = [
        dict(x=random.uniform(lowb, upperb), y=random.uniform(lowb, upperb)),
        dict(x=random.uniform(lowb, upperb), y=random.uniform(lowb, upperb)),
        dict(x=random.uniform(lowb, upperb) + shift, y=random.uniform(
            lowb,
            upperb
        ) + shift),  # true one
        dict(x=random.uniform(lowb, upperb), y=random.uniform(lowb, upperb)),
        dict(x=random.uniform(lowb, upperb), y=random.uniform(lowb, upperb)),
        dict(x=random.uniform(lowb, upperb) + shift, y=random.uniform(
            lowb,
            upperb
        ) + shift)  # true one
    ]
    print(X)
    y = [
        0,
        0,
        1,
        0,
        0,
        1
    ]
    print(y)
    groups = [
        0,
        0,
        0,
        1,
        1,
        1
    ]
    print(groups)

    # Fit the ranker
    ranker = LinearSVMRank()
    ranker.fit(X=X, y=y, groups=groups)

    # Generate a group of three points, the second (index=1) is the true one
    candidates = [
        dict(x=random.uniform(lowb, upperb), y=random.uniform(lowb, upperb)),
        dict(x=random.uniform(lowb, upperb) + shift, y=random.uniform(
            lowb,
            upperb
        ) + shift),  # true one
        dict(x=random.uniform(lowb, upperb), y=random.uniform(lowb, upperb))
    ]

    # Predict
    ranked_candidates, scores = ranker.predict(candidates)
    winner_index = ranked_candidates[0]

    assert winner_index == 1
