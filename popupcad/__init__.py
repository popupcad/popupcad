# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes and CONTRIBUTORS
Email: danaukes<at>asu.edu.
Please see LICENSE for full license.
"""
#from __future__ import absolute_import

import sys

from shapely import speedups

# necessary for homebrewed libgeos which does not work with speedups for some reason.
if sys.platform != 'darwin':
    if speedups.available:
        speedups.enable()

from .global_settings import *

from . import algorithms
from . import filetypes
from . import geometry
from . import graphics2d
from . import graphics3d
from . import guis
from . import manufacturing
from . import materials
from . import widgets

import yaml
try:
    with open(user_materials_filename) as f:
        user_materials = yaml.load(f,Loader=yaml.FullLoader)
except FileNotFoundError:
    pass

try:
    with open(custom_settings_filename) as f:
        custom_settings = yaml.load(f,Loader=yaml.FullLoader)
            
    popupcad_module=sys.modules[__name__]
    for key in custom_settings:
        if hasattr(popupcad_module,key):
            setattr(popupcad_module,key,custom_settings[key])
except FileNotFoundError:
    pass

##load external modules
#
#import ezdxf
#import numpy
#import pypoly2tri
#import pyqtgraph
#import scipy.optimize
#import scipy.spatial
#import shapely
#import sympy
#import yaml

#import idealab_tools.virtual_structure
#commands = idealab_tools.virtual_structure.load_commands(os.path.normpath(os.path.join(supportfiledir,'virtual_structure.yaml')))
#idealab_tools.virtual_structure.run_commands(commands)