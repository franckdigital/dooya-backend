from celery import shared_task


@shared_task(name='chat.transcribe_voice_message')
def transcribe_voice_message_task(message_id: int):
    """Transcrit un message vocal et stocke le résultat."""
    from .models import Message
    from apps.search.transcription import transcribe_audio

    try:
        message = Message.objects.get(pk=message_id, type='audio')
    except Message.DoesNotExist:
        return

    if not message.file:
        return

    try:
        with message.file.open('rb') as f:
            transcript = transcribe_audio(f)
        if transcript:
            message.transcript = transcript
            message.save(update_fields=['transcript'])
    except Exception:
        pass
