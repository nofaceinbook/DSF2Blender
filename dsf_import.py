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

#### IMPORTANT: Requires xplnedsf2.py from https://github.com/nofaceinbook/muxp in your # ******************************************************************************
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
dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zOrtho4XP_-08-015/Earth nav data/-10-020/-08-015.dsf'
xp_path = 'X:/X-Plane/steamapps/common/X-Plane 11'  # Could in future be retrieved from dsf file


def read_ter_file(terpath, xppath, dsfpath):
    """
    Reads X-Plane terrain file (.ter) in terpath and returns values as dictionary.
    In case of errors the dict contains key ERROR with value containing description of error.
    To read default terrains the path for X-Plane (xppath) is needed.
    dsfpath is the path of the dsf file that contains the terrain definition. Needed to read dsf specific terrain.
    """
    ter = dict()

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


print("------------ Starting to use DSF ------------------")

dsf = XPLNEDSF()
dsf.read(dsf_file)

grid_west = int(dsf.Properties["sim/west"])
grid_south = int(dsf.Properties["sim/south"])
print("Importing Mesh and setting west={} and south={} to origin.".format(grid_west, grid_south))

#sP = 0  # selected Pool to be imported
for sP in range(1):  ######range(len(dsf.V)):
    verts = []
    edges = []  # will not be filled as Blender takes in case of empty edges the edges from the faces
    faces = []
    normals = []
    uvs = []
    coords = dict()  # existing coordinates per object as key and index of them in verts as value
    materials = dict()  # containing for each material = terrain the index
    matIndexPerTria = []  # list of material index for each tria of mesh

    for p in dsf.Patches:
        if p.flag > 1:  # for the moment only import pyhsical trias of mesh (no OVERLAY)
            continue
        trias = p.triangles()
        terrain = dsf.DefTerrains[p.defIndex]
        if terrain in materials:
            mat = materials[terrain]
        else:
            mat = len(materials)
            materials[terrain] = mat
        for t in trias:
            ti = []  # index list of vertices of tria that will be added to faces
            tuvs = []  # uvs for that triangle
            for v in t:  # this is now index to Pool and to vertex in Pool
                #### TBD: Scale to Marcartor in order to have same east/west and north/south dimension #####
                vx = round((dsf.V[v[0]][v[1]][0] - grid_west) * 1000, 3)
                vy = round((dsf.V[v[0]][v[1]][1] - grid_south) * 1000, 3)
                vz = dsf.getVertexElevation(dsf.V[v[0]][v[1]][0], dsf.V[v[0]][v[1]][1], dsf.V[v[0]][v[1]][2])
                vz = round(vz / 100, 3) ### TBD: Make stretching of height configureable
                if (vx, vy) in coords:
                    vi = coords[(vx, vy)]
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
                if len(dsf.V[v[0]][v[1]]) > 5:  # do we have uvs
                    tuvs.insert(0, (dsf.V[v[0]][v[1]][5], dsf.V[v[0]][v[1]][6]))  # uvs are defined for every vertex of every face / loop
                else: 
                    tuvs.insert(0, (vx/100, vy/100))  #By this definition uvs exced [0;1] range, but should lead to scale 10 times the size
            faces.append(ti)
            uvs.extend(tuvs)  # uvs added with correct order because of tria different winding
            matIndexPerTria.append(mat)    


    mesh_name = "Patch." + str(sP)
    mesh = bpy.data.meshes.new(mesh_name)  # add the new mesh

    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("Collection")
    col.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    mesh.from_pydata(verts, edges, faces)
    mesh.use_auto_smooth = True  # needed to make use of imported normals split
    #mesh.normals_split_custom_set([(0, 0, 0) for l in mesh.loops])
    mesh.normals_split_custom_set_from_vertices(normals)  # set imported normals as custom split vertex normals
    
    for matName in materials:
        m = bpy.data.materials.new(matName)
        if matName != 'terrain_Water':  ### TBD: Define special texture for water
            ter = read_ter_file(matName, xp_path, dsf_file) #### TBD: Handle error in ter
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
            
        bpy.context.object.data.materials.append(m)
    
    for i, tria in enumerate(bpy.context.object.data.polygons):  #### Use obj instead of context ??
        tria.material_index = matIndexPerTria[i]
        
    print("{} materials added for {} triangles!".format(len(materials), len(matIndexPerTria)))

    print("Now adding {} uv coordinates ....".format(len(uvs)))
    new_uv = bpy.context.active_object.data.uv_layers.new(name='NewUV')  #### Use obj instead of context ??
    for loop in bpy.context.active_object.data.loops:
        new_uv.data[loop.index].uv = uvs[loop.index]
    #### TBD: Add to material name "PRJ" if it is projected without actually having uvs, would help export later not to read ter file ##

        Blender python/lib directory ####
####            For the moment the dsf file must be unzipped or you install PLYZMA in Blender Python ######
####            Only default XP Mesh can currently be displayed for rendering ######
####            UV-Maps and mesh overlays (smoothing terrain borders) are currently not read ######
#####           X-PLANE Normals are currently not imoportant in order to use them for setting Blender split vertex normals ###

################ ENTER BELOW your X-Plane default unzipped DSF File and path to X-Plane #################################
dsf_file = 'X:/X-Plane/steamapps/common/X-Plane 11/Custom Scenery/zzzz_MUXP_default_mesh_updates/Earth nav data/+10-070/+10-067.dsf'
xp_path = 'X:/X-Plane/steamapps/common/X-Plane 11'  # Could in future be retrieved from dsf file



def read_ter_file(terpath, xppath, dsfpath):
    """
    Reads X-Plane terrain file (.ter) in terpath and returns values as dictionary.
    In case of errors the dict contains key ERROR with value containing description of error.
    To read default terrains the path for X-Plane (xppath) is needed.
    dsfpath is the path of the dsf file that contains the terrain definition. Needed to read dsf specific terrain.
    """
    ter = dict()

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


print("------------ Starting to use DSF ------------------")

dsf = XPLNEDSF()
dsf.read(dsf_file)

grid_west = int(dsf.Properties["sim/west"])
grid_south = int(dsf.Properties["sim/south"])
print("Importing Mesh and setting west={} and south={} to origin.".format(grid_west, grid_south))

#sP = 0  # selected Pool to be imported
for sP in range(1):  ######range(len(dsf.V)):
    verts = []
    edges = []  # will not be filled as Blender takes in case of empty edges the edges from the faces
    faces = []
    coords = dict()  # existing coordinates per object as key and index of them in verts as value
    materials = dict()  # containing for each material = terrain the index
    matIndexPerTria = []  # list of material index for each tria of mesh

    for p in dsf.Patches:
        if p.flag > 1:  # for the moment only import pyhsical trias of mesh (no OVERLAY)
            continue
        trias = p.triangles()
        terrain = dsf.DefTerrains[p.defIndex]
        if terrain in materials:
            mat = materials[terrain]
        else:
            mat = len(materials)
            materials[terrain] = mat
        for t in trias:
            ti = []  # index list of vertices of tria that will be added to faces
            for v in t:  # this is now index to Pool and to vertex in Pool
                #### TBD: Scale to Marcartor in order to have same east/west and north/south dimension #####
                vx = round((dsf.V[v[0]][v[1]][0] - grid_west) * 1000, 3)
                vy = round((dsf.V[v[0]][v[1]][1] - grid_south) * 1000, 3)
                vz = dsf.getVertexElevation(dsf.V[v[0]][v[1]][0], dsf.V[v[0]][v[1]][1], dsf.V[v[0]][v[1]][2])
                vz = round(vz / 100, 3) ### TBD: Make stretching of height configureable
                if (vx, vy) in coords:
                    vi = coords[(vx, vy)]
                else:
                    vi = len(coords)  # index in verts is the last one, as coords will now be added
                    coords[(vx, vy)] = vi 
                    verts.append([vx, vy, vz])
                ti.insert(0, vi)  # winding in Blender is just opposite as in X-Plane
            faces.append(ti)
            matIndexPerTria.append(mat)    


    mesh_name = "Patch." + str(sP)
    mesh = bpy.data.meshes.new(mesh_name)  # add the new mesh
    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("Collection")
    col.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    mesh.from_pydata(verts, edges, faces)
    
    for matName in materials:
        m = bpy.data.materials.new(matName)
        if matName != 'terrain_Water':  ### TBD: Define special texture for water
            ter = read_ter_file(matName, xp_path, dsf_file) #### TBD: Hanle error in ter
            teximagefile =  ter["BASE_TEX"][0].replace("/", "\\\\")  ### TBD: for BASE_TEX_NOWRAP #######
            print("Loading texture image: {}".format(teximagefile))
            m.use_nodes = True
            bsdf = m.node_tree.nodes["Principled BSDF"]
            texImage = m.node_tree.nodes.new('ShaderNodeTexImage')
            texImage.image = bpy.data.images.load(teximagefile)
            m.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
            bsdf.inputs[7].default_value = 0.01  # This is setting the specular intensity
            ### TBD: increase rougness
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
            
        bpy.context.object.data.materials.append(m)
    
    for i, tria in enumerate(bpy.context.object.data.polygons):
        tria.material_index = matIndexPerTria[i]
        
    print("{} materials added for {} triangles!".format(len(materials), len(matIndexPerTria)))
        
