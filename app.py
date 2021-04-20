from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from my_util.my_logger import my_logger
from datetime import datetime
from pathlib import Path
import my_util.googleSTT as stt
import os
import time
from io import StringIO
import pathlib
import requests
from flask import send_file, make_response
from flask_http_response import success, result, error

# instantiate the app
app = Flask(__name__)

# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})

# -*-coding:utf-8-*-


@app.route('/STT', methods=['POST'])
def STT():
    print(request)
    file = request.files.get('audio')
    print(file)
    print('===========================')

    # if '..' in file.filename or 'audio/wav' != file.mimetype:
    #     return 'error'

    file_dir = str(time.strftime(
        "C:/audiotest/" + file.filename + "/%Y/%m/%d/"))

    pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)

    file_name = datetime.strftime(
        datetime.now(), (file.filename + ".%Y-%m-%d-%H-%M-%S")) + ".wav"

    file.save(os.path.join(file_dir, file_name))

    result = stt.total_api(file_dir, file_name)

    return result


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv(
        'FLASK_RUN_PORT'), debug=os.getenv('FLASK_DEBUG'))
