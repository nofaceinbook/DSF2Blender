# ******************************************************************************
#
# DSF2Blender: Python script for Blender that allows import of X-Plane DSF files
#              Checked with Blender 3.0 but should work from 2.8 up
#
# For more details refer to GitHub: https://github.com/nofaceinbook/DSF2Blender
#
# WARNING: This code is still under development and may still have some errors.
#
# Copyright (C) 2022 by schmax (Max Schmidt)
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
# A PARTICULAR PURPOSE.  
# ******************************************************************************

from xplnedsf2 import *
import bpy

#### IMPORTANT: Requires xplnedsf2.py from https://github.com/nofaceinbook/muxp in your Blender python/lib directory ####
####            For the moment the dsf file must be unzipped or you install PLYZMA in Blender Python ######
####            Rendering a complete O4XP tile probabyl causes out of memory fault ###########

################ ENTER BELOW your X-Plane default unzipped DSF File and path to X-Plane #################################
dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zzzz_MUXP_default_mesh_updates/Earth nav data/+10-070/+10-067.dsf'
#dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zzzz_MUXP_default_mesh_updates/Earth nav data/+30+040/+39+046.dsf'
#dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zOrtho4XP_+50+007/Earth nav data/+50+000/+50+007.dsf'
#dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zOrtho4XP_-08-015/Earth nav data/-10-020/-08-015.dsf'
#dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zOrtho4XP_+32-017/Earth nav data/+30-020/+32-017.dsf'
xp_path = 'X:/X-Plane/steamapps/common/X-Plane 11'  # Could in future be retrieved from dsf file


def read_ter_file(terpath, xppath, dsfpath):
    """
    Reads X-Plane terrain file (.ter) in terpath and returns values as dictionary.
    In case of errors the dict contains key ERROR with value containing description of error.
    To read default terrains the path for X-Plane (xppath) is needed.
    dsfpath is the path of the dsf file that contains the terrain definition. Needed to read dsf specific terrain.
    """
    ter = dict()
    
    if terpath == 'terrain_Water':  # No terrian file for Water
        return ter
    
    if terpath.endswith('_OVL'):  #### TBD: Can probably be removed as function is called with terrain name now
        overlay = True
        terpath = terpath[:-4]  # remove _OVL now from terrain name

    ### TBD: handle different path delimeters in given pathes like \ by replacing them ? ####
    if terpath.startswith("lib/g10"):  # global XP 10 terrain definition
        #### TBD: Build path correct for every file system ###
        filename = xppath + "/Resources/default scenery/1000 world terrain" + terpath[7:]  # remove lib/g10
    elif terpath.startswith("terrain/"):  # local dsf terrain definition
        filename = dsfpath[:dsfpath.rfind("Earth nav data")] + terpath  # remove part for dsf location
        ### TBD: Error check that terrain file exists
    else:
        ter["ERROR"] = "Unknown Terrain definition: " + terpath
        return ter
        ##### TBD: Build filename for local .ter files starting with ../ using dsfpath #######

    try:
        with open(filename, encoding="utf8") as f:
            for line in f:  ### TBD: Check that first three lines contain A  800  TERRAIN   #####
                values = line.split()
                #print(values)
                if len(values) > 0:  # skip empty line
                    key = values.pop(0)
                    if len(values) > 0 and values[0].startswith("../"):  # replace relative path with full path
                        filepath = filename[:filename.rfind("/")]  # get just path without name of file in path
                        values[0] = filepath[:filepath.rfind("/") + 1] + values[0][3:]
                        #print(filename, values[0])
                        ### TBD: Handle ERROR when '/' is not found; when other delimiters are used
                    ter[key] = values
                ### TBD: in case of multiple keys in files append new values to existing key
    except IOError:
        ter["ERROR"] = "Error reading terrain file: " + filename

    return ter


def add_material(matName, ter, bpy):
    m = bpy.data.materials.new(matName)
    if matName != 'terrain_Water':  
        if "BASE_TEX" in ter:
            teximagefile =  ter["BASE_TEX"][0].replace("/", "\\\\")  
        elif "BASE_TEX_NOWRAP" in ter:
            teximagefile =  ter["BASE_TEX_NOWRAP"][0].replace("/", "\\\\") 
        print("Loading texture image: {}".format(teximagefile))
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        texImage = m.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.image = bpy.data.images.load(teximagefile)
        m.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
        bsdf.inputs[7].default_value = 0.01  # This is setting the specular intensity
        ### TBD: increase rougness
        if matName.endswith( "_OVL"):  # add border texture for overlay
            if "BORDER_TEX" in ter:
                borderimagefile = ter["BORDER_TEX"][0].replace("/", "\\\\")
                borderImage = m.node_tree.nodes.new('ShaderNodeTexImage')
                ############### TBD: Check that existing images are used - if it works as below use everywhere where image is loaded
                borderImage.image = bpy.data.images.load(borderimagefile, check_existing=True)
                borderImage.image.colorspace_settings.name = 'Non-Color'
                m.node_tree.links.new(bsdf.inputs['Alpha'], borderImage.outputs['Color'])                 
                m.blend_method = 'CLIP'
                node = m.node_tree.nodes.new('ShaderNodeUVMap')
                node.location = (-700,0)
                node.uv_map = "borderUV"
                m.node_tree.links.new(node.outputs[0], borderImage.inputs[0])  # add link from new uv map to image texture
            else:
                print("WARNING: No texture file found for this terrain overlay/material!\n")
            
    else:  ### TBD: don't double everything below
        teximagefile = xp_path + "/Resources/bitmaps/world/water/any.png"
        teximagefile.replace("/", "\\\\")
        print("Loading texture image: {}".format(teximagefile))
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        texImage = m.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.image = bpy.data.images.load(teximagefile)
        m.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
        ### TBD: Change specular, roughness, transmission to good values for water
    return m
            



print("------------ Starting to use DSF ------------------")

dsf = XPLNEDSF()
dsf.read(dsf_file)

grid_west = int(dsf.Properties["sim/west"])
grid_south = int(dsf.Properties["sim/south"])
print("Importing Mesh and setting west={} and south={} to origin.".format(grid_west, grid_south))


    
verts = []
edges = []  # will not be filled as Blender takes in case of empty edges the edges from the faces
normals = []  # normals stored per vertex
faces = [[]]
uvs = [[]]
uvs2 = [[]] # second uv coordinates given for borders in case of non projected mesh
coords = dict()  # existing coordinates per object as key and index of them in verts as value
tria_layer = dict()  # returning for a tria of vertex index the current layer (how many are above eahc ohter)
materials = dict()  # containing for each material = terrain the index
matIndexPerTria = [[]] # list of material index for each tria of mesh
used_materials = [[]]  # list containing for each layer the used materials
terrain_details = dict()  # containing per terrain index the details of .ter-file in dict

for p in dsf.Patches:
    trias = p.triangles()
    terrain = dsf.DefTerrains[p.defIndex]
    if not p.defIndex in terrain_details:
        terrain_details[p.defIndex] = read_ter_file(terrain, xp_path, dsf_file)
        if "ERROR" in terrain_details[p.defIndex]:
            print(terrain_details[p.defIndex]["ERROR"])
    if "PROJECTED" in terrain_details[p.defIndex] or (terrain == "terrain_Water" and len(dsf.V[trias[0][0][0]][trias[0][0][1]]) <= 5):
        # if water is projected depends if uv coordinates are given or not, taken from ferst vertex in first tria
        ##### TBD: Can cause issue in case patch is empty
        projected_uv = True
    else:
        projected_uv = False
    if p.flag > 1:  # this is an overlay
        terrain += "_OVL"
    #### TBD: INCLDUDE NEAR/FAR VALUES FOR PATCH TO MATERIAL #####
    if terrain in materials:
        m = materials[terrain]  ######### TBD: this with used_materials seems not efficient ######
    else:
        m = add_material(terrain, terrain_details[p.defIndex], bpy)  # add material to Blender materials
        materials[terrain] = m
    for t in trias:
        ti = []  # index list of vertices of tria that will be added to faces
        tuvs = []  # uvs for that triangle
        tuvs2 = []  # 2nd uves for triangle e.g. for borders if existent
        for v in t:  # this is now index to Pool and to vertex in Pool
            #### TBD: Scale to Marcartor in order to have same east/west and north/south dimension #####
            vx = round((dsf.V[v[0]][v[1]][0] - grid_west) * 1000, 3)
            vy = round((dsf.V[v[0]][v[1]][1] - grid_south) * 1000, 3)
            vz = dsf.getVertexElevation(dsf.V[v[0]][v[1]][0], dsf.V[v[0]][v[1]][1], dsf.V[v[0]][v[1]][2])
            vz = round(vz / 100, 3)  ### TBD: Make stretching of height configureable
            if (vx, vy) in coords:
                vi = coords[(vx, vy)]
                #### TBD: check if new normal is equal to existing one ###############
            else:
                vi = len(coords)  # index in verts is the last one, as coords will now be added
                coords[(vx, vy)] = vi 
                verts.append([vx, vy, vz])
                nx = round(dsf.V[v[0]][v[1]][3], 4)  #### TBD: Rounding and if below can be removed; just checking if existent
                ny = round(dsf.V[v[0]][v[1]][4], 4)
                normals.append([nx, ny, round(sqrt(1 - nx*nx - ny*ny), 4)])
                #if normals[-1] != [0.0, 0.0, 1.0]:
                #    print(normals[-1])
            ti.insert(0, vi)  # winding in Blender is just opposite as in X-Plane
            if len(dsf.V[v[0]][v[1]]) == 7:  # in case of projection we need first uvs do by own unwrapping and use the others as second e.g. for border
                if projected_uv and p.flag == 1:  # for projected physical mesh; for overlay we would need second uvs for border
                    tuvs.insert(0, (dsf.V[v[0]][v[1]][5], dsf.V[v[0]][v[1]][6]))
                    tuvs2.insert(0, (vx/100, vy/100))  # add this uv, even if not needed in order to get full uv-mesh for that layer
                else:  # should only be the case if projected and we have overlay to get uv-map for border
                    tuvs.insert(0, (vx/100, vy/100))  #By this definition uvs exced [0;1] range, but should lead to scale 10 times the size
                    tuvs2.insert(0, (dsf.V[v[0]][v[1]][5], dsf.V[v[0]][v[1]][6]))  # uvs are defined for every vertex of every face / loop
            elif len(dsf.V[v[0]][v[1]]) == 9: # first uvs for mesh 2nd for border
                tuvs.insert(0, (dsf.V[v[0]][v[1]][5], dsf.V[v[0]][v[1]][6]))  # uvs are defined for every vertex of every face / loop
                tuvs2.insert(0, (dsf.V[v[0]][v[1]][7], dsf.V[v[0]][v[1]][8]))  # uvs are defined for every vertex of every face / loop                    
            else: # we don't have uvs so we unwrap our own ones
                tuvs.insert(0, (vx/100, vy/100))  # By this definition uvs exced [0;1] range, but should lead to scale 10 times the size
                tuvs2.insert(0, (vx/100, vy/100))  # Add uvs even if not needed for that tria but to have full uvs for that layer 
        smallest_index = min(ti)  # make sure that smallest index is first in the list, but keep winding of tria
        if smallest_index == ti[1]:
            ti = (ti[1], ti[2], ti[0])
        elif smallest_index == ti[2]:
            ti = (ti[2], ti[0], ti[1])
        else:
            ti = (ti[0], ti[1], ti[2])
        if ti in tria_layer:  # this tria is already existing
            tria_layer[ti] += 1  # this new tria has to be pot on next layer
            layer = tria_layer[ti]
        else:
            tria_layer[ti] = 0  # this is first tria which is layer 0 (base mesh)
            layer = 0    
        if layer >= len(faces):  # We need addtional layer so extend lists
            faces.append([])
            uvs.append([])
            uvs2.append([])
            matIndexPerTria.append([]) 
            used_materials.append([])
        faces[layer].append(ti)
        uvs[layer].extend(tuvs)  # uvs added with correct order because of tria different winding
        if tuvs2 != []:
            uvs2[layer].extend(tuvs2)
        ########### TBD: used materials defined as dict per layer for better performance ###############
        #print(m, used_materials[layer])
        if m not in used_materials[layer]:
            mat = len(used_materials[layer])
            used_materials[layer].append(m)
        else:
            mat = used_materials[layer].index(m)
        matIndexPerTria[layer].append(mat)    

for layer in range(len(faces)):
    if layer == 0:
        mesh_name = "Basemesh"
    else:
        mesh_name = "Overlay_" + str(layer)
        ### TBD Group overlays in own group
    mesh = bpy.data.meshes.new(mesh_name)  # add the new mesh

    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("Collection")
    col.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

	##### Delete loose vertices: bpy.ops.mesh.delete_loose()
	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.delete_loose()
	bpy.ops.object.mode_set(mode='OBJECT')


    mesh.from_pydata(verts, edges, faces[layer])
    mesh.use_auto_smooth = True  # needed to make use of imported normals split
    #mesh.normals_split_custom_set([(0, 0, 0) for l in mesh.loops])
    mesh.normals_split_custom_set_from_vertices(normals)  # set imported normals as custom split vertex normals    

    # ADDING MATERIALS PER LAYER
    for m in used_materials[layer]:
        bpy.context.object.data.materials.append(m)

    for i, tria in enumerate(bpy.context.object.data.polygons):  #### Use obj instead of context ??
        tria.material_index = matIndexPerTria[layer][i]


    new_uv = bpy.context.active_object.data.uv_layers.new(name='baseUV')  #### Use obj instead of context ??
    for loop in bpy.context.active_object.data.loops:
        new_uv.data[loop.index].uv = uvs[layer][loop.index]
    bpy.context.object.data.uv_layers["baseUV"].active_render = True


    ######## ADDING BORDER UVS ###########
    if layer > 0:  # we haver overlay
        border_uv = bpy.context.active_object.data.uv_layers.new(name='borderUV')  #### Use obj instead of context ??
        for loop in bpy.context.active_object.data.loops:
            border_uv.data[loop.index].uv = uvs2[layer][loop.index]

    ### Move overlays along z-axis
    obj.location.z += layer

    #### TBD: Add to material name "PRJ" if it is projected without actually having uvs, would help export later not to read ter file ##

        
