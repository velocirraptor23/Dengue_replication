"""Blender 5.2: export static native assets from the final movie project.
Usage: blender -b --python export_assets.py -- /path/to/Alchemistry_2027.blend
"""
import bpy,sys,json,os
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else ROOT.parent/'Alchemistry_Final/Alchemistry_2027.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
exports=[]
def setup(name,source,frame,predicate,normalize=False):
 bpy.context.window.scene=source;source.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
 target=bpy.data.scenes.new(name);target.world=bpy.data.worlds.new(name+' world');target.world.use_nodes=True
 target.world.node_tree.nodes.get('Background').inputs[0].default_value=(.025,.035,.055,1)
 target.world.node_tree.nodes.get('Background').inputs[1].default_value=.55
 originals=[o for o in source.objects if o.type in {'MESH','CURVE','SURFACE'} and predicate(o)]
 meshes=[];cache={}
 for o in originals:
  eo=o.evaluated_get(dg)
  # Identical rigid copies share one mesh; deformed objects are evaluated independently.
  key=o.data.as_pointer() if not o.modifiers and not getattr(o.data,'shape_keys',None) else o.as_pointer()
  if key not in cache:cache[key]=bpy.data.meshes.new_from_object(eo,preserve_all_data_layers=True,depsgraph=dg)
  me=cache[key]
  if not me.vertices:continue
  n=bpy.data.objects.new(o.name,me);target.collection.objects.link(n);n.matrix_world=eo.matrix_world.copy();n['source_object']=o.name
  meshes.append(n)
 bpy.context.window.scene=target;target.view_layers[0].update()
 pts=[o.matrix_world@Vector(p) for o in meshes for p in o.bound_box]
 lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
 center=(lo+hi)*.5;span=max(hi-lo)
 if normalize:
  trans=Matrix.Scale(4/span,4)@Matrix.Translation(-center)
  for o in meshes:o.matrix_world=trans@o.matrix_world
  center=Vector((0,0,0));span=4
 camera=bpy.data.objects.new('Camera | overview',bpy.data.cameras.new(name+' overview'));target.collection.objects.link(camera)
 camera.location=center+Vector((0,-.85,1.65)).normalized()*span*1.65
 camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=span*1.7;camera.data.clip_end=1000;camera.data.clip_start=.001;target.camera=camera
 for label,offset,power,size in [('Key',(-.6,-.7,1.4),1300,1),('Fill',(.9,.2,1),1000,.8),('Rim',(-.4,.8,.7),1500,.7)]:
  light=bpy.data.objects.new(label,bpy.data.lights.new(label,'AREA'));target.collection.objects.link(light);light.location=center+Vector(offset)*span
  light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power*(span/4)**2;light.data.shape='DISK';light.data.size=span*size
 target.render.engine='CYCLES';target.cycles.samples=24;target.cycles.use_denoising=True;target.render.resolution_x=1200;target.render.resolution_y=900;target.render.resolution_percentage=100;target.render.image_settings.file_format='PNG'
 target.view_settings.view_transform='AgX';target.frame_start=target.frame_end=1;target['source_frame']=frame;target['asset_note']='Static, separately editable native meshes; no animation or add-ons needed.'
 target.render.filepath=str(ROOT/'previews'/f'{name}.png')
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.clip_end=1000
 exports.append((target,meshes,span))
 return target
core=bpy.data.scenes['02 | Intracellular molecular story']
# Current cell, excluding the invisible source models and shot-only effects.
setup('Cell_environment',core,797,lambda o:not o.hide_render and max(o.dimensions)>1e-5 and not any(x in o.name for x in ['Cloud','cloud','funnel','Funnel']))
eg=bpy.data.scenes['02b | RNA packaging and outward release']
setup('2R6P_ensemble',eg,346,lambda o:o.name in ['Egress | actual complete 2R6P assembly','RNA copy | same strand enters the assembly'],True)
setup('6MO0_protease',core,960,lambda o:o.name=='6MO0 | Folding ribbon mesh' or o.name=='JVJ | Exact deposited bound pose',True)
# Freeze animated material values as evaluated above, so assets have no timeline dependency.
for mat in bpy.data.materials:
 mat.animation_data_clear()
 if mat.node_tree:mat.node_tree.animation_data_clear()
for target,meshes,span in exports:
 bpy.context.window.scene=target
 target.render.filepath=str(ROOT/'previews'/f'{target.name}.png')
 bpy.data.libraries.write(str(ROOT/'assets'/f'{target.name}.blend'),{target},fake_user=True,compress=True)
 print('EXPORTED',target.name,len(meshes),flush=True)
 bpy.ops.render.render(write_still=True,scene=target.name)
json.dump([dict(name=s.name,objects=len(ms),vertices=sum(len(o.data.vertices) for o in ms),source_frame=s['source_frame']) for s,ms,sp in exports],open(ROOT/'manifest.json','w'),indent=2)
