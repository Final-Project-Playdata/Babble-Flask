from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from my_util.my_logger import my_logger
from datetime import datetime
from pathlib import Path
import my_util.googleSTT as stt
import os, time
from io import StringIO
import pathlib
import requests
from flask import send_file, make_response
from flask_http_response import success, result, error





# instantiate the app
app = Flask(__name__)

# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})

#-*-coding:utf-8-*-
@app.route('/STT', methods=['POST'])
def STT():
    file = request.files.get('audio')
    username = 'id121'
    file_dir = str(time.strftime("C:/audio/"+ username +"/%Y/%m/%d/"))
    pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)
    file_name = datetime.strftime(datetime.now(), (username+".%Y-%m-%dT%H-%M-%S.%f"))[:-3] + ".wav"
    file.save(os.path.join(file_dir, file_name))

    result = stt.total_api(file_dir, file_name)

    after_sound = file_dir + file_name[:-4] + '.mp3'
    
    response = make_response(send_file(after_sound))
    response.headers['result'] = result

    return response

    # 'paragraph': paragraph,
    #     'filter_paragraph' : filter_paragraph,
    #     'sensitivity' : saltlux_api('11987300804', '0', paragraph),
    #     'emotion' : saltlux_api('11987300804', '1', paragraph),
    #     'keyword' : saltlux_api('00116013830', '1', filter_paragraph)

# def csv_file_download_with_stream():
#     output_stream = StringIO()## dataframe을 저장할 IO stream 
#     temp_audio = 
#     temp_audio.to_csv(output_stream)## 그 결과를 앞서 만든 IO stream에 저장해줍니다. 
#     response = Response(
#         output_stream.getvalue(), 
#         mimetype='audio/mp3', 
#         content_type='application/octet-stream',
#     )
#     response.headers["Content-Disposition"] = "attachment; filename=after_sound.mp3"
#     return response 

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=os.getenv('FLASK_RUN_PORT'),debug=os.getenv('FLASK_DEBUG'))