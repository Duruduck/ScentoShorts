"""
image_generator.py - 이미지 생성 (백엔드 교체 가능)
  huggingface: HuggingFace Inference API (무료)
  local_sd:    로컬 Stable Diffusion WebUI (GPU)
  replicate:   Replicate API (~$0.003/컷)
"""
import io, os, time, requests
from PIL import Image
from config import HUGGINGFACE_API_KEY, HF_IMAGE_MODEL, LOCAL_SD_URL, IMAGE_BACKEND, VIDEO_WIDTH, VIDEO_HEIGHT


def _postprocess(img, save_path):
    """9:16 세로 비율로 크롭/패딩 후 저장"""
    target = VIDEO_HEIGHT / VIDEO_WIDTH
    w, h = img.size
    ratio = h / w
    if ratio < target:
        new_h = int(w * target)
        pad = Image.new("RGB", (w, new_h), (0, 0, 0))
        pad.paste(img, (0, (new_h - h) // 2))
        img = pad
    elif ratio > target:
        new_w = int(h / target)
        img = img.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS).save(save_path, "PNG")
    return save_path


def _generate_huggingface(prompt, neg, seed):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {"inputs": prompt, "parameters": {"negative_prompt": neg, "seed": seed, "num_inference_steps": 4, "guidance_scale": 0, "width": 768, "height": 1344}}
    for attempt in range(3):
        r = requests.post(f"https://api-inference.huggingface.co/models/{HF_IMAGE_MODEL}", headers=headers, json=payload, timeout=120)
        if r.status_code == 503:
            t = 20 * (attempt + 1); print(f"   ⏳ 모델 로딩 {t}초 대기"); time.sleep(t); continue
        if r.status_code == 429:
            print("   ⚠️  한도 초과. 60초 대기"); time.sleep(60); continue
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))
    raise RuntimeError("HuggingFace API 실패")


def _generate_local_sd(prompt, neg, seed):
    import base64
    r = requests.post(f"{LOCAL_SD_URL}/sdapi/v1/txt2img",
        json={"prompt": prompt, "negative_prompt": neg, "seed": seed, "steps": 20, "cfg_scale": 7, "width": 768, "height": 1344, "sampler_name": "DPM++ 2M Karras"},
        timeout=300)
    r.raise_for_status()
    return Image.open(io.BytesIO(base64.b64decode(r.json()["images"][0])))


def _generate_replicate(prompt, neg, seed):
    try: import replicate
    except ImportError: raise ImportError("pip install replicate")
    output = replicate.run("black-forest-labs/flux-schnell", input={"prompt": prompt, "seed": seed, "num_outputs": 1, "aspect_ratio": "9:16", "output_format": "png"})
    return Image.open(io.BytesIO(requests.get(output[0], timeout=60).content))


def generate_image(prompt, negative_prompt="worst quality, low quality, blurry", seed=42, save_path="output.png", backend=None):
    backend = backend or IMAGE_BACKEND
    print(f"   🎨 [{backend}] {prompt[:80]}...")
    if backend == "huggingface": img = _generate_huggingface(prompt, negative_prompt, seed)
    elif backend == "local_sd": img = _generate_local_sd(prompt, negative_prompt, seed)
    elif backend == "replicate": img = _generate_replicate(prompt, negative_prompt, seed)
    else: raise ValueError(f"알 수 없는 백엔드: {backend}")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    return _postprocess(img, save_path)


def generate_all_images(scene_data, output_dir, base_seed=1000):
    """
    씬 데이터의 전체 컷 이미지를 순서대로 생성
    - region_prompts 있는 컷 → ComfyUI Regional Prompter
    - 나머지 컷 → IMAGE_BACKEND
    """
    comfyui_ok = False
    if any(c.get("region_prompts") for c in scene_data["cuts"]):
        try:
            from modules.comfyui_regional import is_comfyui_available
            comfyui_ok = is_comfyui_available()
            print("✅ ComfyUI 연결" if comfyui_ok else "⚠️  ComfyUI 미연결 — 폴백 사용")
        except ImportError:
            print("⚠️  comfyui_regional 모듈 없음")

    os.makedirs(output_dir, exist_ok=True)
    paths = []
    cuts = scene_data["cuts"]
    for cut in cuts:
        cid = cut["cut_id"]
        save_path = os.path.join(output_dir, f"cut_{cid:02d}.png")
        region = cut.get("region_prompts")
        layout = cut.get("layout", "single")
        if region and comfyui_ok:
            print(f"\n👥 컷 {cid}/{len(cuts)} — Regional [{layout}]")
            _generate_regional_cut(cut, save_path, base_seed)
        else:
            mode = "단독" if not region else "폴백(ComfyUI 없음)"
            print(f"\n👤 컷 {cid}/{len(cuts)} — {mode}")
            generate_image(cut["image_prompt"], cut.get("image_negative_prompt", ""), base_seed, save_path)
        paths.append(save_path)
    print(f"\n✅ 이미지 생성 완료: {len(cuts)}컷")
    return paths


def _generate_regional_cut(cut, save_path, seed):
    from modules.comfyui_regional import generate_regional, generate_over_the_shoulder
    region = cut["region_prompts"]
    layout = cut.get("layout", "side_by_side")
    neg = cut.get("image_negative_prompt", "worst quality, low quality, blurry, deformed, extra limbs")
    base = cut.get("mood", "dramatic lighting") + ", anime style, masterpiece, best quality"
    if layout == "over_the_shoulder":
        generate_over_the_shoulder(region.get("left", ""), region.get("right", ""), base, neg, seed, save_path)
    else:
        ratio = "1,1,1" if len(cut.get("characters_in_frame", [])) == 3 else "1,1"
        generate_regional(region.get("left", ""), region.get("right", ""), base, neg, seed, ratio, save_path=save_path)
