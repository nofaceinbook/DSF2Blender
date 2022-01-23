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
        
