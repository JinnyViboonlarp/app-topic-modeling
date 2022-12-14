"""app.py

Wrapping sklearn NMF model to extract topic from documents.
spaCy model is also used for preprocessing(lemmatization), and so it is wrapped too.

Usage:

$ python app.py -t input-mmif/example-transcript.json output-mmif/example-transcript.json
$ python app.py [--develop]

The first invocation is to just test the app without running a server. The
second is to start a server, which you can ping with

$ curl -H "Accept: application/json" -X POST -d@input-mmif/example-transcript.json http://0.0.0.0:5000/

With the --develop option you get a FLask server running in development mode,
without it Gunicorn will be used for a more stable server.

Normally you would run this in a Docker container, see README.md.

"""

import os
import sys
import collections
import json
import urllib
import argparse
import pickle

import numpy as np
import spacy

from clams.app import ClamsApp
from clams.restify import Restifier
from clams.appmetadata import AppMetadata
from mmif.serialize import Mmif
from mmif.vocabulary import AnnotationTypes, DocumentTypes
from lapps.discriminators import Uri

Uri_TOPIC = 'http://vocab.lappsgrid.org/Topic' # empty link

# Load small English core model
nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])

# Load sklearn nmf model
nmf_folder = 'nmf-model'
nmf = pickle.load(open(nmf_folder+'/nmf.sav', 'rb'))
tfidf_feature_names = pickle.load(open(nmf_folder+'/tfidf_feature_names.sav', 'rb'))
tfidf_vectorizer = pickle.load(open(nmf_folder+'/tfidf_vectorizer.sav', 'rb'))

APP_VERSION = '0.1.0'
APP_LICENSE = 'Apache 2.0'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.6'
CLAMS_PYTHON_VERSION = '0.5.1'
SKLEARN_VERSION = '1.1.1'
SKLEARN_LICENSE = 'BSD-3C'
#SPACY_VERSION = '3.3.1'
#SPACY_LICENSE = 'MIT'


# We need this to find the text documents in the documents list
TEXT_DOCUMENT = os.path.basename(str(DocumentTypes.TextDocument))

DEBUG = False

num_topic_display = 5
topic_id_skipped = 25 # the topic that doesn't look good, and so would be skipped

# find the list of words for each topic
num_top_words = 10
def find_words_for_topics(model, feature_names, num_top_words):
    topic_to_words = dict()
    for topic_idx, topic in enumerate(model.components_):
        topic_to_words[topic_idx] = " ".join([feature_names[i] for i in topic.argsort()[:-num_top_words - 1:-1]])
    return topic_to_words
topic_to_words = find_words_for_topics(nmf, tfidf_feature_names, num_top_words)

class TopicModelingApp(ClamsApp):

    def _appmetadata(self):
        
        metadata = AppMetadata(
            identifier='https://apps.clams.ai/sklearn_topic_modeling',
            url='https://github.com/clamsproject/app-topic-modeling',
            name="sklearn Topic Modeling",
            description="Apply sklearn Topic Modeling to all text documents in a MMIF file.",
            app_version=APP_VERSION,
            app_license=APP_LICENSE,
            analyzer_version=SKLEARN_VERSION,
            analyzer_license=SKLEARN_LICENSE,
            mmif_version=MMIF_VERSION
        )
        metadata.add_input(DocumentTypes.TextDocument)
        metadata.add_output(Uri_TOPIC)
        return metadata

    def _annotate(self, mmif, **kwargs):
        Identifiers.reset()
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        for doc in text_documents(self.mmif.documents):
            new_view = self._new_view(doc.id)
            self._add_tool_output(doc, new_view)
        for view in list(self.mmif.views):
            docs = self.mmif.get_documents_in_view(view.id)
            if docs:
                new_view = self._new_view()
                for doc in docs:
                    doc_id = view.id + ':' + doc.id
                    self._add_tool_output(doc, new_view, doc_id=doc_id)
        return self.mmif

    def _new_view(self, docid=None):
        view = self.mmif.new_view()
        self.sign_view(view)
        view.new_contain(Uri_TOPIC, document=docid)
        return view

    def _read_text(self, textdoc):
        """Read the text content from the document or the text value."""
        if textdoc.location:
            fh = urllib.request.urlopen(textdoc.location)
            text = fh.read().decode('utf8')
        else:
            text = textdoc.properties.text.value
        if DEBUG:
            print('>>> %s%s' % (text.strip()[:100],
                                ('...' if len(text) > 100 else '')))
        return text

    def _add_tool_output(self, doc, view, doc_id=None):

        text = self._read_text(doc)

        def lemmatize(text):
            doc = nlp(text) # pass the document through the spaCy NLP model
            new_text = " ".join([token.lemma_ for token in doc])
            new_text = new_text.replace(" \n\n ","\n\n")
            start = doc[0].idx # start index of the document
            end = doc[-1].idx + len(doc[-1].text) # end index of the document
            return (new_text, start, end)

        (text, start, end) = lemmatize(text)
        weights = nmf.transform(tfidf_vectorizer.transform([text]))[0]
        # 'weights' is an np.array of size (num_topics)
        # weights[i] is the (unnormalized) likelihood of the text having the topic i
        weights[topic_id_skipped] = 0 # set probability of the topic that doesn't \
        # look good to zero
        weights = (weights/np.sum(weights)) # normalize the likelihood
        topics_id = weights.argsort()[::-1]
        for i in range(num_topic_display):
            topic_id = topics_id[i]
            add_annotation(
                view, Uri_TOPIC, Identifiers.new("tp"),
                doc_id, start, end,
                {"topic_id": int(topic_id), "topic": topic_to_words[topic_id],
                "likelihood": weights[topic_id]})

    def print_documents(self):
        for doc in self.mmif.documents:
            print("%s %s location=%s text=%s" % (
                doc.id, doc.at_type, doc.location, doc.properties.text.value))


def text_documents(documents):
    """Utility method to get all text documents from a list of documents."""
    return [doc for doc in documents if str(doc.at_type).endswith(TEXT_DOCUMENT)]
    # TODO: replace with the following line and remove TEXT_DOCUMENT variable
    # when mmif-python is updated
    # return [doc for doc in documents if doc.is_type(DocumentTypes.TextDocument)]


def add_annotation(view, attype, identifier, doc_id, start, end, properties):
    """Utility method to add an annotation to a view."""
    a = view.new_annotation(attype, identifier)
    if doc_id is not None:
        a.add_property('document', doc_id)
    if start is not None:
        a.add_property('start', start)
    if end is not None:
        a.add_property('end', end)
    for prop, val in properties.items():
        a.add_property(prop, val)

class Identifiers(object):

    """Utility class to generate annotation identifiers. You could, but don't have
    to, reset this each time you start a new view. This works only for new views
    since it does not check for identifiers of annotations already in the list
    of annotations."""

    identifiers = collections.defaultdict(int)

    @classmethod
    def new(cls, prefix):
        cls.identifiers[prefix] += 1
        return "%s%d" % (prefix, cls.identifiers[prefix])

    @classmethod
    def reset(cls):
        cls.identifiers = collections.defaultdict(int)



def test(infile, outfile):
    """Run spacy on an input MMIF file. This bypasses the server and just pings
    the annotate() method on the SpacyApp class. Prints a summary of the views
    in the end result."""
    print(TopicModelingApp().appmetadata(pretty=True))
    with open(infile) as fh_in, open(outfile, 'w') as fh_out:
        mmif_out_as_string = TopicModelingApp().annotate(fh_in.read(), pretty=True)
        mmif_out = Mmif(mmif_out_as_string)
        fh_out.write(mmif_out_as_string)
        for view in mmif_out.views:
            print("<View id=%s annotations=%s app=%s>"
                  % (view.id, len(view.annotations), view.metadata['app']))


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test',  action='store_true', help="bypass the server")
    parser.add_argument('--develop',  action='store_true', help="start a development server")
    parser.add_argument('infile', nargs='?', help="input MMIF file")
    parser.add_argument('outfile', nargs='?', help="output file")
    args = parser.parse_args()

    if args.test:
        test(args.infile, args.outfile)
    else:
        app = TopicModelingApp()
        service = Restifier(app)
        if args.develop:
            service.run()
        else:
            service.serve_production()
