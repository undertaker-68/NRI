import sys, json, time, torch, os
from diffusers import StableDiffusionPipeline, LCMScheduler
torch.set_num_threads(4)
MODEL = os.environ.get("MODEL", "Meina/MeinaMix_V11")
kw = {"variant": "fp16"} if "dreamshaper" in MODEL else {}
pipe = StableDiffusionPipeline.from_pretrained(MODEL, torch_dtype=torch.float32, safety_checker=None, requires_safety_checker=False, **kw)
pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5", weight_name="pytorch_lora_weights.safetensors"); pipe.fuse_lora()
pipe.set_progress_bar_config(disable=True)
STYLE = "masterpiece, best quality, manhwa style, sharp lineart, cel shading, dramatic lighting, dark fantasy"
NEG = "(worst quality, low quality:1.4), text, letters, watermark, signature, logo, blurry, extra fingers, deformed hands, bad anatomy, chibi, realistic, photo, 3d, cross, crucifix"
jobs = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
for j in jobs:
    path = os.path.join(out, j['id'] + '.png')
    if os.path.exists(path): continue
    t = time.time(); g = torch.Generator().manual_seed(j.get('seed', 1))
    pr = j['prompt']; low = pr.lower(); import re
    male = re.search(r"\b(man|men|boy|witcher|convict|prior|knight|miner|giant|burgomaster|monk|squire|rider|scout|brother|figure)\b", low)
    female = re.search(r"\b(woman|women|girl|she|her)\b", low)
    neg = NEG + (', long hair, ponytail, old man' if 'witcher' in low else '')
    monster = 'no humans' in low
    if monster: neg += ', 1boy, man, handsome, human face, anime boy'
    elif male and not female: pr = '1boy, male focus, adult man, masculine, sharp jaw, ' + pr; neg += ', 1girl, female, feminine, breasts, makeup'
    elif female and not male: pr = '1girl, ' + pr
    im = pipe(prompt=STYLE + ", " + pr, negative_prompt=neg, width=j.get('w', 512), height=j.get('h', 768), num_inference_steps=j.get('steps', 8), guidance_scale=1.5, generator=g).images[0]
    im.save(path); print(j['id'], round(time.time() - t, 1), 's', flush=True)
