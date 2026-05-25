"""
Service de transcription audio → texte.

Stratégie multi-backend :
  1. Si GOOGLE_SPEECH_API_KEY est configuré → Google Speech-to-Text REST API
  2. Sinon → retourne None (la vue retournera une erreur explicite)

Pour intégrer Whisper (OpenAI) ou AssemblyAI, ajouter un backend ici.
"""
import base64
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_file, language_code: str = 'fr-FR') -> str | None:
    """
    Transcrit un fichier audio en texte.

    :param audio_file: InMemoryUploadedFile (WAV, FLAC, MP3, OGG, WEBM)
    :param language_code: BCP-47 language tag (fr-FR, en-US, sw-KE, yo-NG…)
    :return: texte transcrit ou None si échec
    """
    api_key = getattr(settings, 'GOOGLE_SPEECH_API_KEY', '')
    if api_key:
        return _transcribe_google(audio_file, api_key, language_code)

    # Whisper local (optionnel — nécessite pip install openai-whisper)
    if getattr(settings, 'USE_WHISPER', False):
        return _transcribe_whisper(audio_file)

    return None


def _transcribe_google(audio_file, api_key: str, language_code: str) -> str | None:
    """Google Cloud Speech-to-Text REST API v1."""
    audio_content = base64.b64encode(audio_file.read()).decode('utf-8')
    audio_file.seek(0)

    payload = {
        'config': {
            'encoding': 'WEBM_OPUS',
            'languageCode': language_code,
            'alternativeLanguageCodes': ['fr-FR', 'en-US'],
            'model': 'default',
            'enableAutomaticPunctuation': True,
        },
        'audio': {'content': audio_content},
    }

    try:
        resp = requests.post(
            f'https://speech.googleapis.com/v1/speech:recognize?key={api_key}',
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])
        if results:
            return results[0]['alternatives'][0]['transcript']
    except Exception as e:
        logger.warning('Google Speech transcription failed: %s', e)
    return None


def _transcribe_whisper(audio_file) -> str | None:
    """Whisper local (openai-whisper). Lent sur CPU mais gratuit."""
    try:
        import whisper
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name
        audio_file.seek(0)
        model = whisper.load_model('base')
        result = model.transcribe(tmp_path)
        os.unlink(tmp_path)
        return result.get('text', '').strip()
    except Exception as e:
        logger.warning('Whisper transcription failed: %s', e)
    return None
