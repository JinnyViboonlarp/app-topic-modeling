import os
import sys

from mmif.serialize import Mmif, Annotation
from mmif.vocabulary import AnnotationTypes, DocumentTypes
from lapps.discriminators import Uri

def annotate_input_mmif_files_without_docker():
    # this module is used to test the clams app on all transcripts, without Docker  
    in_dir = 'input-mmif'
    out_dir = 'output-mmif'
    for mmif_name in os.listdir(in_dir):
        if(mmif_name.endswith(".json")):
            in_path = in_dir + '/' + mmif_name
            out_path = out_dir + '/' + mmif_name
            os.system("python app.py -t "+in_path+" "+out_path)

def annotate_input_mmif_files():
    # this module is used to test the clams app on all transcripts, with Docker
    # the docker container must first be running
    # The commands are "docker build -t clams-topic-modeling -f Dockerfile ." \
    # and then "docker run --rm -d -p 5000:5000 clams-topic-modeling"
    in_dir = 'input-mmif'
    out_dir = 'output-mmif'  
    for mmif_name in os.listdir(in_dir):
        if(mmif_name.endswith(".json")):
            in_path = in_dir + '/' + mmif_name
            out_path = out_dir + '/' + mmif_name
            os.system('curl -H "Accept: application/json" -X POST -d@' + in_path + ' http://0.0.0.0:5000/?pretty=True -o ' + out_path)

if __name__ == "__main__":

    #annotate_input_mmif_files_without_docker()
    annotate_input_mmif_files()
