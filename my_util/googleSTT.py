from elasticsearch import Elasticsearch, helpers
import requests
import json
import os
import io
import pathlib
import time
import base64
import urllib3
import numpy as np
from flask import Flask, jsonify
from pathlib import Path
from datetime import datetime
from google.cloud import speech
from collections import Counter
import my_util.BadWord as BadWord
from pydub import AudioSegment
from pydub.silence import split_on_silence
AudioSegment.converter = r"C:\\ITstudy\\12.project\\Babble-Flask\\ffmpeg\\bin\\ffmpeg.exe"


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

    audio = {"content": open_audio(file_dir, file_name)}
    response = client.recognize(config=config, audio=audio)

    timeline, swear_timeline, words, filter_words = [], [], [], []
    paragraph = ''
    filter_paragraph = ''
    profanityfilter = BadWord.load_badword_model()

    for result in response.results:
        alternative = result.alternatives[0]
        timeline.append(
            [0, int(alternative.words[0].end_time.seconds * 1000 + 500)])
        words.append(alternative.words[0].word)
        for word in alternative.words[1:]:
            timeline.append([
                int(word.start_time.seconds * 1000 +
                    word.start_time.nanos * (10**-6)),
                int(word.end_time.seconds * 1000 +
                    word.end_time.nanos * (10**-6))
            ])

            words.append(word.word)

        paragraph = " ".join(words)
        for i, v in enumerate(words):
            data = BadWord.preprocessing(v)
            result1 = profanityfilter.predict(data)
            if result1[0][0] >= 0.85:
                swear_timeline.append(timeline[i])
                filter_words.append('*')
                filter_paragraph = " ".join(filter_words)
            else:
                filter_words.append(v)
                filter_paragraph = " ".join(filter_words)

        key = Counter(filter_paragraph.split(" ")).most_common(6)
        keyword = []
        for i in range(len(key)):
            keyword.append(key[i][0])

    return swear_timeline, paragraph, filter_paragraph, keyword


def create_beep(duration):
    sps = 48000
    freq_hz = 1000.0
    vol = 0.9

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
            return [result['label']]
        else:
            return [word[1] for word in result['Result']]


def saltlux_api_post(params):
    url = 'http://svc.saltlux.ai:31781'
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    response = requests.post(url, headers=headers, data=json.dumps(params))
    response_json = json.loads(
        response.content.decode("utf-8", errors='ignore'))
    return response_json

# -*-coding:utf-8-*-


def total_api(file_dir, file_name, user):
    swear_timeline, paragraph, filter_paragraph, keyword = sample_recognize(
        file_dir, file_name)
    sound = AudioSegment.from_wav(file_dir + file_name)
    beep = create_beep(duration=1030)

    if swear_timeline:
        for i in range(len(swear_timeline)):
            if i == 0:
                silence = AudioSegment.silent(
                    duration=swear_timeline[i][1] + 250)
                sound = sound[:swear_timeline[i][0]] + \
                    silence + sound[swear_timeline[i][1] + 250:]
            else:
                silence = AudioSegment.silent(
                    duration=swear_timeline[i][1] - swear_timeline[i][0] + 500)
                # beep = create_beep(
                #     duration=swear_timeline[i][1] - swear_timeline[i][0])
                # sound[swear_timeline[i][0]:swear_timeline[i][1]] = silence
                # sound = sound.overlay(
                #     silence, position=swear_timeline[i][0], gain_during_overlay=-20)
                sound = sound[:swear_timeline[i][0] - 250] + \
                    silence + sound[swear_timeline[i][1] + 250:]

    audio_name = file_dir + file_name[:-4] + '.mp3'
    sound.export(audio_name, format='mp3')

    for k in keyword:
        if k == '*':
            keyword.remove(k)

    collection = {
        'name': file_name[:-4] + '.mp3',
        'paragraph': paragraph,
        'filter_paragraph': filter_paragraph,
        'sensitivity': saltlux_api('11987300804', '0', paragraph),
        'emotion': saltlux_api('11987300804', '1', paragraph),
        'keyword': keyword
    }

    es_collection = {
        'user': user,
        'name': file_name[:-4] + '.mp3',
        'paragraph': paragraph,
        'filter_paragraph': filter_paragraph,
        'sensitivity': saltlux_api('11987300804', '0', paragraph),
        'emotion': saltlux_api('11987300804', '1', paragraph),
        'keyword': keyword
    }
    insertData(es_collection)
    result = json.dumps(collection, ensure_ascii=False).encode('utf-8')

    return result


def insertData(doc):
    es = Elasticsearch('http://127.0.0.1:9200')
    index = "babble"
    doc = doc
    es.index(index=index, doc_type="_doc", body=doc, request_timeout=30)
