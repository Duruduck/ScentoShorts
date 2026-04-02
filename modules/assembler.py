"""
assembler.py - FFmpeg으로 이미지 + 음성 + 자막 → 숏폼 MP4
ffmpeg 설치: https://ffmpeg.org/download.html
"""
import os, subprocess, tempfile
from config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, IMAGE_DURATION_SEC


def _check_ffmpeg():
    try: subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except: raise RuntimeError("ffmpeg 미설치. Mac: brew install ffmpeg / Ubuntu: sudo apt install ffmpeg")

def _audio_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except: return IMAGE_DURATION_SEC

def _make_srt(cuts, durations):
    lines, t = [], 0.0
    for i, (cut, dur) in enumerate(zip(cuts, durations), 1):
        def fmt(x): return f"{int(x//3600):02d}:{int((x%3600)//60):02d}:{int(x%60):02d},{int((x-int(x))*1000):03d}"
        lines += [str(i), f"{fmt(t)} --> {fmt(t+dur)}", cut["narration"], ""]
        t += dur
    tmp = tempfile.NamedTemporaryFile(suffix=".srt", mode="w", encoding="utf-8", delete=False)
    tmp.write("\n".join(lines)); tmp.close()
    return tmp.name


def assemble_slideshow(image_paths, tts_results, output_path, bgm_path=None):
    _check_ffmpeg()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    durations = [max(_audio_duration(r["audio_path"]) + 0.3, IMAGE_DURATION_SEC) for r in tts_results]
    srt = _make_srt(tts_results, durations)
    tmp_dir = tempfile.mkdtemp()
    clips = []

    for i, (img, tts_r, dur) in enumerate(zip(image_paths, tts_results, durations)):
        clip = os.path.join(tmp_dir, f"clip_{i:02d}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", img, "-i", tts_r["audio_path"],
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-t", str(dur),
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(FPS), "-shortest", clip
        ], capture_output=True, check=True)
        clips.append(clip)
        print(f"   🎬 컷 {i+1} 클립 완료")

    concat = os.path.join(tmp_dir, "concat.txt")
    open(concat, "w").write("\n".join(f"file '{p}'" for p in clips))
    merged = os.path.join(tmp_dir, "merged.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", merged], capture_output=True, check=True)

    subtitled = os.path.join(tmp_dir, "subtitled.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", merged,
        "-vf", f"subtitles={srt}:force_style='FontName=NanumGothic,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=80'",
        "-c:a", "copy", subtitled
    ], capture_output=True, check=True)

    if bgm_path and os.path.exists(bgm_path):
        subprocess.run([
            "ffmpeg", "-y", "-i", subtitled, "-i", bgm_path,
            "-filter_complex", "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", output_path
        ], capture_output=True, check=True)
    else:
        import shutil; shutil.copy2(subtitled, output_path)

    os.unlink(srt)
    print(f"\n✅ 영상 완성: {output_path} ({sum(durations):.1f}초)")
    return output_path
