"""모든 설정을 한곳에 모아둔 파일. 여기 값만 바꾸면 동작이 달라진다."""

# ---- 오디오 캡처 ----
SAMPLE_RATE = 16000        # Whisper는 16kHz를 원함 (건드리지 말 것)
CAPTURE_DEVICE = None      # None=기본 스피커 루프백. 특정 장치는 이름 일부 문자열로 지정
BLOCK_SECONDS = 0.1        # 한 번에 읽는 오디오 길이

# ---- 음성 구간 감지(VAD) ----
RMS_THRESHOLD = 0.012      # 이 에너지 이상이면 '말소리'로 간주 (환경에 맞게 튜닝)
SILENCE_END_SEC = 0.45     # 이만큼 조용하면 한 문장 끝난 걸로 보고 끊음
MIN_SEGMENT_SEC = 0.4      # 이보다 짧은 소리는 무시 (짧은 효과음 거름)
MAX_SEGMENT_SEC = 10.0     # 너무 길면 강제로 끊어서 STT 보냄
MAX_PENDING_SEGMENTS = 3   # 처리 대기 큐 한도. 밀리면 오래된 건 버려 지연 누적 방지

# ---- 음성인식 (faster-whisper) ----
# large-v3 = 가장 정확하고 노이즈에 강함(권장). 더 빠르게=medium/small
MODEL_SIZE = "large-v3"    # tiny / base / small / medium / large-v3
DEVICE = "cuda"            # "cuda"(GPU) 또는 "cpu"
COMPUTE_TYPE = "float16"   # GPU: float16 / CPU: int8
DECODE_BEAM = 5            # 빔 서치 크기. 클수록 정확(느림), 1=가장 빠름

# 인식/번역할 소스 언어 제한. 여기 없는 언어(한국어 등)로 감지되면 무시한다.
ALLOWED_LANGS = ["en", "ja"]   # 영어 · 일본어만
MIN_LANG_PROB = 0.6            # 허용 언어 확률이 이보다 낮으면 잡음으로 보고 버림
SOURCE_LANG = None             # 한 언어로 고정하려면 "en" 또는 "ja" (None=자동감지)

# ---- 번역 ----
TARGET_LANG = "ko"         # 내가 읽을 언어
TRANSLATOR = "local"       # "local"(GPU/NLLB, 빠름·오프라인) 또는 "google"(네트워크)
# 로컬 번역 모델 (NLLB). 3.3B = 최고 품질, 3090이면 여유. 더 가볍게=1.3B / 600M
TRANSLATION_MODEL = "facebook/nllb-200-3.3B"
TRANSLATION_CT2_DIR = "models/nllb-200-3.3B-ct2"
TRANSLATE_BEAM = 5             # 번역 빔 크기 (정확도)
TRANSLATE_LENGTH_PENALTY = 1.5  # 길수록 뒷부분 누락 방지 (NLLB가 문장 끝을 잘라먹는 버릇 교정)
USE_GLOSSARY = True            # 게임 슬랭 사전 보정 사용 (glossary.py)

# ---- 오버레이(자막 창) ----
MAX_LINES = 4              # 동시에 보여줄 자막 줄 수
LINE_TTL_SEC = 8           # 자막 한 줄이 사라지기까지 시간(초)
FONT_SIZE = 22
SHOW_ORIGINAL = True       # 번역문 아래에 원문도 같이 표시

# 위치/크기
OVERLAY_WIDTH = 900        # 자막창 너비(px)
OVERLAY_HEIGHT = 240       # 자막창 높이(px)
POSITION_FILE = "overlay_pos.json"  # `--place`로 저장한 위치. 있으면 이 위치를 사용
