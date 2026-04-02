"""
tts_generator.py - edge-tts 한국어 나레이션 (완전 무료)
"""
import asyncio, os, edge_tts
from config import TTS_VOICE

async def _synthesize(text, path, voice):
    await edge_tts.Communicate(text, voice).save(path)

def generate_tts(text, output_path, voice=None):
    voice = voice or TTS_VOICE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    asyncio.run(_synthesize(text, output_path, voice))
    return output_path

def generate_all_tts(scene_data, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for cut in scene_data["cuts"]:
        cid = cut["cut_id"]
        audio_path = os.path.join(output_dir, f"cut_{cid:02d}.mp3")
        print(f'🎙  컷 {cid} TTS: "{cut["narration"][:30]}..."')
        generate_tts(cut["narration"], audio_path)
        results.append({"cut_id": cid, "audio_path": audio_path, "narration": cut["narration"], "duration_sec": cut.get("duration_sec", 4)})
    print(f"✅ TTS 완료: {len(results)}개")
    return results
