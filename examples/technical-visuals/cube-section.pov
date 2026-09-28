// x+y-z=0 passes through the cube centre and cuts six edge midpoints.
#version 3.7;
global_settings { assumed_gamma 1.0 }
background { color rgb <0.93,0.96,0.99> }
camera { location <6,4,-7> look_at <0,0,0> right x*image_width/image_height angle 32 }
light_source { <-3,7,-6> color rgb 1.1 area_light <3,0,0>,<0,0,3>,17,17 adaptive 2 jitter }
light_source { <5,1,4> color rgb .35 }
plane { y,-1.3 pigment { color rgb <.89,.92,.95> } }
intersection {
 box { <-1,-1,-1>,<1,1,1> pigment { color rgb <.18,.49,.68> } }
 plane { <1,1,-1>,0 pigment { color rgb <1,.64,.2> } }
 finish { diffuse .85 }
}
#declare P=array[6] { <1,-1,0>,<1,0,1>,<0,1,1>,<-1,1,0>,<-1,0,-1>,<0,-1,-1> }
#for(I,0,5)
 #debug concat("POINT ",vstr(3,P[I],",",0,6),"\n")
 cylinder { P[I],P[mod(I+1,6)],.016 pigment { color rgb <.35,.16,.035> } }
 sphere { P[I],.028 pigment { color rgb <.35,.16,.035> } }
#end
// Thin neutral lines retain the full original cube as an orientation guide.
#for(A,-1,1,2)
 #for(B,-1,1,2)
  cylinder { <-1,A,B>,<1,A,B>,.006 pigment { color rgb <.45,.51,.57> } no_shadow }
  cylinder { <A,-1,B>,<A,1,B>,.006 pigment { color rgb <.45,.51,.57> } no_shadow }
  cylinder { <A,B,-1>,<A,B,1>,.006 pigment { color rgb <.45,.51,.57> } no_shadow }
 #end
#end
#debug "CHECK plane=x+y-z=0 cube_side=2 section_side=sqrt(2)\n"
