# Sklearn Topic Modeling Service
A CLAMS application that wraps the sklearn topic-modeling NMF model

The sklearn topic-modeling NMF model wrapped as a CLAMS service. The spaCy NLP tool is also wrapped along with the sklearn model, since it is needed for lemmatization in the pre-processing step. spaCy is distributed under the [MIT license](https://github.com/explosion/spaCy/blob/master/LICENSE).

The codes for topic modeling are adapted from [Topic Modeling with Scikit Learn](https://blog.mlreview.com/topic-modeling-with-scikit-learn-e80d33668730) and [Topic Modeling with NMF for User Reviews Classification](https://pub.towardsai.net/topic-modeling-with-nmf-for-user-reviews-classification-65913d0b44fe). The topic-modeling NMF model is trained on 13023 NewHours transcripts, with the number of topics set to 50.

This requires Python 3.6 or higher. For local install of required Python modules do:

```bash
$ pip install clams-python==0.5.1
$ pip install spacy==3.3.1
```

In an earlier version of this application we had to manually install click==7.1.1 because clams-python installed version 8.0.1 and spaCy was not compatible with that version. The spacy install now does that automatically.

You also need the small spaCy model. Even if you have already download a model named `en_core_web_sm` with the older version of spaCy, it is important that you run the following command, because different versions of spaCy use the name `en_core_web_sm` to refer to slightly different models.

```bash
$ python -m spacy download en_core_web_sm
```

## Using this service

Use `python app.py -t input-mmif/example-transcript.json output-mmif/example-transcript.json` just to test the wrapping code without using a server. To test this using a server you run the app as a service in one terminal (when you add the optional  `--develop` parameter a Flask server will be used in development mode, otherwise you will get a production Gunicorn server):

```bash
$ python app.py [--develop]
```

And poke at it from another:

```bash
$ curl http://0.0.0.0:5000/
$ curl -H "Accept: application/json" -X POST -d@input-mmif/example-transcript.json http://0.0.0.0:5000/
```

In CLAMS you usually run this in a Docker container. To create a Docker image

```bash
$ docker build -t clams-topic-modeling .
```

And to run it as a container:

```bash
$ docker run --rm -d -p 5000:5000 clams-topic-modeling
$ curl -H "Accept: application/json" -X POST -d@input-mmif/example-transcript.json http://0.0.0.0:5000/
```

If you prefer to save the output of the app to the json file (which will be named `example-transcript.json` and saved to the folder `output-mmif`), you could run this command

```bash
$ curl -H "Accept: application/json" -X POST -d@input-mmif/example-transcript.json http://0.0.0.0:5000/?pretty=True -o output-mmif/example-transcript.json
```

The spaCy code will run on each text document in the input MMIF file. The file `input-mmif/example-transcript.json` has one view, containing one text document. The text document looks as follows:

```json
{
  "@type": "http://mmif.clams.ai/0.4.0/vocabulary/TextDocument",
  "properties": {
    "text": {
      "@value": "Hello, this is Jim Lehrer with the NewsHour on PBS...."
    },
    "id": "td1"
  }
}
```
Instead of a `text:@value` property the text could in an external file, which would be given as a URI in the `location` property. See the readme file in [https://github.com/clamsproject/app-nlp-example](https://github.com/clamsproject/app-nlp-example) on how to do this.
