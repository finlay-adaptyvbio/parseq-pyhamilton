from pyhamilton import (
    HamiltonInterface,
    Plate96,
    Tip96,
    Reservoir300,
    EppiCarrier24,
)

import commands as cmd
import deck as dk

layout_path = "C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\adaptyv-pyhamilton\\layouts\\purification.lay"

deck = dk.get_deck(layout_path)

l = [dk.index_to_string_384(i) for i in range(384)]

if __name__ == "__main__":
    test_plate = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
    test_frame = dk.frame_384(
        test_plate,
        l,
    )
    print(test_frame._frame())
    print(test_frame.get_tips_384mph(4, 4))
    print(test_frame._frame())

    print(test_frame._frame())
    print(test_frame.get_tips_384mph(5, 5))
    print(test_frame._frame())
