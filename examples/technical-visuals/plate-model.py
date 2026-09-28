"""Headless built-in FreeCAD/TechDraw example, not a manufacturing drawing."""
from pathlib import Path
import json
import math
import os
import FreeCAD as App
import Part
import TechDraw

out = Path(os.environ['VISUAL_OUTPUT_DIR'])
plate = Part.makeBox(80, 50, 8)
bore = Part.makeCylinder(10, 8, App.Vector(40, 25, 0))
shape = plate.cut(bore)
assert shape.isValid() and len(shape.Solids) == 1
expected = (80 * 50 - math.pi * 10**2) * 8
assert math.isclose(shape.Volume, expected, rel_tol=1e-9)
assert not shape.isInside(App.Vector(40, 25, 4), 1e-7, True)
doc = App.newDocument('PlateExample')
obj = doc.addObject('PartDesign::Feature', 'Plate')
obj.Shape = shape
doc.recompute()
doc.saveAs(str(out / 'plate.FCStd'))
shape.exportStep(str(out / 'plate.step'))
shape.translate(-shape.BoundBox.Center)
projection = TechDraw.projectToSVG(shape, App.Vector(1, -1.6, 1.2))
(out / 'figure.svg').write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="580" viewBox="0 0 900 580">
<title>Plate with a through-hole, axonometric illustration</title>
<rect width="900" height="580" fill="white"/>
<g font-family="DejaVu Sans,sans-serif" fill="#193f58">
<text x="35" y="45" font-size="25">One solid model, a real projected view</text>
<text x="35" y="85" font-size="20">80 × 50 × 8 mm plate; central through-hole: diameter 20 mm</text>
<text x="35" y="535" font-size="18">Illustrative CAD model, not a dimensioned manufacturing drawing.</text>
</g><g transform="translate(450,300) rotate(90) scale(5)">{projection}</g></svg>''')
(out / 'checks.json').write_text(json.dumps({'freecad_version': App.Version(), 'valid_solid': True,
    'volume_mm3': shape.Volume, 'expected_volume_mm3': expected, 'bore_center_empty': True}, indent=2)+'\n')
App.closeDocument(doc.Name)
