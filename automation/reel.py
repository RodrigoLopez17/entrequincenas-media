"""Reel vertical 1080x1920, 30 fps, estética uva y lima, con música y efectos (sonido.py al lado).
Uso: python3 -I reel.py <reel.json> <salida.mp4> <carpeta_fuentes>
reel.json = {"kicker": "Finanzas personales", "escenas": [...]}; cada escena con "tipo" y "dur" (s):
  golpe:    {"html": "Frase con <em>clave</em>"}
  contador: {"valor": 1200, "dec": 0, "pre": "$", "suf": "", "texto": "..."}
  texto:    {"texto": "..."}                       (aparece palabra por palabra)
  cuenta:   {"titulo": "...", "filas": [{"c": "concepto", "v": "$1,000", "tipo": "normal"|"resta"|"total"}]}
  raya:     {"n": 15, "hechos": 12, "texto": "..."}  (segmentos que se llenan, ej. días de la quincena)
  pregunta: {"texto": "..."}
  foto:     {"img": ruta local, "texto", "cifra"?, "credito"?}   (foto real teñida de uva, zoom lento)
  video:    {"vid": ruta local mp4, "texto", "cifra"?, "credito"?} (video real de fondo, teñido)
  (fotos.py llena "img"/"vid" a partir de "busqueda"; si falta el archivo, la escena se vuelve texto)
Todas las cifras deben venir del guion; nada inventado."""
import json, sys, os, asyncio, subprocess, tempfile, shutil
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sonido

spec = json.load(open(sys.argv[1])); out = sys.argv[2]; FONTS = os.path.abspath(sys.argv[3])
FPS = 30
for e in spec['escenas']:
    if e['tipo'] == 'video' and not (e.get('vid') and os.path.exists(e['vid'])):
        e['tipo'] = 'foto' if (e.get('img') and os.path.exists(e['img'])) else 'texto'
    if e['tipo'] == 'foto':
        if e.get('img') and os.path.exists(e['img']): e['img'] = 'file://' + os.path.abspath(e['img'])
        else: e['tipo'] = 'texto'
VIDS = [e for e in spec['escenas'] if e['tipo'] == 'video']
t0 = 0.0
for e in spec['escenas']:
    e['a'] = round(t0, 3); t0 += e['dur']; e['b'] = round(t0, 3)
DUR = t0

def ff(fam, w, f):
    return f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{os.path.join(FONTS, f)}') format('woff2')}}"
FACES = ff('Bricolage Grotesque', 800, 'bricolage-grotesque-latin-800-normal.woff2') + ff('Bricolage Grotesque', 700, 'bricolage-grotesque-latin-700-normal.woff2') + \
        ff('Instrument Sans', 500, 'instrument-sans-latin-500-normal.woff2') + ff('Instrument Sans', 600, 'instrument-sans-latin-600-normal.woff2')

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>%%FACES%%
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:transparent}
#solid{position:absolute;inset:0;background:#4B1E8C}
#s{position:relative;width:1080px;height:1920px;overflow:hidden;color:#fff;font-family:'Instrument Sans'}
#bgr{position:absolute;left:-200px;right:-200px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:space-around;opacity:.18}
#bgr div{height:18px;display:flex;gap:16px}#bgr i{flex:1;border-radius:999px;background:#6B43A8}
#flash{position:absolute;inset:0;background:#C6F36B;opacity:0;z-index:8}
#wipe{position:absolute;top:-200px;bottom:-200px;width:1300px;left:-2000px;background:#C6F36B;z-index:9;transform:skewX(-12deg)}
header{position:absolute;left:84px;right:84px;top:130px;display:flex;justify-content:space-between;align-items:center;font:600 34px 'Instrument Sans';z-index:6}
.kick{border:3px solid #C6F36B;color:#C6F36B;border-radius:999px;padding:10px 26px;font:600 28px 'Instrument Sans'}
.sc{position:absolute;left:84px;right:84px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;opacity:0}
em{font-style:normal;color:#C6F36B}
.golpe h1{font:800 150px/0.95 'Bricolage Grotesque';letter-spacing:-6px}
.contador .num{font:800 280px/0.9 'Bricolage Grotesque';letter-spacing:-12px;color:#C6F36B;white-space:nowrap;font-variant-numeric:tabular-nums}
.contador p{font:700 66px/1.1 'Bricolage Grotesque';letter-spacing:-2px;margin-top:34px}
.texto p,.pregunta p{font:800 96px/1.04 'Bricolage Grotesque';letter-spacing:-3.5px}
.w{display:inline-block;opacity:0;transform:translateY(40px)}.n{color:#C6F36B}
.cuenta h2{font:800 76px/1.05 'Bricolage Grotesque';letter-spacing:-2.5px;margin-bottom:50px}
.card{background:#3A1670;border:3px solid #6B43A8;border-radius:36px;padding:20px 48px}
.row{display:flex;justify-content:space-between;align-items:baseline;padding:34px 0;border-bottom:3px solid #6B43A8;font:500 44px 'Instrument Sans';color:#D9CCF0;opacity:0}
.row:last-child{border-bottom:0}.row b{font:800 54px 'Bricolage Grotesque';color:#fff;white-space:nowrap}
.row.total{color:#fff}.row.total b{font-size:76px;color:#C6F36B}
.raya .seg{display:flex;gap:10px;margin-bottom:70px}.raya .seg i{flex:1;height:40px;border-radius:999px;background:#6B43A8}
.raya p{font:800 84px/1.06 'Bricolage Grotesque';letter-spacing:-3px}
.pregunta .h{margin-top:70px;font:600 46px 'Instrument Sans';color:#C6F36B}
.bar2{position:absolute;left:84px;right:84px;bottom:210px;height:12px;background:#6B43A8;border-radius:12px;overflow:hidden;z-index:6}.bar2 i{display:block;height:100%;width:0;background:#C6F36B}
.media{left:0;right:0;padding:0 84px}
.media .bg{position:absolute;inset:0;background-size:cover;background-position:center;filter:grayscale(1) contrast(1.15) brightness(.95)}
.media .t1{position:absolute;inset:0;background:#4B1E8C;mix-blend-mode:multiply;opacity:.6}
.media.video .t1{mix-blend-mode:normal;opacity:.45}
.media .t2{position:absolute;inset:0;background:linear-gradient(180deg,#4B1E8Ccc 0%,#4B1E8C22 36%,#4B1E8Cf0 72%)}
.media .cnt{position:relative;margin-top:620px}
.media .big{font:800 220px/0.9 'Bricolage Grotesque';letter-spacing:-9px;color:#C6F36B;white-space:nowrap}
.media p{font:800 80px/1.06 'Bricolage Grotesque';letter-spacing:-3px;margin-top:20px}
.media .cred{position:absolute;right:84px;bottom:260px;font:500 20px 'Instrument Sans';opacity:.7}
footer{position:absolute;left:84px;right:84px;bottom:130px;display:flex;justify-content:space-between;font:600 30px 'Instrument Sans';color:#D9CCF0;z-index:6}
</style></head><body><div id="s"><div id="solid"></div><div id="bgr"></div>
<div id="scs"></div><div id="flash"></div><div id="wipe"></div>
<header><span class="kick">%%KICK%%</span></header>
<div class="bar2"><i id="pb"></i></div><footer><span>Guárdalo para tu quincena</span><span>Compártelo</span></footer></div>
<script>
const E=%%E%%, DUR=%%DUR%%;
const bg=document.getElementById('bgr');for(let r=0;r<14;r++){const d=document.createElement('div');d.innerHTML='<i></i>'.repeat(6+(r%3));bg.appendChild(d)}
const esc=s=>(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const hiw=s=>esc(s).split(/\s+/).map(w=>'<span class="w'+(/\d/.test(w)?' n':'')+'">'+w+'</span>').join(' ');
const host=document.getElementById('scs');
E.forEach(e=>{const d=document.createElement('div');d.className='sc '+e.tipo;
 if(e.tipo=='golpe')d.innerHTML='<h1>'+e.html+'</h1>';
 if(e.tipo=='contador')d.innerHTML='<div class="num"></div><p>'+esc(e.texto)+'</p>';
 if(e.tipo=='texto')d.innerHTML='<p>'+hiw(e.texto)+'</p>';
 if(e.tipo=='cuenta')d.innerHTML='<h2>'+esc(e.titulo)+'</h2><div class="card">'+e.filas.map(r=>'<div class="row '+(r.tipo||'')+'"><span>'+esc(r.c)+'</span><b>'+esc(r.v)+'</b></div>').join('')+'</div>';
 if(e.tipo=='raya')d.innerHTML='<div class="seg">'+'<i></i>'.repeat(e.n)+'</div><p>'+hiw(e.texto)+'</p>';
 if(e.tipo=='foto'||e.tipo=='video'){d.className='sc media '+e.tipo;
   d.innerHTML=(e.tipo=='foto'?'<div class="bg" style="background-image:url(\''+e.img+'\')"></div>':'')+'<div class="t1"></div><div class="t2"></div><div class="cnt">'+(e.cifra?'<div class="big">'+esc(e.cifra)+'</div>':'')+'<p>'+hiw(e.texto)+'</p></div>'+(e.credito?'<div class="cred">'+esc(e.credito)+'</div>':'');}
 if(e.tipo=='pregunta')d.innerHTML='<p>'+hiw(e.texto)+'</p><div class="h">Te leemos en comentarios</div>';
 host.appendChild(d)});
const cl=x=>Math.min(Math.max(x,0),1), ease=x=>1-Math.pow(1-cl(x),3), back=x=>{x=cl(x);const c=1.7;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const fmt=(v,d)=>v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
window.render=t=>{
 [...bg.children].forEach((r,i)=>r.style.transform=`translateX(${((i%2?1:-1)*t*18)%160}px)`);
 document.getElementById('pb').style.width=(100*t/DUR)+'%';
 let fl=0,wipe=-1;
 [...host.children].forEach((el,i)=>{const e=E[i],k=t-e.a,vis=t>=e.a&&t<e.b;
  el.style.opacity=vis?1:0;if(!vis)return;
  if(i>0&&k<0.28)wipe=k/0.28;
  if(k<0.1)fl=Math.max(fl,0.25*(1-k/0.1));
  let sh=0;if((e.tipo=='golpe'||e.tipo=='contador')&&k<0.35)sh=(1-k/0.35)*14;
  const sx=sh*Math.sin(t*90),sy=sh*Math.cos(t*70),s=1+0.04*(k/e.dur);
  if(e.tipo=='foto'||e.tipo=='video'){el.style.transform='none';const g=el.querySelector('.bg');if(g)g.style.transform=`scale(${1.08+0.14*(k/e.dur)}) translate(${-18*(k/e.dur)}px,${-30*(k/e.dur)}px)`;
    const big=el.querySelector('.big');if(big){big.style.transform=`translateX(${(1-ease(k/0.4))*-120}px)`;big.style.opacity=ease(k/0.3);}}
  else if(e.tipo=='golpe')el.style.transform=`translate(${sx}px,${sy}px) scale(${(0.55+0.45*back(k/0.3))*s})`;
  else el.style.transform=`translate(${sx}px,${(1-ease(k/0.3))*90+sy}px) scale(${s})`;
  el.querySelectorAll('.w').forEach((w,j)=>{const p=ease((k-0.15-j*0.07)/0.25);w.style.opacity=p;w.style.transform=`translateY(${(1-p)*40}px)`});
  if(e.tipo=='contador'){const n=el.querySelector('.num');n.textContent=(e.pre||'')+fmt(e.valor*ease(k/1.2),e.dec||0)+(e.suf||'');n.style.fontSize=Math.min(280,Math.floor(1800/n.textContent.length))+'px'}
  if(e.tipo=='cuenta')el.querySelectorAll('.row').forEach((r,j)=>{const p=ease((k-0.3-j*0.4)/0.3);r.style.opacity=p;r.style.transform=`translateX(${(1-p)*-60}px)`});
  if(e.tipo=='raya')el.querySelectorAll('.seg i').forEach((x,j)=>{const on=k>0.2+j*0.09;x.style.background=!on?'#6B43A8':(j==e.hechos?'#C6F36B':(j<e.hechos?'#fff':'#6B43A8'))});
 });
 const cur=E.find(e=>t>=e.a&&t<e.b), isv=cur&&cur.tipo=='video';
 document.getElementById('solid').style.opacity=isv?0:1; bg.style.opacity=isv?0:.18;
 document.getElementById('flash').style.opacity=fl;
 document.getElementById('wipe').style.left=(wipe<0?-2000:(-1700+wipe*3400))+'px';
};
</script></body></html>"""

def eventos():
    ev = []
    for i, e in enumerate(spec['escenas']):
        a = e['a']
        if i > 0: ev.append((max(0, a - 0.12), 'whoosh'))
        if e['tipo'] in ('golpe', 'contador'): ev.append((a, 'impacto'))
        if e['tipo'] == 'contador': ev += [(a + 0.1 + j * 0.08, 'tick') for j in range(13)]
        if e['tipo'] == 'cuenta': ev += [(a + 0.3 + j * 0.4, 'pop') for j in range(len(e['filas']))]
        if e['tipo'] == 'raya': ev += [(a + 0.2 + j * 0.09, 'tick') for j in range(min(e['n'], e['hechos'] + 1))]
        if e['tipo'] == 'pregunta': ev.append((max(0, a - 1.2), 'riser')); ev.append((a, 'cierre'))
    return ev

async def main():
    tmp = tempfile.mkdtemp(); fr = os.path.join(tmp, 'f'); os.makedirs(fr)
    page = os.path.join(tmp, 'r.html')
    html = (HTML.replace('%%FACES%%', FACES)
            .replace('%%KICK%%', spec.get('kicker', '')).replace('%%E%%', json.dumps(spec['escenas'], ensure_ascii=False))
            .replace('%%DUR%%', str(DUR)))
    open(page, 'w').write(html)
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1080, 'height': 1920})
        await pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
        await pg.goto('file://' + page); await pg.evaluate('document.fonts.ready')
        for k in range(int(DUR * FPS)):
            await pg.evaluate(f'render({k / FPS})')
            await pg.screenshot(path=os.path.join(fr, f'{k:05d}.png'), omit_background=True)
        await b.close()
    wav = os.path.join(tmp, 'a.wav'); sonido.pista(DUR, eventos(), wav, semilla=len(spec['escenas']))
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c=0x4B1E8C:s=1080x1920:r={FPS}:d={DUR}']
    for e in VIDS:
        cmd += ['-stream_loop', '-1', '-t', str(e['dur'] + 0.5), '-i', e['vid']]
    cmd += ['-framerate', str(FPS), '-i', os.path.join(fr, '%05d.png'), '-i', wav]
    fc = []; last = '[0:v]'
    for j, e in enumerate(VIDS):
        fc.append(f'[{j+1}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},hue=s=0,eq=contrast=1.1:brightness=-0.05,setpts=PTS-STARTPTS+{e["a"]}/TB[v{j}]')
        fc.append(f"{last}[v{j}]overlay=enable='between(t,{e['a']},{e['b']})':eof_action=pass[b{j}]"); last = f'[b{j}]'
    gi = len(VIDS) + 1
    fc.append(f'{last}[{gi}:v]overlay=format=auto,format=yuv420p[out]')
    cmd += ['-filter_complex', ';'.join(fc), '-map', '[out]', '-map', f'{gi+1}:a', '-t', str(DUR),
            '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', out]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp); print(out, f'{DUR:.1f}s', len(spec['escenas']), 'escenas')

asyncio.run(main())
