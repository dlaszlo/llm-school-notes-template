"""Run with FreeCADCmd/freecadcmd; outputs go to VISUAL_PILOT_OUTPUT.

Headless parameterized gear, independent radial/angle checks, native model
and a sampled SVG preview. No GUI imports, network calls or installation.
"""
import json
import math
import os
from pathlib import Path
import time

import FreeCAD as App
import Part
import InvoluteGearFeature


def run():
    output = Path(os.environ["VISUAL_PILOT_OUTPUT"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    doc = App.newDocument("GearPilot")
    gear = InvoluteGearFeature.makeInvoluteGear("Gear")
    gear.NumberOfTeeth = 20
    gear.Modules = "2 mm"
    gear.PressureAngle = "20 deg"
    gear.HighPrecision = True
    gear.ProfileShiftCoefficient = 0
    doc.recompute()
    wire = gear.Shape
    assert wire.isValid() and wire.isClosed(), "Invalid or open gear outline"
    solid = Part.Face(wire).extrude(App.Vector(0, 0, 5))
    assert solid.isValid() and len(solid.Solids) == 1
    body = doc.addObject("PartDesign::Feature", "ExtrudedGear")
    body.Shape = solid
    model_seconds = time.perf_counter() - started

    # Independent expected involute angular thickness at three radii.
    # This checks the actual CAD intersections, not just the input properties.
    z, module, pressure = 20, 2, math.radians(20)
    pitch_radius = z * module / 2
    base_radius = pitch_radius * math.cos(pressure)
    period = 2 * math.pi / z
    checks = []
    for radius in (19.5, 20.0, 21.0):
        section = wire.section(Part.makeCircle(radius))
        angles = sorted(math.atan2(v.Point.y, v.Point.x) % (2 * math.pi)
                        for v in section.Vertexes)
        assert len(angles) == 2 * z, (radius, len(angles))
        alpha_r = math.acos(base_radius / radius)
        expected = math.pi / (2 * z) + math.tan(pressure) - pressure - (math.tan(alpha_r) - alpha_r)
        observed = [abs((angle + period / 2) % period - period / 2) for angle in angles]
        error = max(abs(a - expected) for a in observed)
        assert error < 0.0001, (radius, error)
        checks.append({"radius_mm": radius, "intersections": len(angles), "max_angle_error_rad": error})

    points = wire.discretize(Deflection=0.01)
    radii = [math.hypot(p.x, p.y) for p in points]
    assert abs(max(radii) - 22) < 0.02
    assert abs(min(radii) - 17.5) < 0.02
    svg_path = "M " + " L ".join(f"{p.x:.5f},{-p.y:.5f}" for p in points) + " Z"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="860" viewBox="-26 -29 52 56">
<title>Involute gear: twenty teeth, module two millimetres, pressure angle twenty degrees</title>
<rect x="-26" y="-29" width="52" height="56" fill="white"/>
<text x="0" y="-25" text-anchor="middle" font-family="sans-serif" font-size="1.7">z = 20 · m = 2 mm · α = 20°</text>
<path d="{svg_path}" fill="#ddebf6" stroke="#173e5a" stroke-width="0.12"/>
<circle r="20" fill="none" stroke="#a03416" stroke-dasharray="0.8 0.5" stroke-width="0.1"/>
<circle r="{base_radius:.6f}" fill="none" stroke="#305936" stroke-dasharray="0.2 0.4" stroke-width="0.1"/>
<text x="0" y="-1" text-anchor="middle" font-family="sans-serif" font-size="1.5">Osztókör: d = 40 mm</text>
<text x="0" y="2" text-anchor="middle" font-family="sans-serif" font-size="1.5">Alapkör: d ≈ {2*base_radius:.2f} mm</text>
<text x="0" y="25" text-anchor="middle" font-family="sans-serif" font-size="1.3">Paraméteres mintaprofil; nem gyártási rajz.</text>
</svg>'''
    (output / "gear.svg").write_text(svg, encoding="utf-8")
    doc.recompute()
    doc.saveAs(str(output / "gear.FCStd"))
    solid.exportStep(str(output / "gear.step"))
    result = {"freecad_version": App.Version(), "model_seconds": model_seconds,
              "total_script_seconds": time.perf_counter() - started,
              "checks": checks, "preview_deflection_mm": 0.01,
              "limitations": "No gear pair/contact/load/tolerance or manufacturing certification. No thread or wall tested."}
    (output / "gear-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    App.closeDocument(doc.Name)


run()
