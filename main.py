"""
main.py - ScentoShorts
웹소설 → 숏폼 영상 파이프라인

실행 방법:
  python main.py                  # 대화형 모드
  python main.py --full           # 전체 자동 실행
  python main.py --step analyze   # 씬 분석만
  python main.py --session ID --step images
  python main.py --session ID --step assemble
"""
import os, sys, json, argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from modules.scene_analyzer import analyze_scene, save_scene_data
from modules.image_generator import generate_all_images
from modules.tts_generator import generate_all_tts
from modules.assembler import assemble_slideshow
from config import OUTPUT_DIR


# --- 캐릭터 카드 예시 (자신의 소설 캐릭터로 교체하세요) ---

EXAMPLE_CHARACTERS = [
    {
        "name": "이제온",
        "description": "냉혹한 황제. 은발에 얼음처럼 차가운 눈빛.",
        "appearance": (
            "silver long hair, ice blue eyes, sharp jawline, tall muscular male, "
            "black emperor robe with gold trim, cold expressionless face, pale skin, imperial crown"
        ),
    },
    {
        "name": "서하린",
        "description": "황후. 겉으론 온순하지만 내면에 강인한 의지.",
        "appearance": (
            "long black hair with loose waves, dark brown eyes, elegant female, "
            "white and gold hanbok-style dress, gentle smile, soft features, small silver hairpin"
        ),
    },
]

EXAMPLE_SCENE = """
황제 이제온은 차가운 시선으로 무렮를 꿇은 신하들을 내려다보았다.
"감히 황후를 모욕했다고?"
낮고 조용한 목소리였지만, 그 안에 담긴 분노는 온 궁궐을 얼어붙게 했다.
서하린은 눈을 내리깔고 있었다. '제발, 그냥 넘어가 주세요...'
황제는 손을 들어올렸다.
"오늘부로 삼족을 멸한다."
"""


# --- 단계별 실행 ---

def step_analyze(session_dir, characters, scene, style, num_cuts):
    print("\n" + "="*50 + "\n📖 1단계: 씬 분석\n" + "="*50)
    data = analyze_scene(characters=characters, scene_description=scene, style=style, num_cuts=num_cuts)
    path = os.path.join(session_dir, "scenes", "scene_data.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_scene_data(data, path)
    for cut in data["cuts"]:
        print(f"  [{cut['cut_id']}] {cut['duration_sec']}초 | {cut['camera']} | {cut['narration'][:30]}...")
    return data

def step_images(session_dir, scene_data):
    print("\n" + "="*50 + "\n🎨 2단계: 이미지 생성\n" + "="*50)
    return generate_all_images(scene_data, os.path.join(session_dir, "images"))

def step_tts(session_dir, scene_data):
    print("\n" + "="*50 + "\n🎙  3단계: TTS 나레이션\n" + "="*50)
    return generate_all_tts(scene_data, os.path.join(session_dir, "audio"))

def step_assemble(session_dir, scene_data, image_paths, tts_results):
    print("\n" + "="*50 + "\n🎬 4단계: 영상 조합\n" + "="*50)
    title_safe = scene_data["title"].replace(" ", "_").replace("/", "-")
    output_path = os.path.join(session_dir, "final", f"{title_safe}.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    return assemble_slideshow(image_paths, tts_results, output_path)


# --- 대화형 모드 ---

def interactive_mode():
    print("\n" + "="*60 + "\n🎬 ScentoShorts - 웹소설 → 숏폼 영상 생성기\n" + "="*60)

    char_choice = input("\n캐릭터: 1)예시 사용  2)직접 입력  (1/2): ").strip()
    if char_choice == "2":
        characters = []
        for i in range(int(input("캐릭터 수: "))):
            print(f"\n캐릭터 {i+1}")
            characters.append({
                "name": input("  이름: ").strip(),
                "description": input("  한국어 설명: ").strip(),
                "appearance": input("  영문 외형 프롬프트: ").strip()
            })
    else:
        characters = EXAMPLE_CHARACTERS
        print("  -> 예시 캐릭터 사용")

    scene_choice = input("\n장면: 1)예시 사용  2)직접 입력  (1/2): ").strip()
    if scene_choice == "2":
        print("장면 묘사 입력 (빈 줄 + Enter로 완료):")
        lines = []
        while True:
            line = input()
            if line == "": break
            lines.append(line)
        scene = "\n".join(lines)
    else:
        scene = EXAMPLE_SCENE
        print("  -> 예시 장면 사용")

    style = {"1": "anime", "2": "webtoon", "3": "realistic"}.get(
        input("\n스타일 (1=anime/2=webtoon/3=realistic, 기본=1): ").strip(), "anime")
    nc = input("컷 수 (4~8, 기본=6): ").strip()
    num_cuts = int(nc) if nc.isdigit() else 6

    print("\n단계: 1)전체  2)분석만  3)분석+이미지  4)분석+이미지+TTS")
    step = input("선택 (기본=2): ").strip() or "2"

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(OUTPUT_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    print(f"\n📁 세션: {session_dir}")

    data = step_analyze(session_dir, characters, scene, style, num_cuts)
    if step == "1":
        input("\n▶ Enter 후 이미지 생성...")
        imgs = step_images(session_dir, data)
        tts = step_tts(session_dir, data)
        print(f"\n🎉 완성! -> {step_assemble(session_dir, data, imgs, tts)}")
    elif step == "2":
        print(f"\n✅ JSON: {session_dir}/scenes/scene_data.json")
        print(f"   다음: python main.py --session {session_id} --step images")
    elif step == "3":
        input("\n▶ Enter 후 이미지 생성..."); step_images(session_dir, data)
    elif step == "4":
        input("\n▶ Enter 후 이미지+TTS 생성...")
        step_images(session_dir, data); step_tts(session_dir, data)
        print(f"\n✅ 완료. 영상 조합: python main.py --session {session_id} --step assemble")


# --- CLI 모드 ---

def cli_mode(args):
    if args.full:
        sd = os.path.join(OUTPUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(sd, exist_ok=True)
        d = step_analyze(sd, EXAMPLE_CHARACTERS, EXAMPLE_SCENE, "anime", 6)
        print(f"\n🎉 -> {step_assemble(sd, d, step_images(sd, d), step_tts(sd, d))}")
        return
    if args.session:
        sd = os.path.join(OUTPUT_DIR, args.session)
        with open(os.path.join(sd, "scenes", "scene_data.json"), "r", encoding="utf-8") as f:
            d = json.load(f)
        if args.step == "images": step_images(sd, d)
        elif args.step == "tts": step_tts(sd, d)
        elif args.step == "assemble":
            imgs_dir = os.path.join(sd, "images")
            imgs = sorted([os.path.join(imgs_dir, f) for f in os.listdir(imgs_dir) if f.endswith(".png")])
            step_assemble(sd, d, imgs, generate_all_tts(d, os.path.join(sd, "audio")))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="ScentoShorts")
    p.add_argument("--full", action="store_true")
    p.add_argument("--session", type=str)
    p.add_argument("--step", type=str, choices=["analyze", "images", "tts", "assemble"])
    args = p.parse_args()
    cli_mode(args) if (args.full or args.session) else interactive_mode()
