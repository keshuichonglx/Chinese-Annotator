import os
import uuid

from django.http import JsonResponse
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from werkzeug.utils import secure_filename

from apis.apiresponse import APIResponse
from apis.mongomodel import AnnotationData
from apis.serializers import APIResponseSerializer, AnnotationDataSerializer
from utils.mongoUtil import get_mongo_client
import json


UPLOAD_FOLDER = '../../data/files'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

class AnnotationDataViewSet(APIView):
    pass


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_remote_file(request):
    """
    load data from file to mongodb, this is the main interface to load data
    :return:
    """
    response = APIResponse()
    response.data = {"status": "Failed"}
    response.code = 302
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' in request.FILES:
            file = request.FILES['file']
            print(file.name)
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.name != '':
                if file and allowed_file(file.name):
                    # save file
                    filename = secure_filename(file.name)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(file_path, 'wb+')as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    # read file
                    ca = get_mongo_client(uri='mongodb://localhost:27017/')
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            text = line.strip()
                            text_uuid = uuid.uuid1()
                            annotation_data = AnnotationData(text=text, uuid=text_uuid)
                            annotation_data_serializer = AnnotationDataSerializer(annotation_data)
                            ca["annotation_data"].insert_one(annotation_data_serializer.data)
                    response.data = {"status": "success"}
                    response.code = 200
                    response.message = "Load SUCCESS"
                else:
                    response.message = "only support 'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif' file"
            else:
                response.message = "file name should not been empty"
        else:
            response.message = "no file has been upload"
    else:
        response.message = "Only support POST function"
    api_serializer = APIResponseSerializer(response)
    return JsonResponse(api_serializer.data)


def load_local_dataset(request):
    """
    load local unlabeled dataset
    :return:
    """
    if request.method == 'POST':
        file_path = request.body.get("filepath")
    else:
        file_path = request.GET.get("filepath")
    print(file_path)
    response = APIResponse()
    if os.path.exists(file_path):
        # read file
        ca = get_mongo_client(uri='mongodb://localhost:27017/')

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # label, txt = line.split(" ", 1)
                print("get string %s" % line)
                text = line.strip()
                text_uuid = uuid.uuid1()
                annotation_data = AnnotationData(text=text, uuid=text_uuid)
                annotation_data_serializer = AnnotationDataSerializer(annotation_data)
                ca["annotation_data"].insert_one(annotation_data_serializer.data)
        response.data = {"status": "success"}
        response.code = 200
        response.message = "Load SUCCESS"
    else:
        response.data = {"status": "Failed"}
        response.code = 302
        response.message = "the specified file is not exist"

    serializer = APIResponseSerializer(response)
    return JsonResponse(serializer.data)

def export_data(request):
    """
    dump data to local user instance folder
    :return:
    """
    # read file
    ca = get_mongo_client(uri='mongodb://localhost:27017/')
    with open("../../data/files/data.json", "w") as f:
        annotations = ca["annotation_data"].find({}).batch_size(50)
        result = []
        for annotation in annotations:
            data = {
                "label": annotation["label"],
                "txt": annotation["txt"],

            }
            result.append(data)
        json.dump(result, f)

    response = APIResponse()
    response.data = {"status": "success"}
    response.code = 200
    response.message = "export SUCCESS"
    serializer = APIResponseSerializer(response)
    return JsonResponse(serializer.data)


def load_single_unlabeled(request):
    """
    load one unlabeled text from Mongo DB to web
    :return:
    """
    # read file
    ca = get_mongo_client(uri='mongodb://localhost:27017/')
    text = ca["annotation_data"].find_one({"label": ""})

    annotation_data = AnnotationData(text=text.get("text"), uuid=text.get("uuid"))
    annotation_data_serializer = AnnotationDataSerializer(annotation_data)

    response = APIResponse()
    response.data = annotation_data_serializer.data
    response.code = 200
    serializer = APIResponseSerializer(response)
    return JsonResponse(serializer.data)

