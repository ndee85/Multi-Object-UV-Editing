# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Multi Object UV Editing",
    "author": "Andreas Esau",
    "version": (0,9,7),
    "blender": (2, 7, 4),
    "location": "Object Tools",
    "description": "This Addon enables a quick way to create one UV Layout for multiple objects.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "UV"}

import bpy
from bpy.props import IntProperty, FloatProperty

def deselect_all(context):
    for obj in context.selected_objects:
        obj.select = False

def get_selected_mesh_objects(context):
    return [obj for obj in context.selected_objects if obj.type=='MESH']


class MultiObjectUVEdit(bpy.types.Operator):
    """This operator gives you the ability to edit the uv of multiple objects at once."""
    bl_idname = "object.multi_object_uv_edit"
    bl_label = "Multi object UV edit"
    bl_options = {"REGISTER","UNDO"}
    
    multi_object = None
    initial_objects = []
    initial_objects_hide_render = []
    active_object = None

    def leave_editing_mode(self,context):
        mesh_select_mode = list(context.tool_settings.mesh_select_mode)
        context.tool_settings.mesh_select_mode = (True,False,False)
        self.multi_object.select = True
        context.scene.objects.active = self.multi_object
        
        ### unhide all vertices
        bpy.ops.mesh.reveal()
    
        ### copy uvs based on the vertex groups to its final object
        for v_group in self.multi_object.vertex_groups:
            
            ### select object vertex group and separate mesh into its own object
            num_verts = self.select_vertex_group(self.multi_object,v_group.name)
            if num_verts > 0:
                bpy.ops.mesh.separate(type="SELECTED")
                tmp_obj = context.selected_objects[0]
                tmp_obj.name = v_group.name+"_tmp"
                
                
                ### go into object mode select newely created object and transfer the uv's to its final object
                bpy.ops.object.mode_set(mode='OBJECT')
                
                deselect_all(context)
                    
                tmp_obj.select = True   
                context.scene.objects.active = tmp_obj
                original_object = bpy.data.objects[v_group.name]
                original_object.hide = False
                original_object.select = True
                
                if len(tmp_obj.data.uv_textures) > 0:
                    if tmp_obj.data.uv_textures.active.name not in bpy.data.objects[v_group.name].data.uv_textures:
                        new_uv_layer = bpy.data.objects[v_group.name].data.uv_textures.new(tmp_obj.data.uv_textures.active.name)
                        original_object.data.uv_textures.active = new_uv_layer
                    else:
                        original_object.data.uv_textures.active = original_object.data.uv_textures[self.multi_object.data.uv_textures.active.name]

                    bpy.ops.object.join_uvs()
                    self.assign_tex_to_uv(tmp_obj.data.uv_textures.active,original_object.data.uv_textures.active)
                    
                ### delete the tmp object
                original_object.select = False
                tmp_obj.select = False
                context.scene.objects.active = self.multi_object
                bpy.context.scene.objects.unlink(tmp_obj)
                bpy.data.objects.remove(tmp_obj)
                bpy.ops.object.mode_set(mode='EDIT')        
            
        ### restore everything
        context.tool_settings.mesh_select_mode = mesh_select_mode
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.scene.objects.unlink(self.multi_object)
        bpy.data.objects.remove(self.multi_object)
        for i,object in enumerate(self.initial_objects):
            object.select = True
            object.hide_render = self.initial_objects_hide_render[i]
            
        context.scene.objects.active = self.active_object
        bpy.ops.ed.undo_push(message="Multi UV edit") 
    
    def assign_tex_to_uv(self,src_uv,dst_uv):
        if len(src_uv.data) == len(dst_uv.data):
            for i,data in enumerate(src_uv.data):
                image = data.image
                dst_uv.data[i].image = image
        else:
            self.report({'INFO'}, "Mesh has been edited. Modifying UVS is not possible for edited meshes.")
        
    def select_vertex_group(self,ob,group_name):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        num_selected_verts = 0
        for i,vert in enumerate(ob.data.vertices):
            try:
                ob.vertex_groups[group_name].weight(i)
                vert.select = True
                num_selected_verts += 1
            except:
                pass
        bpy.ops.object.mode_set(mode='EDIT')
        return num_selected_verts
        
    def merge_selected_objects(self,context):       
        objects = list(context.selected_objects)
        dupli_objects = []
        ### deselect objects
        for ob in objects:
            ob.select = False

        for i,ob in enumerate(objects):
            if ob.type == 'MESH':
                dupli_ob = ob.copy()
                context.scene.objects.link(dupli_ob)
                dupli_me = dupli_ob.data.copy()
                dupli_ob.data = dupli_me
                
                dupli_objects.append(dupli_ob)
                for group in dupli_ob.vertex_groups:
                    dupli_ob.vertex_groups.remove(group)
                v_group = dupli_ob.vertex_groups.new(name=ob.name)
                v_group.add(range(len(dupli_ob.data.vertices)),1,"REPLACE")  
            
        ### select all the new objects, and make the first one active, so we can do a join
        for ob in dupli_objects:
            if ob.type == 'MESH':
                ob.select = True
        self.multi_object = context.scene.objects.active = dupli_objects[0]
        ### copy the mesh, because we will join into that mesh 
        self.multi_object.data = self.multi_object.data.copy()
        bpy.ops.object.join()
        self.multi_object.name = "Multi_UV_Object"
          
    
    def modal(self, context, event):
        if (event.type in ['TAB'] and not event.ctrl and not event.shift and not event.oskey) or self.multi_object.mode == "OBJECT":
            self.report({'INFO'}, "Multi Object UV Editing done.")
            self.leave_editing_mode(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        ### leave local view, prevents blender to crash when joining objects
        if context.area.spaces.active.local_view != None:
            override = bpy.context.copy()
            override["area"] = context.area
            bpy.ops.view3d.localview(override)
        
        ### reset variables
        self.multi_object = None
        context.window_manager.modal_handler_add(self)
        
        ### store active and selected objects
        self.initial_objects = context.selected_objects
        self.initial_objects_hide_render = [obj.hide_render for obj in self.initial_objects]
        self.active_object = context.scene.objects.active
       
        ### make merged copy of all selected objects, that we can edit
        self.merge_selected_objects(context)
        self.multi_object.hide_render = False
        self.multi_object.hide = False
        
        ### hide the initial objects
        for obj in self.initial_objects:
            if obj.type == 'MESH':
                obj.hide = True
                obj.hide_render = True
            
        ###switch to edit mode
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='SELECT')
        if len(self.multi_object.data.uv_textures) > 0:
            bpy.ops.uv.select_all(action='SELECT')

        return {'RUNNING_MODAL'}

def add_object_tools(self,context):
    if len(get_selected_mesh_objects(context)) > 1:
        self.layout.operator_context = "INVOKE_DEFAULT"
        self.layout.separator()
        self.layout.label("UV Tools:")
        self.layout.operator("object.multi_object_uv_edit",text="Multi Object UV Editing",icon="IMAGE_RGB")

def add_object_specials(self,context):
    if len(get_selected_mesh_objects(context)) > 1:
        self.layout.operator_context = "INVOKE_DEFAULT"
        self.layout.operator("object.multi_object_uv_edit",text="Multi Object UV Editing",icon="IMAGE_RGB")  

def register():
    bpy.types.VIEW3D_PT_tools_object.append(add_object_tools)
    bpy.types.VIEW3D_MT_object_specials.append(add_object_specials)
    bpy.utils.register_class(MultiObjectUVEdit)


def unregister():
    bpy.types.VIEW3D_PT_tools_object.remove(add_object_tools)
    bpy.types.VIEW3D_MT_object_specials.remove(add_object_specials)
    bpy.utils.unregister_class(MultiObjectUVEdit)


if __name__ == "__main__":
    register()
