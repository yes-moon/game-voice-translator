"""Windows에서 pip로 설치한 NVIDIA CUDA 런타임 DLL을 찾도록 경로를 등록한다.

ctranslate2(faster-whisper의 백엔드)는 cublas64_12.dll / cudnn64_9.dll 등을
시스템 PATH나 DLL 검색 경로에서 찾는다. pip 휠(nvidia-*-cu12)로 설치하면
site-packages/nvidia/*/bin 에 들어가므로, faster_whisper를 import 하기 전에
이 함수를 호출해 그 경로들을 등록해야 한다.
"""
import os
import sys
import glob


def add_cuda_dlls():
    if sys.platform != "win32":
        return
    try:
        import nvidia
    except ImportError:
        return
    base = list(nvidia.__path__)[0]
    for d in glob.glob(os.path.join(base, "*", "bin")):
        if os.path.isdir(d):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
