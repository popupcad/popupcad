# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes and CONTRIBUTORS
Email: danaukes<at>asu.edu.
Please see LICENSE for full license.
"""
import popupcad
import numpy
import shapely.geometry as sg
import popupcad
from popupcad.filetypes.laminate import Laminate


def cleanup3(ls1, value, res):
    ls2 = ls1.buffer(-value, resolution=res)
    ls3 = ls2.buffer(2 * value, resolution=res)
    ls4 = ls1.intersection(ls3)

    ls5 = ls1.buffer(value * 10, resolution=res)
    ls6 = ls5.difference(ls1)
    ls7 = ls6.buffer(-value, resolution=res)
    ls8 = ls7.buffer(2 * value, resolution=res)
    ls9 = ls6.intersection(ls8)
    ls9_1 = ls5.difference(ls9)
    ls10 = ls4.symmetric_difference(ls9_1)
    ls11 = ls1.symmetric_difference(ls10)
    return ls11


def cross_section(layerdef, sketch, parent, scale_value):
    from popupcad.filetypes.laminate import Laminate
    from popupcad.filetypes.genericshapes import GenericLine
    import shapely.affinity as aff
    import popupcad.algorithms.points as points
    import shapely.geometry as sg
    import numpy

    laminate = Laminate(layerdef)
    for item in sketch.operationgeometry:
        if isinstance(item, GenericLine):
            line = item
            b = line.exteriorpoints(scaling = popupcad.csg_processing_scaling)[0]
            c = numpy.array(b) + numpy.array([1, 0])
            a = points.calctransformfrom2lines(
                line.exteriorpoints(scaling = popupcad.csg_processing_scaling), [
                    b, c.tolist()], scale_x=1, scale_y=1)
            sketch_csg = sketch.output_csg()

            for layer in layerdef.layers:
                laminate.replacelayergeoms(layer, sketch_csg)
            result = parent.intersection(laminate)
            laminate2 = Laminate(layerdef)
            for ii, layerid in enumerate(layerdef.layers):
                yshift = layerdef.z_values[layerid] * popupcad.csg_processing_scaling * scale_value
                layer = result.layer_sequence[layerid]
                thickness = layerid.thickness * popupcad.csg_processing_scaling * scale_value
                newgeoms = [item for item in layer.geoms]
                newgeoms = [aff.affine_transform(item, a) for item in newgeoms]
                newgeoms2 = []
                for geom in newgeoms:
                    newgeom = sg.box(geom.coords[0][0],
                                     geom.coords[0][1],
                                     geom.coords[-1][0],
                                     geom.coords[-1][1] + thickness)
                    newgeoms2.append(newgeom)
                newgeoms = newgeoms2
                newgeoms = [aff.translate(item,yoff=yshift) for item in newgeoms]
                newgeoms = popupcad.algorithms.csg_shapely.condition_shapely_entities(*newgeoms)
                laminate2[ii] = newgeoms
            return laminate2

    return laminate

def transform_csg(layerdef_from,layerdef_to,inshift,outshift,step,geom_from,geoms_to,csg_laminate,scale_x,scale_y):
    from popupcad.filetypes.laminate import Laminate
    import shapely.affinity as aff
    from popupcad.algorithms.points import calctransformfrom2lines

    lsout = Laminate(layerdef_to)

    for layer_from,layer_to in zip(layerdef_from.layers[::step][inshift:], layerdef_to.layers[outshift:]):
        newgeoms = []
        for geom in geoms_to:
            for designgeom in csg_laminate.layer_sequence[layer_from].geoms:
                try:
                    from_line = geom_from.exteriorpoints(scaling = popupcad.csg_processing_scaling)
                    to_line = geom.exteriorpoints(scaling = popupcad.csg_processing_scaling)
                    transform = calctransformfrom2lines(from_line,to_line,scale_x=scale_x,scale_y=scale_y)
                    transformed_geom = aff.affine_transform(designgeom,transform)
                    newgeoms.append(transformed_geom)
                except IndexError:
                    pass
        result1 = popupcad.algorithms.csg_shapely.unary_union_safe(newgeoms)
        results2 = popupcad.algorithms.csg_shapely.condition_shapely_entities(result1)
        lsout.replacelayergeoms(layer_to, results2)

    return lsout

def shift_flip_rotate(ls1, shift, flip, rotate):
    from popupcad.filetypes.laminate import Laminate
    lsout = Laminate(ls1.layerdef)
    layers = ls1.layerdef.layers
    step = 1

    if flip:
        step = -1

    if rotate:
        for layerout, layerin in zip(
                layers[shift:] + layers[:shift], layers[::step]):
            lsout.replacelayergeoms(
                layerout,
                ls1.layer_sequence[layerin].geoms)

    else:
        if shift > 0:
            outshift = shift
            inshift = 0
        elif shift < 0:
            outshift = 0
            inshift = -shift
        else:
            outshift = 0
            inshift = 0
        for layerout, layerin in zip(layers[outshift:], layers[::step][inshift:]):
            lsout.replacelayergeoms(layerout,ls1.layer_sequence[layerin].geoms)
    return lsout


def sketch_operation(sketch, layerdef, layers):
    from popupcad.filetypes.laminate import Laminate
    operationgeom = sketch.output_csg()
    laminate = Laminate(layerdef)
    for layer in layers:
        laminate.replacelayergeoms(layer, operationgeom)
    return laminate


def find_rigid(generic, layerdef):
    
    csg1 = generic.to_csg()
    laminate_results = []    

    for ii,layer in enumerate(layerdef.layers):
        if layer.is_rigid:
            rigid_layer_csg = csg1.layer_sequence[layer]

            laminate_result = Laminate(layerdef)
            laminate_result.replacelayergeoms(layer,rigid_layer_csg.geoms)

            lower_layers = layerdef.layers[ii::-1]
            upper_layers = layerdef.layers[ii:]


            for list1 in [lower_layers,upper_layers]:
                a = list1[:-1]
                b = list1[1:]
                c = zip(a,b)
                for aa,bb in c:
                    if aa.is_adhesive or bb.is_adhesive:
                        if bb.is_rigid:
                            break
                        csga = laminate_result.layer_sequence[aa]
                        csgb = csg1.layer_sequence[bb]
                        layer_result = csga.intersection(csgb)
                        laminate_result.replacelayergeoms(bb,layer_result.geoms)
                    else:
                        break
                        
            laminate_results.append(laminate_result)

    laminate_results = [item for item in laminate_results if not item.isEmpty()]
    result = Laminate.unaryoperation(laminate_results,'union')
    return result

def remove_holes_from_rigid(laminate):
    generic_holes_removed = laminate.copy()
    for layer in generic_holes_removed.layers():
        if layer.is_rigid:
            for geom in generic_holes_removed.geoms[layer]:
                geom.interiors = []
    return generic_holes_removed          

