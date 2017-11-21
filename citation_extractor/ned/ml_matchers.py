# -*- coding: utf-8 -*-


from __future__ import print_function
import pdb
import logging
import pkg_resources
import os
import pandas as pd
from stop_words import safe_get_stop_words
from sklearn.feature_extraction.text import TfidfVectorizer

LOGGER = logging.getLogger(__name__)

NIL_URN = 'urn:cts:GreekLatinLit:NIL'
LANGUAGES = ['en', 'es', 'de', 'fr', 'it']
PREPS = [u'di', u'da', u'of', u'von', u'de']
AUTHOR_TYPE = 'AAUTHOR'
WORK_TYPE = 'AWORK'
REFAUWORK_TYPE = 'REFAUWORK'


# TODO: how to deal with parallel computing?
# TODO: how to deal/apply with (optional?) refinement step?


class MLCitationMatcher(object):
    def __init__(self, kb=None):
        LOGGER.info('Initializing Citation Matcher')
        # TODO: Load, pre-process, ... the KB (?)
        self._kb = None
        self._feature_extractor = None
        self._ranker = None

    def train(self, train_data=None, wikipages_dir=None, include_nil=True):
        LOGGER.info('Starting training')
        # TODO: get tf-idf data from wiki texts
        tfidf = self._compute_tfidf_matrix()
        for k, v in tfidf.iteritems():
            print(k, v)
        # TODO: compute probs from train data
        # TODO: generate features for candidates (FeatureExtractor)
        # TODO: generate ranking function (SVMRank)

    def disambiguate(self, surface, scope, type, doc_title, mentions_in_title, doc_text, other_mentions, **kwargs):
        LOGGER.info('Disambiguating ...')
        # TODO: get candidates (pre-computed?)
        # TODO: generate features for candidates (FeatureExtractor)
        # TODO: rank candidates (SVMRank)
        return None

    # TODO: should be in FeatureExtractor
    def _compute_tfidf_matrix(self, base_dir=None):
        LOGGER.info('Computing TF-IDF matrix (base_dir={})'.format(base_dir))
        tfidf_data = {}

        # Compute tf-idf distribution for each language
        for lang in LANGUAGES:
            lang_data = {}

            if not base_dir:
                resources_dir = 'data/wikipages/text/authors/{}'.format(lang)
                text_authors_dir_lang = pkg_resources.resource_filename('citation_extractor', resources_dir)
                text_authors_files = pkg_resources.resource_listdir('citation_extractor', resources_dir)
            else:
                text_authors_dir_lang = os.path.join(base_dir, lang)
                text_authors_files = os.listdir(text_authors_dir_lang)

            texts = []
            urn_to_index = {}
            index = 0
            for file in text_authors_files:
                if not file.endswith('.txt'):
                    continue

                urn = file.replace('.txt', '')
                filepath = os.path.join(text_authors_dir_lang, file)
                with open(filepath) as txt_file:
                    text = txt_file.read()
                texts.append(text)
                urn_to_index[urn] = index
                index += 1

            # Dictionary mapping a URN to an index (row)
            lang_data['urn_to_index'] = urn_to_index

            tfidf_vectorizer = TfidfVectorizer(
                input='content',
                strip_accents='unicode',
                analyzer='word',
                stop_words=safe_get_stop_words(lang)
            )

            # Language-specific vectorizer
            lang_data['vectorizer'] = tfidf_vectorizer

            # Tf-idf matrix computed with the specific vectorizer
            tfidf_matrix = tfidf_vectorizer.fit_transform(texts)
            lang_data['matrix'] = tfidf_matrix

            tfidf_data[lang] = lang_data

        return tfidf_data


class FeatureExtractor(object):
    """TODO."""

    def __init__(self, kb, train_data=None):
        """Initialise an instance of FeatureExtractor.

        :param kb: instance of HuCit KnowledgeBase
        :param train_data:
        """
        LOGGER.info('Initializing Feature Extractor')
        # self.tfidf = tfidf_data
        # if kb is needed elsewhere will need to save it somewhere
        self.prior_prob = self._compute_entity_probability(kb, train_data)
        # self.me_prob = m_given_e_prob
        # self.em_prob = e_given_m_prob

    def _compute_entity_probability(self, kb, df_data):
        """Compute the probability of an entity to occur in the training data.

        :param kb: a KnowledgeBase instance
        :param df_data: a dataframe with the traning data
        :type df_data: output of `citation_extractor.Utils.IO.load_brat_data`
        :rtype: a `pandas.Dataframe` with columns: ["count", "prob"] and
                indexed by URN of author/work/NIL entity.
        """
        LOGGER.info("Computing entity probability...")

        kb_authors = [
            str(a.get_urn())
            for a in kb.get_authors()
            if a.get_urn() is not None
        ]

        kb_works = [
            str(w.get_urn())
            for a in kb.get_authors()
            for w in a.get_works()
            if w.get_urn() is not None
        ]

        idx = pd.Index(kb_works).append(pd.Index(kb_authors))
        freqs = pd.DataFrame(
            index=idx.append(pd.Index([NIL_URN])),
            dtype='float64'
        )
        freqs['count'] = 0
        freqs['prob'] = 0.0
        M = df_data.shape[0]
        N = freqs.shape[0]
        MN = M+N

        for mid, mrow in df_data.iterrows():
            urn = mrow.urn_clean
            freqs.loc[urn, 'count'] += 1

        for mid, mrow in freqs.iterrows():
            c = int(mrow['count'])
            p = float(c+1) / MN
            freqs.loc[mid, 'prob'] = p

        LOGGER.info("Done computing entity probability.")
        return freqs

    def extract_nil(self, m_type, m_scope, feature_dicts):
        LOGGER.info('Extracting NIL features for ...')
        # TODO: extract features
        return None

    def extract(self, m_surface, m_scope, m_type, m_title_mentions, m_title, m_doc_text, m_prev_entities,
                candidate_urn):
        LOGGER.info('Extracting features for ...')
        # TODO: extract features
        return None


class SVMRank(object):
    def __init__(self):
        LOGGER.info('Initializing SVM Rank')
        self._svm = None

    def fit(self, X, y, groups):
        LOGGER.info('Fitting data ...')
        # TODO: apply pairwise transform
        # TODO: (optional?) compute best C parameter (k-folded)
        # TODO: fit linear SVM

    def predict(self, x):
        LOGGER.info('Predicting ...')
        # TODO: apply dot product + sort
        return None


def main():
    logging.basicConfig(level=logging.INFO)

    matcher = MLCitationMatcher()
    matcher.train()



if __name__ == '__main__':
    main()
