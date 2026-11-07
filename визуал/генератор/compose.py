import json, os, sys, math, random, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SP = '/tmp/claude-0/-home-user-nri/421959fb-dfca-59ae-87ff-54c3d6a40123/scratchpad'
FD = SP + '/fonts/'
PW, PH = 1200, 1800
MARGIN, GUT = 34, 16
PAPER = (238, 233, 224)
INK = (14, 12, 12)


def F(name, size):
    return ImageFont.truetype(FD + name + '.ttf', size)


def layout(page):
    rows = page['rows']
    th = sum(r['h'] for r in rows)
    avail_h = PH - 2 * MARGIN - GUT * (len(rows) - 1) - 60  # bottom: page number
    y = MARGIN
    cells = []
    for r in rows:
        rh = avail_h * r['h'] / th
        tw = sum(p.get('w', 1) for p in r['panels'])
        avail_w = PW - 2 * MARGIN - GUT * (len(r['panels']) - 1)
        x = MARGIN
        for p in r['panels']:
            pw = avail_w * p.get('w', 1) / tw
            cells.append((p, (int(x), int(y), int(x + pw), int(y + rh))))
            x += pw + GUT
        y += rh + GUT
    return cells


def gen_size(box):
    w, h = box[2] - box[0], box[3] - box[1]
    ar = w / h
    area = 512 * 704
    gw = math.sqrt(area * ar)
    gh = gw / ar
    r64 = lambda v: max(384, min(896, int(round(v / 64)) * 64))
    return r64(gw), r64(gh)


def cover(im, w, h):
    iw, ih = im.size
    s = max(w / iw, h / ih)
    im = im.resize((int(iw * s + .5), int(ih * s + .5)), Image.LANCZOS)
    l = (im.width - w) // 2
    t = (im.height - h) // 3
    return im.crop((l, t, l + w, t + h))


def wrap(draw, text, font, maxw):
    if '\n' in text:
        out = []
        for part in text.split('\n'):
            out += wrap(draw, part, font, maxw)
        return out
    words = text.split()
    lines, cur = [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, fname, maxw, size, minsize=18):
    while True:
        f = F(fname, size)
        lines = wrap(draw, text, f, maxw)
        if all(draw.textlength(l, font=f) <= maxw for l in lines) or size <= minsize:
            return f, lines
        size -= 2


def anchor(box, pos, bw, bh, pad=14):
    x0, y0, x1, y1 = box
    cx = {'l': x0 + pad, 'c': (x0 + x1 - bw) // 2, 'r': x1 - pad - bw}
    cy = {'t': y0 + pad, 'c': (y0 + y1 - bh) // 2, 'b': y1 - pad - bh}
    pos = pos or 'tl'
    v = 't' if 't' in pos else ('b' if 'b' in pos else 'c')
    h = 'l' if 'l' in pos else ('r' if 'r' in pos else 'c')
    if pos in ('t', 'b'):
        h = 'c'
    return cx[h], cy[v]


def jagged(cx, cy, rx, ry, n=22, amp=.22, seed=1):
    rnd = random.Random(seed)
    pts = []
    for i in range(n * 2):
        a = math.pi * 2 * i / (n * 2)
        k = 1 + (amp if i % 2 == 0 else -amp * .3) * (0.8 + rnd.random() * .4)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


def dashed_ellipse(d, box, width=3, seg=10):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    n = int(2 * math.pi * max(rx, ry) / seg)
    for i in range(0, n, 2):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        d.line([(cx + math.cos(a0) * rx, cy + math.sin(a0) * ry), (cx + math.cos(a1) * rx, cy + math.sin(a1) * ry)], fill=INK, width=width)


def draw_text_block(d, lines, f, x, y, lh, fill=INK, center=True, w=0):
    for i, l in enumerate(lines):
        tw = d.textlength(l, font=f)
        xx = x + (w - tw) / 2 if center else x
        d.text((xx, y + i * lh), l, font=f, fill=fill)


def bubble(img, box, t, idx, used):
    d = ImageDraw.Draw(img, 'RGBA')
    pw = box[2] - box[0]
    kind = t.get('kind', 'speech')
    text = t['text'].strip().replace('≈', '~')
    if kind == 'sfx':
        size = max(40, min(96, int(pw / 6)))
        f = F('russo', size)
        tw = d.textlength(text, font=f)
        while tw > pw * .9 and size > 30:
            size -= 4
            f = F('russo', size)
            tw = d.textlength(text, font=f)
        lay = Image.new('RGBA', (int(tw) + 40, size + 40), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.text((20, 10), text, font=f, fill=(255, 214, 120, 255), stroke_width=5, stroke_fill=(20, 8, 4, 255))
        lay = lay.rotate(random.Random(idx).uniform(-9, 9), expand=True, resample=Image.BICUBIC)
        x, y = anchor(box, t.get('pos', 'c'), lay.width, lay.height, pad=6)
        img.alpha_composite(lay, (int(x), int(y)))
        return
    if kind == 'caption':
        maxw = int(pw * .62)
        f, lines = fit(d, text, 'ptn400', maxw - 24, 27)
        lh = int(f.size * 1.18)
        bw = int(max(d.textlength(l, font=f) for l in lines)) + 26
        bh = lh * len(lines) + 18
        x, y = anchor(box, t.get('pos', 'tl'), bw, bh, pad=0)
        x, y = max(box[0], x), max(box[1], y)
        d.rectangle([x, y, x + bw, y + bh], fill=(236, 222, 186, 245), outline=INK, width=3)
        draw_text_block(d, lines, f, x + 13, y + 9, lh, center=False)
        return
    if kind == 'system':
        maxw = int(pw * .7)
        f, lines = fit(d, text, 'ptn400', maxw - 30, 26)
        lh = int(f.size * 1.2)
        bw = int(max(d.textlength(l, font=f) for l in lines)) + 32
        bh = lh * len(lines) + 24
        x, y = anchor(box, t.get('pos', 'tr'), bw, bh)
        d.rectangle([x, y, x + bw, y + bh], fill=(16, 26, 38, 215), outline=(150, 190, 225, 255), width=2)
        d.line([x + 6, y + 4, x + bw - 6, y + 4], fill=(150, 190, 225, 160), width=1)
        draw_text_block(d, lines, f, x + 16, y + 12, lh, fill=(206, 228, 246), center=False)
        return
    # speech / shout / whisper
    who = (t.get('who') or '').strip()
    maxw = int(min(pw * .55, 380))
    font = 'ptn700' if kind == 'shout' else 'ptn400'
    size = 30 if kind == 'shout' else 28
    f, lines = fit(d, text, font, maxw, size)
    lh = int(f.size * 1.12)
    tw = max(d.textlength(l, font=f) for l in lines)
    th = lh * len(lines)
    padx, pady = (30, 24) if kind != 'shout' else (44, 36)
    bw, bh = int(tw + padx * 2), int(th + pady * 2)
    x, y = anchor(box, t.get('pos', 'tl'), bw, bh, pad=10)
    # avoid overlap with previous bubbles in same panel
    for _ in range(6):
        hit = [u for u in used if not (x + bw < u[0] or x > u[2] or y + bh < u[1] or y > u[3])]
        if not hit:
            break
        y = hit[0][3] + 8
        if y + bh > box[3] - 4:
            y = box[1] + 10
            x = box[2] - bw - 10 if x < (box[0] + box[2]) / 2 else box[0] + 10
    x = max(box[0] + 4, min(x, box[2] - bw - 4))
    y = max(box[1] + 4, min(y, box[3] - bh - 4))
    used.append((x, y, x + bw, y + bh))
    cx, cy = x + bw / 2, y + bh / 2
    # tail toward panel centre-bottom
    pcx, pcy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    down = cy < pcy
    tx = cx + (32 if cx < pcx else -32)
    ty = (y + bh + 46) if down else (y - 46)
    ty = max(box[1] + 6, min(box[3] - 6, ty))
    base_y = y + bh - 8 if down else y + 8
    if kind == 'shout':
        pts = jagged(cx, cy, bw / 2, bh / 2, seed=idx)
        d.polygon(pts, fill=(255, 255, 255, 250), outline=INK)
        d.line(pts + [pts[0]], fill=INK, width=4)
    else:
        tail = [(cx - 16, base_y), (cx + 16, base_y), (tx, ty)]
        d.polygon(tail, fill=(255, 255, 255, 250))
        d.line([tail[0], tail[2], tail[1]], fill=INK, width=3)
        d.ellipse([x, y, x + bw, y + bh], fill=(255, 255, 255, 250))
        if kind == 'whisper':
            dashed_ellipse(d, [x, y, x + bw, y + bh])
        else:
            d.ellipse([x, y, x + bw, y + bh], outline=INK, width=3)
        d.polygon([(cx - 13, base_y - 4), (cx + 13, base_y - 4), (cx, base_y + 6)], fill=(255, 255, 255, 250))
    draw_text_block(d, lines, f, x + padx, y + pady - 2, lh, center=True, w=tw)
    if who:
        nf = F('ptn700', 17)
        nw = d.textlength(who, font=nf)
        d.rectangle([x + bw / 2 - nw / 2 - 6, y - 12, x + bw / 2 + nw / 2 + 6, y + 8], fill=(20, 18, 18, 230))
        d.text((x + bw / 2 - nw / 2, y - 11), who, font=nf, fill=(236, 200, 120))


def compose(page_json, imgdir, out):
    page = json.load(open(page_json))
    img = Image.new('RGBA', (PW, PH), PAPER + (255,))
    d = ImageDraw.Draw(img)
    cells = layout(page)
    for p, box in cells:
        w, h = box[2] - box[0], box[3] - box[1]
        src = os.path.join(imgdir, p['id'] + '.png')
        if os.path.exists(src):
            im = cover(Image.open(src).convert('RGB'), w, h)
        else:
            im = Image.new('RGB', (w, h), (40, 36, 34))
        img.paste(im, box[:2])
        d.rectangle(box, outline=INK, width=5)
    for p, box in cells:
        used = []
        for i, t in enumerate(p.get('texts', [])):
            bubble(img, box, t, page['page'] * 100 + i, used)
    d = ImageDraw.Draw(img)
    f = F('ptn400', 22)
    s = '— %d —' % page['page']
    d.text(((PW - d.textlength(s, font=f)) / 2, PH - 50), s, font=f, fill=(90, 80, 70))
    img.convert('RGB').save(out, quality=88)


def jobs(panel_dir):
    out = []
    for fjs in sorted(glob.glob(os.path.join(panel_dir, 'p*.json'))):
        page = json.load(open(fjs))
        for p, box in layout(page):
            gw, gh = gen_size(box)
            out.append({'id': p['id'], 'seed': p.get('seed', 1), 'w': gw, 'h': gh, 'prompt': p['prompt']})
    return out


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'jobs':
        js = jobs(sys.argv[2])
        json.dump(js, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
        print(len(js), 'jobs')
    elif cmd == 'page':
        compose(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'all':
        os.makedirs(sys.argv[4], exist_ok=True)
        for fjs in sorted(glob.glob(os.path.join(sys.argv[2], 'p*.json'))):
            n = os.path.basename(fjs)[:-5]
            compose(fjs, sys.argv[3], os.path.join(sys.argv[4], n + '.jpg'))
            print(n)
