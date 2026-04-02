"""
scene_analyzer.py - Claude API로 웹소설 장면 분석
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

SYSTEM_PROMPT = """당신은 웹소설을 숏폼 영상(30~60초)으로 변환하는 전문 PD입니다.

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "title": "영상 제목 (15자 이내)",
  "total_duration_sec": 45,
  "cuts": [
    {
      "cut_id": 1,
      "duration_sec": 5,
      "narration": "한국어 나레이션 (30자 이내)",
      "characters_in_frame": ["캐릭터명1"],
      "layout": "single | side_by_side | over_the_shoulder",
      "image_prompt": "상세한 영문 이미지 생성 프롬프트",
      "region_prompts": null,
      "image_negative_prompt": "worst quality, low quality, blurry, deformed, extra limbs",
      "camera": "close-up | medium shot | wide shot",
      "mood": "dramatic"
    }
  ]
}

━━━ 캐릭터 수에 따른 프롬프트 규칙 ━━━

【단독 컷】layout: "single", region_prompts: null
- image_prompt에 해당 캐릭터 appearance 전체 삽입

【2명 동시 컷】layout: "side_by_side" 또는 "over_the_shoulder"
- region_prompts 반드시 채울 것:
  {"left": "1boy, [캐릭터A appearance], [동작], anime style",
   "right": "1girl, [캐릭터B appearance], [동작], anime style"}
- image_prompt: "2characters, facing each other, [mood], anime style, masterpiece" (폴백용)

【over-the-shoulder】
- region_prompts:
  {"left": "back view, [캐릭터A appearance], shoulders only, blurred",
   "right": "[캐릭터B appearance], looking forward, emotional expression"}

━━━ 공통 규칙 ━━━
1. 반드시 영어로 작성
2. 캐릭터 appearance를 해당 region에 그대로 복사 (일관성 핵심!)
3. 퀄리티 태그: masterpiece, best quality, highly detailed
4. 같은 장면의 단독 컷들은 배경 묘사를 통일"""


def build_user_message(characters, scene, style, num_cuts):
    char_block = "".join(
        f"\n캐릭터명: {c['name']}\n한국어 설명: {c.get('description', '')}\n이미지 프롬프트용 외형(영문): {c['appearance']}\n"
        for c in characters
    )
    return f"""다음 웹소설 장면을 {num_cuts}개 컷의 숏폼 영상으로 변환해주세요.\n스타일: {style}\n\n【등장 캐릭터】\n{char_block.strip()}\n\n【장면 묘사】\n{scene}\n\n※ 각 컷의 image_prompt에 캐릭터 외형(영문)을 반드시 복사해서 넣어주세요."""


def analyze_scene(characters, scene_description, style="anime", num_cuts=6):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print("🤖 Claude가 장면을 분석 중...")
    msg = client.messages.create(
        model=CLAUDE_MODEL, max_tokens=2000, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(characters, scene_description, style, num_cuts)}],
    )
    raw = msg.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    data = json.loads(raw.strip())
    data["characters"] = characters
    data["style"] = style
    print(f"✅ 씬 분석 완료: '{data['title']}' — {len(data['cuts'])}컷")
    for cut in data["cuts"]:
        tag = "👥 Regional" if cut.get("region_prompts") else "👤 단독"
        print(f"   컷{cut['cut_id']}: {tag} [{cut.get('layout','single')}] — {', '.join(cut.get('characters_in_frame', []))}")
    multi = [c for c in data["cuts"] if c.get("region_prompts")]
    if multi:
        print(f"\n   → Regional Prompter 컷 {len(multi)}개 감지")
    return data


def save_scene_data(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 씬 데이터 저장: {output_path}")
