"""Lee un brief diario, valida el JSON y genera las piezas.
Uso: python3 -I preparar.py <brief.txt> <carpeta_salida>
- brief.txt: texto completo del brief (con el bloque entre "=== JSON ===" y "=== FIN ===").
- Genera en <carpeta_salida>: los JPEG de los dos carruseles, reel.mp4 y manifest.json.
manifest.json = {"fecha", "ok": bool, "errores": [...], "avisos": [...], "posts": [
   {"key": "manana"|"reel"|"tarde", "hora": "8:00", "tipo": "CARRUSEL"|"REEL", "archivos": [...],
    "caption", "linkedin", "titulo_corto", "banco"} ]}
Si "ok" es false, no se debe publicar nada.
"""
import json, os, re, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
brief_path, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
FONTS = os.path.join(HERE, 'fonts')
txt = open(brief_path, encoding='utf-8').read()
errores, avisos = [], []

m = re.search(r'===\s*JSON\s*===\s*(\{.*\})\s*===\s*FIN\s*===', txt, re.S)
if not m:
    m = re.search(r'(\{\s*"fecha".*\})', txt, re.S)
if not m:
    print(json.dumps({'ok': False, 'errores': ['No encontré el bloque JSON en el brief']}, ensure_ascii=False)); sys.exit(0)
raw = m.group(1)
raw = raw.replace('“', '"').replace('”', '"')  # comillas tipográficas que meten algunos editores
try:
    b = json.loads(raw)
except Exception as ex:
    print(json.dumps({'ok': False, 'errores': [f'JSON inválido: {ex}']}, ensure_ascii=False)); sys.exit(0)

PROHIBIDAS = ['raya', 'devengo', 'entre quincenas', 'entrequincenas', 'adelanto de nómina', 'adelanto de nomina', '@', 'http']
LIM = {  # (campo, máximo) por tipo de lámina
    'portada': {'titular': 60, 'bajada': 110, 'cifra': 7, 'numero': 2, 'mito': 70},
    'texto': {'etiqueta': 22, 'titular': 55, 'texto': 210},
    'dato': {'etiqueta': 22, 'cifra': 9, 'texto': 120},
    'lista': {'etiqueta': 22, 'titular': 55},
    'cuenta': {'etiqueta': 22, 'titular': 45, 'nota': 140},
    'versus': {'etiqueta': 22, 'titular': 45},
    'cierre': {'titular': 70, 'texto': 90},
}
TOL = 1.15  # 15% de tolerancia: el renderizador encoge el texto si hace falta

def textos(o):
    if isinstance(o, str): yield o
    elif isinstance(o, list):
        for x in o: yield from textos(x)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('fuentes', 'notas_verificacion', 'tipo', 'tema', 'estilo', 'icono', 'id'): continue
            yield from textos(v)

def revisar_prohibidas(nombre, pieza):
    for t in textos(pieza):
        low = t.lower()
        for p in PROHIBIDAS:
            if p in low:
                errores.append(f'{nombre}: contiene "{p}" → "{t[:60]}"')

def limpia(s):
    return re.sub(r'[*]|<[^>]+>', '', s or '')

def revisar_carrusel(nombre, c):
    for k in ('id', 'tema', 'pilar', 'slides', 'caption'):
        if not c.get(k): errores.append(f'{nombre}: falta "{k}"'); return
    if c['tema'] not in ('uva', 'claro', 'noche'): errores.append(f'{nombre}: tema inválido {c["tema"]}')
    sl = c['slides']
    if not 5 <= len(sl) <= 9: errores.append(f'{nombre}: {len(sl)} láminas (deben ser 6-8)')
    if sl[0].get('tipo') != 'portada': errores.append(f'{nombre}: la primera lámina no es portada')
    if sl[-1].get('tipo') != 'cierre': avisos.append(f'{nombre}: la última lámina no es cierre')
    for i, s in enumerate(sl, 1):
        t = s.get('tipo')
        if t not in LIM: errores.append(f'{nombre} lámina {i}: tipo desconocido {t}'); continue
        for campo, mx in LIM[t].items():
            v = limpia(str(s.get(campo, '')))
            if len(v) > mx * TOL: errores.append(f'{nombre} lámina {i} ({t}): "{campo}" mide {len(v)} (máx {mx})')
            elif len(v) > mx: avisos.append(f'{nombre} lámina {i}: "{campo}" un poco largo ({len(v)}/{mx})')
        if t == 'cuenta':
            try:
                vals = [(f.get('tipo', 'normal'), float(re.sub(r'[^0-9.\-]', '', f['v']))) for f in s['filas']]
                if vals and vals[-1][0] == 'total' and len(vals) > 1:
                    pass  # los totales pueden ser parciales (ej. 50/30/20); solo se revisa que sean números
            except Exception:
                avisos.append(f'{nombre} lámina {i}: algún monto de la cuenta no es numérico')
    if len(c.get('caption', '')) > 2200: errores.append(f'{nombre}: caption mayor a 2,200 caracteres')
    revisar_prohibidas(nombre, {k: v for k, v in c.items() if k not in ('fuentes',)})
    if not c.get('fuentes'): avisos.append(f'{nombre}: sin fuentes')

def revisar_reel(r):
    if not r or not r.get('escenas'): errores.append('reel: falta o sin escenas'); return
    es = r['escenas']
    if es[0].get('tipo') != 'golpe': avisos.append('reel: no empieza con golpe')
    if es[-1].get('tipo') != 'pregunta': avisos.append('reel: no termina con pregunta')
    dur = sum(float(e.get('dur', 0)) for e in es)
    if not 15 <= dur <= 27: errores.append(f'reel: dura {dur:.1f} s (debe ser 18-24)')
    for e in es:
        if e.get('tipo') not in ('golpe', 'texto', 'contador', 'cuenta', 'raya', 'pregunta'):
            errores.append(f'reel: tipo de escena desconocido {e.get("tipo")}')
        if e.get('tipo') == 'raya' and not (0 <= int(e.get('hechos', 0)) < int(e.get('n', 1))):
            errores.append('reel: escena raya con "hechos" fuera de rango')
    revisar_prohibidas('reel', {k: v for k, v in r.items() if k not in ('fuentes',)})

cm, cr, ct = b.get('carrusel_manana'), b.get('reel'), b.get('carrusel_tarde')
if cm: revisar_carrusel('carrusel_manana', cm)
else: errores.append('falta carrusel_manana')
if ct: revisar_carrusel('carrusel_tarde', ct)
else: errores.append('falta carrusel_tarde')
revisar_reel(cr)

posts = []
if not errores:
    for key, c, hora in (('manana', cm, cm.get('hora', '8:00')), ('tarde', ct, ct.get('hora', '19:00'))):
        spec = os.path.join(out, c['id'] + '.json')
        json.dump({'id': c['id'], 'tema': c['tema'], 'pilar': c['pilar'], 'slides': c['slides']}, open(spec, 'w'), ensure_ascii=False)
        r = subprocess.run(['python3', '-I', os.path.join(HERE, 'render.py'), spec, out, FONTS], capture_output=True, text=True)
        if r.returncode != 0:
            errores.append(f'{key}: falló el render: {r.stderr[-300:]}'); continue
        res = json.loads(r.stdout.strip().splitlines()[-1])
        if res['problemas']: errores.append(f'{key}: problemas de diseño {res["problemas"]}')
        posts.append({'key': key, 'hora': hora, 'tipo': 'CARRUSEL', 'archivos': res['imagenes'], 'caption': c['caption'],
                      'linkedin': c.get('linkedin', ''), 'titulo_corto': c.get('titulo_corto', '')[:90], 'banco': c.get('banco', '')})
    if cr and not any(e.startswith('reel') for e in errores):
        spec = os.path.join(out, 'reel.json')
        json.dump({'kicker': cr.get('kicker', cm.get('pilar', '')), 'escenas': cr['escenas']}, open(spec, 'w'), ensure_ascii=False)
        r = subprocess.run(['python3', '-I', os.path.join(HERE, 'reel.py'), spec, os.path.join(out, 'reel.mp4'), FONTS], capture_output=True, text=True)
        if r.returncode != 0:
            errores.append(f'reel: falló el render: {r.stderr[-300:]}')
        else:
            posts.append({'key': 'reel', 'hora': cr.get('hora', '13:00'), 'tipo': 'REEL', 'archivos': ['reel.mp4'], 'caption': cr.get('caption', ''),
                          'linkedin': cr.get('linkedin', ''), 'titulo_corto': cr.get('titulo_corto', '')[:90], 'banco': cr.get('banco', '')})

man = {'fecha': b.get('fecha'), 'ok': not errores, 'errores': errores, 'avisos': avisos, 'posts': posts}
json.dump(man, open(os.path.join(out, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: man[k] for k in ('fecha', 'ok', 'errores', 'avisos')}, ensure_ascii=False))
