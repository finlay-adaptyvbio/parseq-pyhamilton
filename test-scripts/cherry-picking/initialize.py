import os
from pyhamilton import (HamiltonInterface, INITIALIZE, LayoutManager)

layout_filename = 'Py_Adaptyv_v1.5.lay'

layfile = os.path.abspath(os.path.join(r"C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\layouts", layout_filename))
lmgr = LayoutManager(layfile)

if __name__ == '__main__':

    with HamiltonInterface() as hammy:
        hammy.wait_on_response(hammy.send_command(INITIALIZE))
        print('Initialized!')