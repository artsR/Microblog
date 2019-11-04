import json
import requests
from flask import current_app
from flask_babel import _



def translate(text, scr_lang, dst_lang):

    if ('YANDEX_TRANSLATION_KEY' not in current_app.config or not
                    current_app.config['YANDEX_TRANSLATION_KEY']):
        return _('Error: the translation service is not configured.')

    r = requests.get(f"https://translate.yandex.net/api/v1.5/tr.json/translate?"
                     f"key={current_app.config['YANDEX_TRANSLATION_KEY']}&"
                     f"text={text}&"
                     f"lang={scr_lang}-{dst_lang}&"
                     f"format=plain")
    if r.status_code != 200:
        return _('Error: the translation service failed.')

    return r.json()['text'][0]
