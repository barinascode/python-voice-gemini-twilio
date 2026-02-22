import audioop
import base64

def mulaw_to_pcm_16k_base64(payload_b64: str) -> str:
    """Convierte audio mu-law 8kHz en Base64 a PCM 16kHz en Base64."""
    mu_law_audio = base64.b64decode(payload_b64)
    # 1. mu-law a linear pcm 8kHz
    pcm_8k = audioop.ulaw2lin(mu_law_audio, 2)
    # 2. linear 8kHz a 16kHz
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return base64.b64encode(pcm_16k).decode("utf-8")

def pcm_24k_base64_to_mulaw_base64(payload_b64: str) -> str:
    """Convierte audio PCM 24kHz en Base64 a mu-law 8kHz en Base64."""
    pcm_audio_24k = base64.b64decode(payload_b64)
    # 1. PCM 24kHz a 8kHz
    pcm_8k, _ = audioop.ratecv(pcm_audio_24k, 2, 1, 24000, 8000, None)
    # 2. linear pcm a mu-law
    mu_law = audioop.lin2ulaw(pcm_8k, 2)
    return base64.b64encode(mu_law).decode("utf-8")
