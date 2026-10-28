"""Carruseles de finanzas (estética uva y lima) v2 -> JPEG 1080x1350.
Uso: python3 -I render.py <carrusel.json> <carpeta_salida> [carpeta_fuentes]
Si faltan las fuentes, las baja de npm (@fontsource/bricolage-grotesque y @fontsource/instrument-sans).
Los íconos (Lucide, licencia ISC) están en iconos.json junto a este archivo.

carrusel.json = {"id": "c-2026-10-29-1", "tema": "uva" | "claro" | "noche", "pilar": "Finanzas personales",
                 "slides": [ { "tipo": ..., ... } ]}   (6 a 8 láminas)
Tipos de lámina (todas aceptan "icono" opcional: wallet, piggy-bank, calendar, percent, triangle-alert,
circle-check, credit-card, landmark, trending-up, trending-down, receipt, calculator, briefcase, users, clock,
shield-check, banknote, hand-coins, chart-line, circle-x, lightbulb, search, file-text, building-2, target, scale):
  portada:  {"estilo": "raya"|"cifra"|"numero"|"mito", "titular": "con *palabra* resaltada", "bajada"?,
             "cifra"? (estilo cifra, máx 7 caracteres), "numero"? (estilo numero, 1-2 dígitos),
             "mito"? (estilo mito: la creencia falsa, máx 70)}
  texto:    {"etiqueta", "titular", "texto"?, "puntos"?: [..]}
  dato:     {"etiqueta"?, "cifra": "$4,800", "texto", "proporcion"?: 0..1 (pinta 10 segmentos)}
  lista:    {"etiqueta"?, "titular", "items": [{"t", "d"?}]}  (2 a 4)
  cuenta:   {"etiqueta"?, "titular", "filas": [{"c", "v", "tipo": "normal"|"resta"|"total"}], "nota"?}
  versus:   {"etiqueta"?, "titular", "a": {"t", "puntos": []}, "b": {"t", "puntos": []}}
  cierre:   {"titular": "pregunta a la audiencia", "texto"?}
*palabra* en titulares se pinta con el color de acento.
Escribe <id>-01.jpg ... y <id>.json con {"imagenes": [...], "problemas": [...]}.
"""
import json, sys, os, html, subprocess, tempfile, glob, shutil
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
spec_path, out = sys.argv[1], sys.argv[2]
FONTS = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, 'fonts')
os.makedirs(out, exist_ok=True)
spec = json.load(open(spec_path))
ICONOS = json.load(open(os.path.join(HERE, 'iconos.json')))

NEED = ['bricolage-grotesque-latin-700-normal.woff2', 'bricolage-grotesque-latin-800-normal.woff2',
        'instrument-sans-latin-400-normal.woff2', 'instrument-sans-latin-500-normal.woff2',
        'instrument-sans-latin-600-normal.woff2', 'instrument-sans-latin-700-normal.woff2']

def fuentes():
    if all(os.path.exists(os.path.join(FONTS, f)) for f in NEED):
        return
    os.makedirs(FONTS, exist_ok=True)
    tmp = tempfile.mkdtemp()
    subprocess.run(['npm', 'pack', '@fontsource/bricolage-grotesque', '@fontsource/instrument-sans'], cwd=tmp, check=True, capture_output=True)
    for tgz in glob.glob(os.path.join(tmp, '*.tgz')):
        d = tgz[:-4]; os.makedirs(d); subprocess.run(['tar', 'xzf', tgz, '-C', d], check=True)
    for f in NEED:
        shutil.copy(glob.glob(os.path.join(tmp, '*', 'package', 'files', f))[0], FONTS)
    shutil.rmtree(tmp)

fuentes()

def ff(fam, w, f):
    return f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{os.path.abspath(os.path.join(FONTS, f))}') format('woff2')}}"
FACES = '\n'.join([ff('Bricolage Grotesque', 700, NEED[0]), ff('Bricolage Grotesque', 800, NEED[1]),
                   ff('Instrument Sans', 400, NEED[2]), ff('Instrument Sans', 500, NEED[3]),
                   ff('Instrument Sans', 600, NEED[4]), ff('Instrument Sans', 700, NEED[5])])

TEMAS = {
    'uva':   dict(bg='#4B1E8C', ink='#FFFFFF', mut='#D9CCF0', acc='#C6F36B', tag='#C6F36B', card='#3A1670', line='#6B43A8',
                  done='#FFFFFF', todo='#6B43A8', cur='#C6F36B', curb='#C6F36B', ghost='#5A2AA6', iconbg='#C6F36B', iconfg='#1E1033'),
    'claro': dict(bg='#F7F4FB', ink='#1E1033', mut='#5B4A73', acc='#4B1E8C', tag='#4B1E8C', card='#FFFFFF', line='#DDD3EC',
                  done='#4B1E8C', todo='#E7DEF5', cur='#C6F36B', curb='#4B1E8C', ghost='#EDE6F7', iconbg='#4B1E8C', iconfg='#C6F36B'),
    'noche': dict(bg='#120A1F', ink='#F4EFFB', mut='#B8A9CF', acc='#C6F36B', tag='#C4A8F5', card='#1C1230', line='#3A2C55',
                  done='#C4A8F5', todo='#3A2C55', cur='#C6F36B', curb='#C6F36B', ghost='#1F1433', iconbg='#C6F36B', iconfg='#120A1F'),
}
T = TEMAS.get(spec.get('tema', 'uva'), TEMAS['uva'])

def e(s):
    return html.escape(str(s or ''))

def hi(s):
    parts = e(s).split('*')
    return ''.join(f'<em>{p}</em>' if i % 2 else p for i, p in enumerate(parts))

def ico(name, cls='ico'):
    if not name or name not in ICONOS: return ''
    return f'<div class="{cls}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{ICONOS[name]}</svg></div>'

def puntos(ps):
    if not ps: return ''
    return '<ul>' + ''.join(f'<li>{hi(p)}</li>' for p in ps) + '</ul>'

def head(s):
    i = ico(s.get('icono'))
    tag = f'<div class="tag">{e(s.get("etiqueta"))}</div>' if s.get('etiqueta') else ''
    return f'<div class="hd">{i}{tag}</div>' if (i or tag) else ''

def raya_grande(n=4, cur=2):
    return '<div class="rg">' + ''.join(f'<i class="{"d" if j < cur else ("c" if j == cur else "")}"></i>' for j in range(n)) + '</div>'

def cuerpo(s):
    t = s['tipo']
    if t == 'portada':
        st = s.get('estilo', 'raya')
        baj = f'<p class="bajada">{hi(s["bajada"])}</p>' if s.get('bajada') else ''
        des = '' if spec.get('suelto') else '<div class="desliza">Desliza</div>'
        if st == 'cifra':
            return f'<div class="pcifra fitw">{e(s.get("cifra"))}</div><h1 class="m">{hi(s["titular"])}</h1>{baj}{des}'
        if st == 'numero':
            return f'<div class="pnum">{e(s.get("numero"))}</div><h1>{hi(s["titular"])}</h1>{baj}{des}'
        if st == 'mito':
            return (f'<div class="sello">Mito</div><div class="mito"><span>{e(s.get("mito"))}</span></div>'
                    f'<h1 class="m">{hi(s["titular"])}</h1>{baj}{des}')
        return f'{raya_grande()}<h1>{hi(s["titular"])}</h1>{baj}{des}'
    if t == 'texto':
        return head(s) + f'<h2>{hi(s["titular"])}</h2>' + (f'<p>{hi(s["texto"])}</p>' if s.get('texto') else '') + puntos(s.get('puntos'))
    if t == 'dato':
        prop = ''
        if s.get('proporcion') is not None:
            k = round(float(s['proporcion']) * 10)
            prop = '<div class="prop">' + ''.join(f'<i class="{"on" if j < k else ""}"></i>' for j in range(10)) + '</div>'
        return head(s) + f'<div class="cifra fitw">{e(s["cifra"])}</div>{prop}<p class="big">{hi(s["texto"])}</p>'
    if t == 'lista':
        items = ''.join(f'<div class="it"><div class="n">{i+1}</div><div><b>{hi(x["t"])}</b>' + (f'<span>{hi(x.get("d"))}</span>' if x.get('d') else '') + '</div></div>' for i, x in enumerate(s['items']))
        return head(s) + f'<h2>{hi(s["titular"])}</h2><div class="items">{items}</div>'
    if t == 'cuenta':
        rows = ''.join(f'<div class="row {r.get("tipo","normal")}"><span>{hi(r["c"])}</span><b>{e(r["v"])}</b></div>' for r in s['filas'])
        return head(s) + f'<h2>{hi(s["titular"])}</h2><div class="card">{rows}</div>' + (f'<p class="nota">{hi(s["nota"])}</p>' if s.get('nota') else '')
    if t == 'versus':
        col = lambda x, k: f'<div class="col {k}"><h3>{hi(x["t"])}</h3>{puntos(x.get("puntos"))}</div>'
        return head(s) + f'<h2>{hi(s["titular"])}</h2><div class="vs">{col(s["a"],"a")}<div class="vsx">vs</div>{col(s["b"],"b")}</div>'
    if t == 'foto':
        card = (f'<div class="fcard"><div class="fimg" style="background-image:url(\'file://{os.path.abspath(s["img"])}\')"></div><div class="ftint"></div></div>'
                if s.get('img') else '')
        return card + head(s) + f'<h2>{hi(s["titular"])}</h2>' + (f'<p>{hi(s["texto"])}</p>' if s.get('texto') else '')
    if t == 'cierre':
        return (f'{raya_grande(5, 4)}<div class="tag">Tu turno</div><h1 class="q">{hi(s["titular"])}</h1>'
                + (f'<p class="bajada">{hi(s["texto"])}</p>' if s.get('texto') else '')
                + '<div class="follow"><div class="fb">' + ico('file-text', 'fi') + '<span><b>Guárdalo</b> para tu próxima quincena</span></div>'
                + '<div class="fb">' + ico('users', 'fi') + '<span><b>Compártelo</b> con quien lo necesite</span></div></div>')
    raise ValueError('tipo desconocido: ' + t)

CSS = """%FACES%
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;background:%bg%}
.s{position:relative;width:1080px;height:1350px;background:%bg%;color:%ink%;font-family:'Instrument Sans';overflow:hidden}
.ghost{position:absolute;right:-60px;top:150px;display:flex;flex-direction:column;gap:26px;align-items:flex-end;z-index:0}
.ghost i{display:block;height:70px;border-radius:999px;background:%ghost%}
.top{position:absolute;left:80px;right:80px;top:72px;display:flex;justify-content:space-between;align-items:center;font:600 28px 'Instrument Sans';color:%mut%;z-index:2}
.top .h{color:%ink%}
.main{position:absolute;left:80px;right:80px;top:180px;bottom:170px;display:flex;flex-direction:column;justify-content:flex-start;z-index:1}
.portada .main,.cierre .main{justify-content:flex-end}
.dato .main{justify-content:center}
em{font-style:normal;color:%acc%}
.hd{display:flex;align-items:center;gap:24px;margin-bottom:34px;min-height:20px}
.ico{flex:none;width:96px;height:96px;border-radius:28px;background:%iconbg%;color:%iconfg%;display:flex;align-items:center;justify-content:center}
.ico svg{width:56px;height:56px}
.tag{font:700 30px 'Instrument Sans';letter-spacing:3px;text-transform:uppercase;color:%tag%}
h1{font:800 124px/0.98 'Bricolage Grotesque';letter-spacing:-4.5px}
h1.m{font-size:100px;letter-spacing:-3.5px}
h1.q{font-size:100px;letter-spacing:-3.5px;margin-top:24px}
.bajada{margin-top:36px;font:500 40px/1.32 'Instrument Sans';color:%mut%}
.desliza{margin-top:50px;font:600 28px 'Instrument Sans';color:%mut%;display:flex;align-items:center;gap:16px}
.desliza:after{content:'';width:90px;height:12px;border-radius:999px;background:%cur%;box-shadow:0 0 0 3px %curb% inset}
.rg{display:flex;gap:18px;margin-bottom:70px}
.rg i{flex:1;height:110px;border-radius:999px;background:%todo%}
.rg i.d{background:%done%}.rg i.c{background:%cur%;box-shadow:0 0 0 5px %curb% inset}
.cierre .rg{margin-bottom:60px}.cierre .rg i{height:64px}
.pcifra{font:800 330px/0.86 'Bricolage Grotesque';letter-spacing:-8px;color:%acc%;white-space:nowrap;margin-bottom:40px;font-variant-numeric:tabular-nums}
.pnum{position:absolute;right:-30px;top:-120px;font:800 900px/0.8 'Bricolage Grotesque';letter-spacing:-50px;color:%ghost%;z-index:-1}
.sello{align-self:flex-start;font:800 34px 'Bricolage Grotesque';letter-spacing:3px;text-transform:uppercase;background:%acc%;color:%bg%;padding:12px 28px;border-radius:999px;margin-bottom:30px}
.mito{font:700 58px/1.15 'Bricolage Grotesque';letter-spacing:-1.5px;color:%mut%;margin-bottom:56px}
.mito span{background:linear-gradient(transparent 46%, %acc% 46%, %acc% 56%, transparent 56%);-webkit-box-decoration-break:clone;box-decoration-break:clone}
h2{font:800 84px/1.02 'Bricolage Grotesque';letter-spacing:-3px;margin-bottom:40px}
p{font:400 44px/1.38 'Instrument Sans';color:%mut%}
p.big{font:600 52px/1.25 'Instrument Sans';color:%ink%;margin-top:30px}
ul{list-style:none;margin-top:36px;display:flex;flex-direction:column;gap:26px}
li{position:relative;padding-left:56px;font:500 42px/1.32 'Instrument Sans';color:%ink%}
li:before{content:'';position:absolute;left:0;top:22px;width:32px;height:12px;border-radius:999px;background:%cur%;box-shadow:0 0 0 3px %curb% inset}
.cifra{font:800 280px/0.9 'Bricolage Grotesque';letter-spacing:-7px;color:%acc%;font-variant-numeric:tabular-nums;white-space:nowrap}
.prop{display:flex;gap:12px;margin-top:40px}.prop i{flex:1;height:44px;border-radius:999px;background:%todo%}.prop i.on{background:%done%}
.items{display:flex;flex-direction:column;gap:34px}
.it{display:flex;gap:32px;align-items:flex-start}
.it .n{flex:none;width:92px;height:92px;border-radius:28px;background:%iconbg%;display:flex;align-items:center;justify-content:center;font:800 52px 'Bricolage Grotesque';color:%iconfg%}
.it b{display:block;font:700 44px/1.16 'Instrument Sans';color:%ink%;padding-top:4px}
.it span{display:block;margin-top:8px;font:400 36px/1.34 'Instrument Sans';color:%mut%}
.card{background:%card%;border:3px solid %line%;border-radius:36px;padding:14px 44px}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:30px;padding:30px 0;border-bottom:3px solid %line%;font:500 40px 'Instrument Sans';color:%mut%}
.row:last-child{border-bottom:0}
.row b{font:800 48px 'Bricolage Grotesque';color:%ink%;font-variant-numeric:tabular-nums;white-space:nowrap}
.row.resta b{color:%mut%}
.row.total{color:%ink%;font-weight:700}
.row.total b{font-size:76px;color:%acc%;letter-spacing:-2px}
.nota{margin-top:30px;font-size:34px}
.vs{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:stretch}
.vsx{align-self:center;font:800 40px 'Bricolage Grotesque';color:%acc%}
.col{background:%card%;border:3px solid %line%;border-radius:36px;padding:40px 34px}
.col.b{border-color:%cur%}
.col h3{font:800 52px/1.05 'Bricolage Grotesque';letter-spacing:-1.5px}
.col li{font-size:34px;padding-left:44px}.col li:before{width:26px;top:17px}
.follow{margin-top:56px;padding-top:40px;border-top:3px solid %line%;display:flex;flex-direction:column;gap:22px;font:500 36px 'Instrument Sans';color:%mut%}
.fb{display:flex;align-items:center;gap:22px}.fb b{color:%ink%}
.fi{flex:none;width:64px;height:64px;border-radius:20px;border:3px solid %line%;color:%acc%;display:flex;align-items:center;justify-content:center}.fi svg{width:36px;height:36px}
.bgf{position:absolute;inset:0;background-size:cover;background-position:center;filter:grayscale(1) contrast(1.1);z-index:0}
.bgt{position:absolute;inset:0;background:#4B1E8C;mix-blend-mode:multiply;opacity:.6;z-index:0}
.bgg{position:absolute;inset:0;background:linear-gradient(180deg,%bg%00 0%,%bg%00 22%,%bg%e6 52%,%bg% 66%);z-index:0}
.conf .rg{display:none}
.conf .top,.conf .top .h{color:#FFFFFF;text-shadow:0 2px 12px rgba(0,0,0,.35)}
.fcard{position:relative;height:500px;border-radius:36px;overflow:hidden;margin-bottom:44px;flex:none}
.fimg{position:absolute;inset:0;background-size:cover;background-position:center;filter:grayscale(1) contrast(1.1)}
.ftint{position:absolute;inset:0;background:#4B1E8C;mix-blend-mode:multiply;opacity:.55}
.cred{position:absolute;right:80px;bottom:44px;font:500 18px 'Instrument Sans';color:%mut%;opacity:.8;z-index:2}
.raya{position:absolute;left:80px;right:80px;bottom:80px;display:flex;gap:10px;z-index:2}
.raya i{flex:1;height:16px;border-radius:999px;background:%todo%}
.raya i.d{background:%done%}.raya i.c{background:%cur%;box-shadow:0 0 0 3px %curb% inset}
"""
for k, v in T.items():
    CSS = CSS.replace('%' + k + '%', v)
CSS = CSS.replace('%FACES%', FACES)

N = len(spec['slides'])
GHOSTS = {'texto': [380, 260, 160], 'lista': [300, 180], 'cuenta': [240, 140], 'versus': [260]}
def page(i, s):
    if spec.get('suelto'):  # post independiente: firma fija en lugar de progreso
        raya = '<i class="d"></i><i class="d"></i><i class="c"></i><i></i><i></i>'
    else:
        raya = ''.join(f'<i class="{"d" if j < i else ("c" if j == i else "")}"></i>' for j in range(N))
    g = GHOSTS.get(s['tipo'])
    bgf = ''
    if s['tipo'] in ('portada', 'cierre') and s.get('img'):
        bgf = f'<div class="bgf" style="background-image:url(\'file://{os.path.abspath(s["img"])}\')"></div><div class="bgt"></div><div class="bgg"></div>'
    cred = f'<div class="cred">Foto: {e(s.get("credito"))}</div>' if s.get('img') and s.get('credito') else ''
    ghost = ('<div class="ghost">' + ''.join(f'<i style="width:{w}px"></i>' for w in g) + '</div>') if g else ''
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="s {s['tipo']}{' conf' if bgf else ''}">{bgf}{ghost}<div class="top"><span class="h">{e(spec.get('pilar'))}</span><span>{'' if spec.get('suelto') else f'{i+1}/{N}'}</span></div>
<div class="main" id="m">{cuerpo(s)}</div>
<div class="raya">{raya}</div>{cred}</div></body></html>"""

FIT = """() => { const m = document.getElementById('m');
  const over = () => m.scrollHeight > m.clientHeight + 2 || [...m.querySelectorAll('.fitw,.cifra,.row,h1,h2,h3')].some(x => x.scrollWidth > x.clientWidth + 2);
  let k = 1, n = 0;
  while (over() && n < 25) { k *= 0.95; n++;
    m.querySelectorAll('*').forEach(x => { if (x.closest('svg')) return; if (!x.dataset.fs) x.dataset.fs = parseFloat(getComputedStyle(x).fontSize);
      x.style.fontSize = (x.dataset.fs * k) + 'px'; }); }
  return {pasos: n, sigue: over()}; }"""

res = {'imagenes': [], 'problemas': []}
CHECK = "Promise.all(['800 50px \"Bricolage Grotesque\"','400 30px \"Instrument Sans\"'].map(f=>document.fonts.load(f))).then(()=>['800 50px \"Bricolage Grotesque\"','400 30px \"Instrument Sans\"'].every(f=>document.fonts.check(f)))"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1080, 'height': 1350})
    pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
    tmp = tempfile.mkdtemp()
    for i, s in enumerate(spec['slides']):
        f = os.path.join(tmp, f'{i}.html'); open(f, 'w').write(page(i, s))
        pg.goto('file://' + f); pg.evaluate('document.fonts.ready')
        ok = pg.evaluate(CHECK)
        fit = pg.evaluate(FIT)
        name = f"{spec['id']}-{i+1:02d}.jpg"
        pg.screenshot(path=os.path.join(out, name), type='jpeg', quality=90)
        res['imagenes'].append(name)
        if not ok or fit['sigue'] or fit['pasos'] > 8:
            res['problemas'].append({'lamina': name, 'fuentes': ok, **fit})
    b.close(); shutil.rmtree(tmp)
json.dump(res, open(os.path.join(out, spec['id'] + '.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
