// Two routes to the same height; no force/dynamics claim. Model units = metres.
#version 3.7;
global_settings { assumed_gamma 1.0 }
background { color rgb <0.92,0.95,0.98> }
camera { orthographic location <6,5,-10> look_at <0,0.7,0> right x*9 up y*6 }
light_source { <-4,10,-6> color rgb 1.1 area_light <4,0,0>,<0,0,4>,17,17 adaptive 2 jitter }
light_source { <4,6,6> color rgb 0.35 }
plane { y,-0.025 pigment { color rgb <0.91,0.93,0.95> } finish { diffuse 0.8 } }
#declare H = 1.5;
#macro Ramp(L,X,Col)
union {
 mesh {
  triangle { <0,0,-.65>,<L,0,-.65>,<L,H,-.65> }
  triangle { <0,0,.65>,<L,H,.65>,<L,0,.65> }
  triangle { <0,0,-.65>,<L,H,-.65>,<L,H,.65> }
  triangle { <0,0,-.65>,<L,H,.65>,<0,0,.65> }
  triangle { <L,0,-.65>,<L,0,.65>,<L,H,.65> }
  triangle { <L,0,-.65>,<L,H,.65>,<L,H,-.65> }
  pigment { color rgb Col } finish { diffuse 0.85 }
 }
 cylinder { <0,.03,-.67>,<L,H+.03,-.67>,.028 pigment { color rgb <0.08,0.26,0.4> } }
 cylinder { <L+.18,0,-.65>,<L+.18,H,-.65>,.018 pigment { color rgb <0.85,0.32,0.07> } }
 sphere { <L+.18,0,-.65>,.035 pigment { color rgb <0.85,0.32,0.07> } }
 sphere { <L+.18,H,-.65>,.035 pigment { color rgb <0.85,0.32,0.07> } }
 translate <X-L/2,0,0>
}
#end
Ramp(3,-2.2,<0.25,0.59,0.73>)
Ramp(1.5,2.2,<0.72,0.78,0.84>)
#debug "CHECK equal_height=1.5 run_long=3 run_short=1.5\n"
