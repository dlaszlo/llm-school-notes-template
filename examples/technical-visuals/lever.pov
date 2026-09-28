// Prescribed poses, NOT a dynamic simulation. Length = 1 model unit.
// Vertical downward force: perpendicular moment arm = cos(theta).
#version 3.7;
global_settings { assumed_gamma 1.0 }
background { color rgb <0.96,0.97,0.99> }
camera { orthographic location <0.5,0.2,-5> look_at <0.5,0.2,0>
  right x*3.15 up y*2.1 }
light_source { <-3,5,-7> color rgb 1 }
#declare Theta = radians(-45+90*clock);
#declare End = <cos(Theta),sin(Theta),0>;
#declare Blue = texture { pigment { color rgb <0.08,0.36,0.62> } finish { diffuse 0.8 } }
#declare Red = texture { pigment { color rgb <0.8,0.08,0.05> } finish { diffuse 0.8 } }
// Fixed pivot and rigid arm.
cylinder { <0,0,0>, End, 0.025 texture { Blue } }
cylinder { <0,0,-0.055>, <0,0,0.055>, 0.05 pigment { color rgb <0.25,0.28,0.32> } }
// Arrow tip ends at the application point; shaft stays vertical.
cylinder { End+<0,0.35,0>, End+<0,0.075,0>, 0.012 texture { Red } }
cone { End+<0,0.075,0>, 0.037, End, 0 texture { Red } }
// Horizontal projection illustrates the perpendicular moment arm.
cylinder { <0,-0.78,0>, <End.x,-0.78,0>, 0.006 pigment { color rgb <0.2,0.2,0.2> } }
#for (Y,-0.75,End.y,0.065)
  cylinder { <End.x,Y,0.03>, <End.x,min(Y+0.025,End.y),0.03>, 0.003 pigment { color rgb 0.5 } }
#end
#debug concat("CHECK theta_deg=",str(degrees(Theta),0,6)," x=",str(End.x,0,9)," y=",str(End.y,0,9),"\n")
