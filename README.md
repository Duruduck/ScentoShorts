# 🎬 ScentoShorts

웹소설 텍스트를 숏폼 영상(YouTube Shorts / TikTok / Reels)으로 자동 변환하는 Python 파이프라인입니다.

## 주요 기능

- **씬 분석**: Claude API로 웹소설 장면을 N개 컷으로 자동 분할
- **캐릭터 카드**: 캐릭터별 외형을 영문 프롬프트로 등록 → 매 컷에 자동 삽입 (일관성 유지)
- **다중 캐릭터 지원**: 단독 / side-by-side / over-the-shoulder 레이아웃 자동 선택
- **이미지 생성**: HuggingFace(무료) / 로컬 Stable Diffusion / Replicate 중 선택
- **Regional Prompter**: ComfyUI + Regional Prompter로 두 캐릭터를 좌/우 영역에 분리 생성
- **TTS 나레이션**: edge-tts (Microsoft, 완전 무료) 한국어 음성 생성
- **영상 조합**: FFmpeg으로 이미지 + 음성 + 자막 번인 → 9:16 MP4 출력

## 파이프라인 구조

```
웹소설 텍스트 입력
    ↓
① Claude API — 씬 분석 & 컷 분할 & 이미지 프롬프트 생성
    ↓
② 이미지 생성 — HuggingFace / 로컬 SD / Replicate
   (다중 캐릭터 컷) → ComfyUI Regional Prompter 자동 사용
    ↓
③ TTS — edge-tts 한국어 나레이션
    ↓
④ FFmpeg — 클립 연결 + 자막 burn-in + BGM 믹싱
    ↓
숏폼 MP4 출력
```

## 설치

```bash
git clone https://github.com/Duruduck/ScentoShorts.git
cd ScentoShorts
pip install -r requirements.txt

# ffmpeg 설치
# Mac:    brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
```

## 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

| 키 | 필수 | 설명 |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API 키 |
| `HUGGINGFACE_API_KEY` | 이미지 생성 시 | HuggingFace 무료 토큰 |
| `IMAGE_BACKEND` | - | `huggingface` / `local_sd` / `replicate` |
| `VIDEO_MODE` | - | `slideshow` / `ai_video` |

## 사용법

```bash
# 대화형 모드 (단계별 선택)
python main.py

# 전체 자동 실행
python main.py --full

# 단계별 실행
python main.py --step analyze    # 씬 분석만
python main.py --session 20240101_120000 --step images   # 이미지 생성
python main.py --session 20240101_120000 --step assemble # 영상 조합
```

## 캐릭터 카드 구조

`main.py`의 `EXAMPLE_CHARACTERS`를 자신의 소설 캐릭터로 교체하세요.

```python
characters = [
    {
        "name": "캐릭터 이름",
        "description": "한국어 설명 (Claude 참고용)",
        "appearance": "silver long hair, ice blue eyes, ..."  # 영문, 매 컷 프롬프트에 자동 삽입
    }
]
```

## 다중 캐릭터 컷 레이아웃

두 캐릭터가 같은 화면에 등장할 때 레이아웃을 자동 선택합니다.

| 레이아웃 | 설명 | ComfyUI |
|---|---|---|
| `single` | 단독 등장 | 불필요 |
| `side_by_side` | 좌/우 분할 | Regional Prompter |
| `over_the_shoulder` | 뒷모습 + 정면 | Regional Prompter |

### ComfyUI + Regional Prompter 설치 (선택)

```bash
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI && pip install -r requirements.txt

cd custom_nodes
git clone https://github.com/hako-mikan/sd-webui-regional-prompter

# 모델 배치: ComfyUI/models/checkpoints/ 에 .safetensors 파일
# 추천 모델: Anything V5 (애니 스타일)

python main.py --listen
```

## 프로젝트 구조

```
ScentoShorts/
├── main.py                      # 실행 진입점
├── config.py                    # 설정값
├── requirements.txt
├── .env.example
└── modules/
    ├── scene_analyzer.py        # Claude: 텍스트 → 컷 분할
    ├── image_generator.py       # 이미지 생성 (백엔드 교체 가능)
    ├── comfyui_regional.py      # ComfyUI Regional Prompter 연동
    ├── tts_generator.py         # edge-tts 나레이션
    └── assembler.py             # FFmpeg 영상 조합
```

## 예상 비용 (영상 1편 기준)

| 항목 | 비용 |
|---|---|
| Claude API (씬 분석) | ~$0.01 |
| 이미지 생성 (HuggingFace) | 무료 |
| 이미지 생성 (로컬 SD) | 무료 |
| TTS (edge-tts) | 무료 |
| 영상 조합 (FFmpeg) | 무료 |
| **합계** | **~$0.01** |

## 라이선스

MIT License
