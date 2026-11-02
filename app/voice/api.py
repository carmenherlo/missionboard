from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.voice.service import MAX_TEXT, Voice, VoiceUnavailableError

router = APIRouter(prefix="/api/voice", tags=["voice"])


def get_voice(request: Request) -> Voice:
    return request.app.state.voice


@router.get("/status")
def status(voice: Voice = Depends(get_voice)):
    """Whether the natural voice is here; without it, the tablet reads with its own."""
    return {"available": voice.available}


@router.get("")
def speak(text: str = Query(min_length=1, max_length=MAX_TEXT), voice: Voice = Depends(get_voice)):
    """The text read aloud by the natural voice (WAV); 503 without it."""
    try:
        audio = voice.speak(text.strip())
    except VoiceUnavailableError as error:
        raise HTTPException(status_code=503, detail="No natural voice") from error
    # The same text always sounds the same: the browser may keep it for a day.
    return Response(audio, media_type="audio/wav", headers={"Cache-Control": "max-age=86400"})
