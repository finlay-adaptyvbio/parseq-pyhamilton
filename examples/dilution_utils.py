# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 19:34:32 2020

@author: stefa
"""


#!python3

import sys, os, time, logging, importlib
from threading import Thread



import pyhamilton
from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate24, Plate96, Tip96,
    INITIALIZE, PICKUP, EJECT, ASPIRATE, DISPENSE, ISWAP_GET, ISWAP_PLACE, HEPA,
    WASH96_EMPTY, PICKUP96, EJECT96, ASPIRATE96, DISPENSE96,
    oemerr, PositionError)

def resource_list_with_prefix(layout_manager, prefix, res_class, num_ress, order_key=None, reverse=False):
    def name_from_line(line):
        field = LayoutManager.layline_objid(line)
        if field:
            return field
        return LayoutManager.layline_first_field(line)
    layline_test = lambda line: LayoutManager.field_starts_with(name_from_line(line), prefix)
    res_type = ResourceType(res_class, layline_test, name_from_line)
    res_list = [layout_manager.assign_unused_resource(res_type, order_key=order_key, reverse=reverse) for _ in range(num_ress)]
    return res_list

def labware_pos_str(labware, idx):
    return labware.layout_name() + ', ' + labware.position_id(idx)

def compound_pos_str(pos_tuples):
    present_pos_tups = [pt for pt in pos_tuples if pt is not None]
    return ';'.join((labware_pos_str(labware, idx) for labware, idx in present_pos_tups))

def compound_pos_str_96(labware96):
    return ';'.join((labware_pos_str(labware96, idx) for idx in range(96)))
