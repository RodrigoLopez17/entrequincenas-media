"""Busca y descarga fotos y videos de Pixabay para láminas de carrusel y escenas de reel.
Uso: python3 -I fotos.py <spec.json> <carpeta_media>
Lee PIXABAY_KEY del entorno. Cualquier lámina o escena con "busqueda" (2-4 palabras en inglés) y
"busqueda2" opcional recibe "img" (foto) o, si es escena de tipo "video", "vid", más "credito".
Si no hay clave, red o resultados, el elemento queda sin archivo: las plantillas lo dibujan sin foto.
No repite la misma foto o video dentro del mismo archivo. Reescribe spec.json.
"""
import json, os, sys, urllib.request, urllib.parse

spec_path, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
spec = json.load(open(spec_path))
key = os.environ.get('PIXABAY_KEY', '').strip()
usadas = set()
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'

def api(path, **kw):
    params = dict(key=key, safesearch='true', per_page=30, **kw)
    req = urllib.request.Request(f'https://pixabay.com/api/{path}?' + urllib.parse.urlencode(params), headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get('hits', [])

def bajar(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://pixabay.com/'})
    with urllib.request.urlopen(req, timeout=90) as r, open(dest, 'wb') as f:
        f.write(r.read())

def foto(q, vertical):
    hits = api('', q=q[:100], image_type='photo', orientation='vertical' if vertical else 'horizontal', min_width=1080)
    if not hits: hits = api('', q=q[:100], image_type='photo', min_width=1080)
    return hits

def video(q, dur):
    return [x for x in api('videos/', q=q[:100]) if x.get('duration', 0) >= min(dur, 6)]

elementos = list(spec.get('escenas', [])) + list(spec.get('slides', []))
for i, e in enumerate(elementos):
    if not e.get('busqueda'):
        continue
    e.pop('img', None); e.pop('vid', None)
    if not key:
        print('sin PIXABAY_KEY: elemento', i, 'queda sin foto'); continue
    es_video = e.get('tipo') == 'video'
    vertical = 'escenas' in spec or e.get('tipo') == 'portada'
    try:
        h = None
        for q in [e.get('busqueda', ''), e.get('busqueda2', '')]:
            if not q: continue
            hits = video(q, float(e.get('dur', 3))) if es_video else foto(q, vertical)
            hits = [x for x in hits if x['id'] not in usadas]
            if hits: h = hits[0]; break
        if not h:
            print('sin resultados:', e.get('busqueda')); continue
        usadas.add(h['id'])
        if es_video:
            v = h['videos']
            src = (v.get('medium') or {}).get('url') or (v.get('small') or {}).get('url') or (v.get('large') or {}).get('url')
            dest = os.path.join(outdir, f'video-{i}-{h["id"]}.mp4'); bajar(src, dest); e['vid'] = dest
        else:
            dest = os.path.join(outdir, f'foto-{i}-{h["id"]}.jpg'); bajar(h['largeImageURL'], dest); e['img'] = dest
        e['credito'] = f'{h.get("user", "")} / Pixabay'
        print('ok', e.get('busqueda'), '->', dest)
    except Exception as ex:
        print('error en elemento', i, ex)
json.dump(spec, open(spec_path, 'w'), ensure_ascii=False, indent=1)
