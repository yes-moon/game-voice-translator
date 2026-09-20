"""번역 백엔드.

- LocalBackend: 로컬 GPU에서 NLLB-200 모델을 CTranslate2로 돌린다.
  네트워크 불필요, 빠르고, 오프라인 동작.
- GoogleBackend: deep-translator의 Google 번역(네트워크). 로컬 모델이 없을 때 대체.
"""
import os
import re

import config

# 절 단위(마침표/물음표/느낌표/콤마 + 일본어 구두점)로 나눈다.
# NLLB는 긴 다절 문장에서 뒷부분을 통째로 빼먹는 버릇이 있어, 절마다 따로 번역해
# 정보 누락을 막는다. (자막은 매끄러움보다 '빠짐없이'가 더 중요)
_CLAUSE_SPLIT = re.compile(r"[,，、.!?。！？]+")

# NLLB-200이 쓰는 언어 코드 (FLORES-200)
NLLB_CODE = {"en": "eng_Latn", "ja": "jpn_Jpan", "ko": "kor_Hang"}

_BASE = os.path.dirname(os.path.abspath(__file__))


def _ct2_dir():
    d = config.TRANSLATION_CT2_DIR
    return d if os.path.isabs(d) else os.path.join(_BASE, d)


class GoogleBackend:
    name = "Google 번역 (네트워크)"

    def translate(self, text, src, tgt):
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target=tgt).translate(text)


class LocalBackend:
    name = "로컬 GPU 번역 (NLLB)"

    def __init__(self):
        import cuda_setup
        cuda_setup.add_cuda_dlls()
        import ctranslate2
        from transformers import AutoTokenizer
        ct2_dir = _ct2_dir()
        try:
            self.translator = ctranslate2.Translator(
                ct2_dir, device="cuda", compute_type="float16")
            self.device = "cuda"
        except Exception:
            self.translator = ctranslate2.Translator(
                ct2_dir, device="cpu", compute_type="int8")
            self.device = "cpu"
        self.tok = AutoTokenizer.from_pretrained(config.TRANSLATION_MODEL)

    def translate(self, text, src, tgt):
        src_code = NLLB_CODE.get(src)
        tgt_code = NLLB_CODE.get(tgt)
        if not src_code or not tgt_code:
            return text
        self.tok.src_lang = src_code

        clauses = [c.strip() for c in _CLAUSE_SPLIT.split(text) if c.strip()]
        if not clauses:
            return ""
        batch = [self.tok.convert_ids_to_tokens(self.tok.encode(c))
                 for c in clauses]
        results = self.translator.translate_batch(
            batch, target_prefix=[[tgt_code]] * len(batch),
            beam_size=config.TRANSLATE_BEAM,
            length_penalty=config.TRANSLATE_LENGTH_PENALTY,
            no_repeat_ngram_size=3,         # 같은 표현 반복 방지
            max_decoding_length=256)
        outs = []
        for r in results:
            target = r.hypotheses[0]
            if target and target[0] == tgt_code:   # 맨 앞 목표언어 토큰 제거
                target = target[1:]
            outs.append(self.tok.decode(self.tok.convert_tokens_to_ids(target)))
        return " ".join(outs).strip()


def local_model_exists():
    return os.path.isdir(_ct2_dir())


def make_backend(on_status=None):
    """config.TRANSLATOR에 따라 백엔드 생성. 로컬 모델이 없으면 Google로 폴백."""
    if config.TRANSLATOR == "local" and local_model_exists():
        if on_status:
            on_status("번역 모델 로딩 중...")
        return LocalBackend()
    if config.TRANSLATOR == "local" and on_status:
        on_status("로컬 번역 모델이 없어 Google 번역으로 대체합니다.")
    return GoogleBackend()
