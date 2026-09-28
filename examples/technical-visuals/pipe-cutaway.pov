// Three-quarter hollow cylinder: visible cut faces reveal wall thickness.
#version 3.7;
global_settings { assumed_gamma 1.0 }
background { color rgb <0.94,0.96,0.98> }
camera { location <6,5,-7> look_at <0,1.3,0> right x*image_width/image_height angle 40 }
light_source { <-4,8,-6> color rgb 1.1 area_light <3,0,0>,<0,0,3>,17,17 adaptive 2 jitter }
light_source { <5,4,5> color rgb 0.4 }
plane { y,-.03 pigment { color rgb <0.9,0.92,0.94> } }
difference {
 cylinder { <0,0,0>,<0,3,0>,1.3 }
 cylinder { <0,-.01,0>,<0,3.01,0>,1.0 }
 box { <0,-.02,-2>,<2,3.02,0> }
 texture { pigment { color rgb <0.13,0.48,0.65> } finish { diffuse .8 specular .25 roughness .045 } }
 cutaway_textures
}
// Emphasize the two radial cut edges and reveal the 0.3-unit wall.
box { <1.0,0,-.008>,<1.3,3,.008> pigment { color rgb <0.94,0.62,0.21> } }
box { <-.008,0,-1.3>,<.008,3,-1.0> pigment { color rgb <0.94,0.62,0.21> } }
#debug "CHECK outer_radius=1.3 inner_radius=1.0 thickness=0.3 height=3 removed_quadrant=1\n"
