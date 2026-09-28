"""Three headless CAD examples; no addons. Use VISUAL_PILOT_OUTPUT.

Construct native BRep geometry, check measured volumes/dimensions, then
export TechDraw projections and editable FCStd/STEP. Not design certification.
"""
from pathlib import Path
import os
import json
import math
import time
import re
import html
import FreeCAD as App
import Part
import TechDraw

out = Path(os.environ['VISUAL_PILOT_OUTPUT']).resolve()
out.mkdir(parents=True, exist_ok=True)
results = []


def finish(doc, shape, name, title, subtitle, lines, expected_volume, checks):
    assert shape.isValid() and len(shape.Solids) == 1, name
    assert math.isclose(shape.Volume, expected_volume, rel_tol=1e-8), (name, shape.Volume, expected_volume)
    model = doc.addObject('PartDesign::Feature', 'Result')
    model.Shape = shape
    doc.recompute()
    doc.saveAs(str(out / (name + '.FCStd')))
    shape.exportStep(str(out / (name + '.step')))
    centered = shape.copy()
    centered.translate(-shape.BoundBox.Center)
    # Real TechDraw visible-edge projection, not hand-drawn imitation.
    snippet = TechDraw.projectToSVG(centered, App.Vector(1, -1.6, 1.2))
    snippet = re.sub(r'stroke-width="[^"]+"', 'stroke-width="1.5"', snippet).replace('<path ', '<path vector-effect="non-scaling-stroke" ')
    scale = 360 / shape.BoundBox.DiagonalLength
    front = TechDraw.projectToSVG(centered, App.Vector(0, -1, 0))
    front = re.sub(r'stroke-width="[^"]+"', 'stroke-width="1.5"', front).replace('<path ', '<path vector-effect="non-scaling-stroke" ')
    descriptions = ''.join(f'<text x="40" y="{510+i*29}" font-size="20">{html.escape(line)}</text>' for i,line in enumerate(lines))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:freecad="http://www.freecadweb.org/wiki/index.php?title=Svg_Namespace" width="1000" height="630" viewBox="0 0 1000 630">
<title>{html.escape(title)}</title><rect width="1000" height="630" fill="#fafcfd"/>
<g font-family="DejaVu Sans,sans-serif" fill="#193f58">
<text x="40" y="48" font-size="29" font-weight="bold">{html.escape(title)}</text>
<text x="40" y="82" font-size="19">{html.escape(subtitle)}</text>
<text x="270" y="125" text-anchor="middle" font-size="19">Térbeli nézet</text>
<text x="750" y="125" text-anchor="middle" font-size="19">Elölnézet</text>
{descriptions}</g>
<g transform="translate(270,300) rotate(90) scale({scale})">{snippet}</g>
<g transform="translate(750,300) rotate(90) scale({scale})">{front}</g>
</svg>'''
    (out/(name+'.svg')).write_text(svg)
    results.append({'name':name, 'volume_mm3':shape.Volume, 'expected_volume_mm3':expected_volume,
                    'checks':checks, 'freecad_version':App.Version()})
    App.closeDocument(doc.Name)


started = time.perf_counter()
doc = App.newDocument('Bracket')
base = Part.makeBox(80, 50, 8)
upright = Part.makeBox(8, 50, 60)
solid = base.fuse(upright).removeSplitter()
for x in (30, 65):
    solid = solid.cut(Part.makeCylinder(5, 8, App.Vector(x, 25, 0)))
solid = solid.cut(Part.makeCylinder(5, 8, App.Vector(0, 25, 40), App.Vector(1,0,0))).removeSplitter()
assert solid.BoundBox.XLength == 80 and solid.BoundBox.YLength == 50 and solid.BoundBox.ZLength == 60
for p in (App.Vector(30,25,4), App.Vector(65,25,4), App.Vector(4,25,40)):
    assert not solid.isInside(p, 1e-7, True)
finish(doc,solid,'cad-bracket','Egy alkatrész, két nézet','A furatok a modell részei; a nézeteket ugyanaz a test adja.',
       ['Külső méret: 80 × 50 × 60 mm; lemezvastagság: 8 mm.', 'Három átmenő furat: Ø10 mm. Szemléltető modell, nem gyártási rajz.'],
       80*50*8 + 8*50*60 - 8*50*8 - 3*math.pi*25*8,
       ['80×50×60 mm bounds','three bore centers empty','one valid solid','analytic volume'])

doc = App.newDocument('WindowWall')
wall = Part.makeBox(3000, 300, 2800)
opening = Part.makeBox(1200, 300, 1400, App.Vector(900, 0, 900))
solid = wall.cut(opening).removeSplitter()
assert not solid.isInside(App.Vector(1500,150,1600),1e-7,True)
assert solid.isInside(App.Vector(1500,150,400),1e-7,True)
finish(doc,solid,'cad-wall','A nyílás térfogatot vesz el a falból','Egyszerű geometriai modell; áthidaló és szerkezeti méretezés nélkül.',
       ['Fal: 3,00 × 2,80 m; vastagság: 0,30 m. Nyílás: 1,20 × 1,40 m.', 'Nettó térfogat: (3,00 × 2,80 − 1,20 × 1,40) × 0,30 = 2,016 m³.'],
       (3000*2800 - 1200*1400)*300,
       ['opening center empty','wall below opening remains','one valid solid','net volume 2.016 m³'])

doc = App.newDocument('ISection')
solid = Part.makeBox(120,400,12)
solid = solid.fuse(Part.makeBox(120,400,12,App.Vector(0,0,188)))
solid = solid.fuse(Part.makeBox(8,400,176,App.Vector(56,0,12))).removeSplitter()
assert solid.BoundBox.ZLength == 200 and solid.BoundBox.XLength == 120
assert not solid.isInside(App.Vector(20,200,100),1e-7,True)
assert solid.isInside(App.Vector(60,200,100),1e-7,True)
finish(doc,solid,'cad-section','I keresztmetszet: övek és gerinc','A térbeli tartó és az elölnézeti keresztmetszet összetartozik.',
       ['Magasság: 200 mm; övszélesség: 120 mm; övvastagság: 12 mm.', 'Gerincvastagság: 8 mm. Terület: 2 × 120 × 12 + 8 × 176 = 4288 mm².'],
       (2*120*12 + 8*176)*400,
       ['200 mm high','web center solid; side cavity empty','one valid solid','section area from volume/400 = 4288 mm²'])
(out/'cad-checks.json').write_text(json.dumps({'seconds':time.perf_counter()-started,'cases':results},indent=2)+'\n')
