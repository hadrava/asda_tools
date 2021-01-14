#!/usr/bin/env python3

import sys
from asdapar2json import ASDAParser

if __name__ == "__main__":
    if len(sys.argv) == 3:
        filename_in = sys.argv[1]
        filename_out = sys.argv[2]

        writer = ASDAParser()
        writer.from_json_file(filename_in)
        writer.reconstruct()
        writer.write_reconstruction(filename_out)
    else:
        print("Usage: python3 {} input_file.json output_file.par".format(sys.argv[0]), file=sys.stderr)
