from google.cloud import speech
from pydub import AudioSegment
AudioSegment.converter = r"C:\ITStudy\STT\ffmpeg\bin\ffmpeg.exe"
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify
import speech_recognition as sr
import numpy as np
import io, os
import urllib3
import json, requests
import base64

import time
import pathlib

def open_audio(file_dir, file_name):
    with io.open(file_dir + file_name, "rb") as f:
        return f.read()

def sample_recognize(file_dir, file_name):
    client = speech.SpeechClient()
    language_code = "ko-KR"
    sample_rate_hertz = 48000
    encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    config = {
        "language_code": language_code,
        "sample_rate_hertz": sample_rate_hertz,
        "encoding": encoding,
        "enable_word_time_offsets": True,
        "use_enhanced": True
    }

    # with io.open(file_dir + file_name, "rb") as f:
    #     audio_file = f.read()
    # audio = {"content": audio_file}
    audio = {"content": open_audio(file_dir, file_name)}
    response = client.recognize(config=config, audio=audio)

    profanityfilter = ['시발', '씨발', '시발놈아', '씨발놈아', '존나', '지랄', '미친새끼', '새끼가', '병신', '개새끼야', '지랄이야', '씹새끼야']
    timeline, swear_timeline, words, filter_words = [], [], [], []
    paragraph = ''
    filter_paragraph = ''

    for result in response.results:
        alternative = result.alternatives[0]
        for word in alternative.words[1:]:
            timeline.append([
                int(word.start_time.seconds * 1000 + word.start_time.nanos * (10**-6)),
                int(word.end_time.seconds * 1000 + word.end_time.nanos * (10**-6))
            ])
            
            words.append(word.word)
            paragraph = " ".join(words)

            if word.word in profanityfilter:
                filter_words.append('*')
                filter_paragraph = " ".join(filter_words)
                swear_timeline.append([
                    int(word.start_time.seconds * 1000 + word.start_time.nanos * (10**-6)),
                    int(word.end_time.seconds * 1000 + word.end_time.nanos * (10**-6))
                ])
            else:
                filter_words.append(word.word)
                filter_paragraph = " ".join(filter_words)


    return swear_timeline, paragraph, filter_paragraph

def create_beep(duration):
    sps = 48000
    freq_hz = 1000.0
    vol = 0.8

    esm = np.arange(duration / 1020 * sps)
    wf = np.sin(2 * np.pi * esm * freq_hz / sps)
    wf_quiet = wf * vol
    wf_int = np.int16(wf_quiet * 32767)

    beep = AudioSegment(
        wf_int.tobytes(), 
        frame_rate=sps,
        sample_width=wf_int.dtype.itemsize, 
        channels=1
    )

    return beep

def saltlux_api(service_id, type_number, text):
    params = {
        'key': "407370b5-44b0-4f96-8d9d-182c67a7d08a",
        'serviceId': service_id,
        'argument': {
            "type": type_number
        }
    }

    result = []

    if service_id == "11987300804":
        params['argument']['query'] = text
        result = saltlux_api_post(params)
        if type_number == '0':
            return [ result['label'] ]
        else:
            return [ word[1] for word in result['Result'] ]
    elif service_id == "00116013830":
        params['argument']['question'] = text
        result = saltlux_api_post(params)
        return [ word['keyword'] for word in result['return_object']['keylists'] ]

def saltlux_api_post(params):
    url = 'http://svc.saltlux.ai:31781'
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    response = requests.post(url, headers = headers, data = json.dumps(params))
    response_json = json.loads(response.content.decode("utf-8", errors='ignore'))
    return response_json

#-*-coding:utf-8-*-
def total_api(file_dir, file_name):
    swear_timeline, paragraph, filter_paragraph = sample_recognize(file_dir, file_name)
    sound = AudioSegment.from_wav(file_dir + file_name)
    beep = create_beep(duration=1030)
    print('swear_timeline', swear_timeline)
  
    if swear_timeline:
        for i in range(len(swear_timeline)):
            beep = create_beep(duration=swear_timeline[i][1] - swear_timeline[i][0])
            sound = sound.overlay(beep, position=swear_timeline[i][0], gain_during_overlay=-20)
    #     after_sound = sound.export(file_dir + file_name[:-4] + '.mp3', format='mp3')
    # else: after_sound = sound.export(file_dir + file_name[:-4] + '.mp3', format='mp3')
    sound.export(file_dir + file_name[:-4] + '.mp3', format='mp3')

    # before_sound = open_audio(file_dir, file_name)
    # after_sound = open_audio(file_dir, file_name[:-4] + '.mp3')

    collection = {
        'paragraph': paragraph,
        'filter_paragraph' : filter_paragraph,
        'sensitivity' : saltlux_api('11987300804', '0', paragraph),
        'emotion' : saltlux_api('11987300804', '1', paragraph),
        'keyword' : saltlux_api('00116013830', '1', filter_paragraph)
    }
    print(type(paragraph))
    result = json.dumps(collection, ensure_ascii=False).encode('utf-8')
    # result = json.dumps(collection, ensure_ascii=False).decode('cp949').encode('utf-8')


    return result
