"""Generate a local road review: dated aerial evidence versus representative PBR material."""
from pathlib import Path
import datetime,html,json

ROOT=Path(__file__).resolve().parents[1]
ROUTES={'preview':'/road-reference/asphalt-1k','balanced':'/road-reference/asphalt-2k','presentation':'/road-reference/asphalt-4k'}
LABELS={'preview':'Preview · 1K','balanced':'Balanced · 2K','presentation':'Presentation · 4K'}

def render(manifest):
    selected=manifest['selected_quality']
    if selected not in ROUTES:raise ValueError('Unknown active quality tier')
    diffuse={r['tier']:r for r in manifest['maps'] if r['channel']=='Diffuse'}
    if set(diffuse)!=set(ROUTES):raise ValueError('Three diffuse quality references are required')
    cards=[]
    for tier in ROUTES:
        current=tier==selected;row=diffuse[tier]
        badge='<span class="badge">Active in working scene</span>' if current else ''
        cards.append(f'''<article class="tier"><div class="tier-title"><h3>{html.escape(LABELS[tier])}</h3>{badge}</div>
<img src="{ROUTES[tier]}" alt="Poly Haven asphalt diffuse image at {html.escape(row['resolution'].upper())} resolution" loading="lazy" width="320" height="320">
<p>{html.escape(manifest['tiers'][tier])}.</p><button type="button" data-tier="{tier}" aria-pressed="{'true' if current else 'false'}">Inspect {html.escape(row['resolution'].upper())} image</button></article>''')
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Edgewater · Road references and surface quality</title>
<style>
:root{color-scheme:light;--ink:#18382f;--muted:#52675e;--line:#d4dfd8;--paper:#f4f6f1;--accent:#235f47}*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}header{background:#173d32;color:#fff;padding:30px max(24px,calc((100vw - 1420px)/2))}header a{color:#d5efdd}h1{margin:4px 0 8px;font-size:clamp(26px,3vw,40px);line-height:1.18}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:12px}header p{max-width:880px;margin-bottom:0}
main{max-width:1468px;margin:auto;padding:26px 24px 40px}h2{font-size:24px;line-height:1.25;margin:3px 0 12px}h3{font-size:17px;margin:0}p{margin:10px 0 16px}a{color:#215c43}figure{margin:0}figcaption{font-size:14px;color:var(--muted);margin-top:12px}.reference-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:24px;align-items:start}.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px;overflow:hidden}.label{font-size:12px;letter-spacing:.09em;font-weight:750;text-transform:uppercase;color:var(--accent)}.aerial{display:block;width:100%;max-height:820px;object-fit:contain;background:#e6ece5;border-radius:8px}.focus{display:block;width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;background:#ddd}.facts{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.facts span,.badge{font-size:12px;background:#e7f0e6;color:#244b34;border-radius:20px;padding:5px 10px}.note{background:#fff4d8;border-left:4px solid #b58a24;padding:12px 15px;margin:20px 0;color:#5b491d}.quality{margin-top:24px}.tiers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.tier{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px}.tier-title{min-height:65px}.tier img{width:100%;height:auto;aspect-ratio:1;object-fit:cover;border-radius:7px;display:block}.tier p{min-height:55px;color:var(--muted);font-size:14px}button{font:inherit;font-size:14px;background:#fff;color:var(--accent);border:1px solid #8ba995;border-radius:7px;padding:9px 13px;cursor:pointer}button[aria-pressed=true]{background:var(--accent);color:#fff}button:focus-visible,a:focus-visible{outline:3px solid #cc9c27;outline-offset:3px}.credit{font-size:14px;color:var(--muted)}details{background:#fff;border:1px solid var(--line);border-radius:8px;margin-top:24px;padding:14px}summary{cursor:pointer;font-weight:650}footer{font-size:13px;color:var(--muted);margin-top:22px}@media(max-width:850px){.reference-grid{grid-template-columns:1fr}.aerial{max-height:650px}.tiers{grid-template-columns:1fr}.tier-title,.tier p{min-height:0}.tier img{max-height:420px;object-fit:contain}main{padding:18px 14px}.panel{padding:17px}}
</style></head><body>
<header><div class="eyebrow">College Park · TWIN</div><h1>Edgewater road review</h1><p>Inspect the real street reference beside the asphalt material selected for the digital twin.</p><p><a href="/">Back to parcel map</a></p></header>
<main><div class="reference-grid">
<section class="panel"><div class="label">Real place · Historical aerial reference</div><h2>Princeton to southern Smith junction</h2>
<div class="facts"><span>OCPA · January 2025</span><span>Original local reference export</span></div>
<figure><a href="/road-reference/aerial2025" target="_blank" rel="noopener"><img class="aerial" src="/road-reference/aerial2025" alt="January 2025 OCPA aerial showing the Edgewater pilot block, intersections, road markings, parked cars, storefront roofs and trees" width="768" height="1152"></a>
<figcaption>Use the dated aerial to review road layout, markings, parking and canopy. Shadows and trees can hide curbs and sidewalks. Source: <a href="https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/info/iteminfo?f=json">OCPA January 2025 flight metadata</a>.</figcaption></figure>
<p class="credit">Local reference review only. This aerial is not a pavement texture; publication and redistribution eligibility remain unresolved.</p></section>
<section class="panel"><div class="label">Representative surface · PBR material</div><h2>Asphalt surface detail</h2>
<div class="facts"><span>CC0 · Poly Haven</span><span>Physical repeat: __TILE__ m × __TILE__ m</span><span>Working scene: __ACTIVE__</span></div>
<figure><a id="focus-link" href="__FOCUS_ROUTE__" target="_blank" rel="noopener"><img id="focus-image" class="focus" src="__FOCUS_ROUTE__" alt="Poly Haven representative asphalt diffuse image at the balanced 2K working quality" width="640" height="640"></a><figcaption id="focus-caption" role="status" aria-live="polite">Inspecting __ACTIVE__. Diffuse color preview; the scene also uses normal and roughness maps.</figcaption></figure>
<p>This material supplies plausible asphalt grain and shading. It is representative material, not a measurement or photograph of Orlando pavement condition.</p>
<p class="credit"><strong>Powered by Poly Haven</strong> · <a href="__ASSET_URL__">asphalt_02 source asset</a> · <a href="__LICENSE_URL__">CC0 license</a></p></section></div>
<div class="note">Road widths, sidewalk geometry, material scale in the scene and street-level realism still require review. Higher image resolution does not establish geographic accuracy or measured performance.</div>
<section class="quality" aria-labelledby="quality-title"><div class="label">Choose an image to inspect</div><h2 id="quality-title">Three quality roles</h2><p>All three resolutions use the same __TILE__ m physical repeat. These buttons change the reference preview here; they do not switch the live scene.</p><div class="tiers">__CARDS__</div></section>
<details><summary>Source and quality record</summary><p>Source: __PUBLISHER__ / __ASSET__. Acquired or verified __VERIFIED__. Active quality from the local material register: __ACTIVE__.</p><p>Diffuse, OpenGL normal and roughness maps are available at 1K, 2K and 4K. Parent acquisition recorded publisher MD5 and local SHA-256 per file. This page presents the actual diffuse files, rather than a synthetic rendered road image.</p><p>The aerial is historical evidence of a real location. The CC0 asphalt is a separate surface asset. Neither completes existing-condition road geometry or pedestrian acceptance.</p></details>
<footer>Generated __GENERATED__. All displayed images are loaded from this local project.</footer></main>
<script>const routes=__ROUTES__,labels=__LABELS__;document.querySelectorAll('[data-tier]').forEach(button=>button.addEventListener('click',()=>{const tier=button.dataset.tier;document.getElementById('focus-image').src=routes[tier];document.getElementById('focus-image').alt='Poly Haven representative asphalt diffuse image: '+labels[tier];document.getElementById('focus-link').href=routes[tier];document.getElementById('focus-caption').textContent='Inspecting '+labels[tier]+'. Diffuse color preview; the scene also uses normal and roughness maps.';document.querySelectorAll('[data-tier]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));}));</script></body></html>'''.replace('__TILE__',f"{manifest['tile_m']:.0f}").replace('__ACTIVE__',html.escape(LABELS[selected])).replace('__FOCUS_ROUTE__',ROUTES[selected]).replace('__CARDS__',''.join(cards)).replace('__ASSET_URL__',html.escape(manifest['asset_url'],quote=True)).replace('__LICENSE_URL__',html.escape(manifest['license_url'],quote=True)).replace('__PUBLISHER__',html.escape(manifest['publisher'])).replace('__ASSET__',html.escape(manifest['asset'])).replace('__VERIFIED__',html.escape(manifest['acquired_or_verified_utc'])).replace('__GENERATED__',html.escape(now)).replace('__ROUTES__',json.dumps(ROUTES)).replace('__LABELS__',json.dumps(LABELS))

def build(root=ROOT):
    manifest=json.loads((root/'data/processed/road_materials.json').read_text(encoding='utf-8'))
    for row in manifest['maps']:
        asset=(root/row['file']).resolve()
        if not asset.is_relative_to((root/'assets/generated/road_materials').resolve()) or not asset.is_file():raise ValueError('Missing or invalid material file: '+row['file'])
    aerial=root/'data/imagery/OCPA_Aerials2025_edgewater-princeton-smith-south-v1.jpg'
    if not aerial.is_file():raise ValueError('Local dated aerial reference is missing')
    output=root/'data/transport/road_reference_gallery.html';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(render(manifest),encoding='utf-8')
    print(json.dumps({'output':str(output),'current_working_quality':manifest['selected_quality'],'physical_repeat_m':manifest['tile_m'],
       'diffuse_preview_routes':ROUTES,'aerial_route':'/road-reference/aerial2025'},indent=2));return output

if __name__=='__main__':build()
