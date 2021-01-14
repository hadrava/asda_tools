#!/usr/bin/env python3

import sys
import struct
import json
import re


class ASDAParseError(Exception):
    pass

class ASDAReconstructError(Exception):
    pass


class ASDAParser(object):
    # TODO begin obsolete
    #BINARY_LEN = 39248
    BINARY_LEN = 39248 + (8 + 48) * 2
    VERSION_OFFSET = 0x10
    #PARAM_BLOCK_LENGTHS =  [64, 99, 95, 14, 25, 100, 100, 28]
    PARAM_BLOCK_LENGTHS =  [64, 99, 95 + 2, 14, 25, 100, 100, 28]
    PARAM_OFFSET = 0x1f0
    MAX_MIN_DEFAULT_OFFSET = 0x1270
    TRAILER_OFFSET = 0x7550
    # TODO end obsolete

    BINARY_CONSTANTS = {
            # XXX We have no idea, what it means
            # 0x6730     --> FileCode?
            # 0x00001005 --> FileVer?
            # 0x00030004 --> DEV1?
            # 0x0000     --> DEV2?
            "magic":                   [0x30, 0x67, 0x05, 0x10, 0x00, 0x00, 0x04, 0x00, 0x03, 0x00, 0x00, 0x00],
            "before_table":            [0x00] * 2 + [0x80] + [0x00] * 3 + [0x07] + [0x00] * 9 +
                                       [0x00] * 2 + [0x80] + [0x00] * 13,
            "0001_firmware_version_1": [0x01, 0x00, 0x00, 0x00, 0xf4, 0x01, 0x00, 0x00],
            "0001_firmware_version_2": [0x01, 0x00, 0x00, 0x00],
            "0002_unknown_1":          [0x08] +[0x00] * 15 +
                                       [0x00, 0x00, 0x40, 0x00, 0x01, 0x00, 0x63, 0x00, 0x02, 0x00],
            "0002_unknown_2":          [0x03, 0x00, 0x0e, 0x00] +
                                       [0x04, 0x00, 0x19, 0x00, 0x05, 0x00, 0x64, 0x00, 0x06, 0x00, 0x64, 0x00, 0x07, 0x00, 0x1c, 0x00] +
                                       [0x00] * 16,
            "0006_unit_param_unknown": [0x00] * 3 + [0x20] + [0x00] * 5 + [0x20] + [0x00] * 4 +
                                       [0x00] * 16,
            }
    ASDASOFT_VERSION_STRING_LEN = 0x70

    def __init__(self):
        self.binary = None
        self.binary_reconstruct = None
        self.data = None

    def load_param_file(self, filename):
        with open(filename, "rb") as f:
            byte = f.read()
            self.binary = b''
            while byte:
                self.binary += byte
                byte = f.read(1)

    def write_reconstruction(self, filename):
        with open(filename, "wb") as f:
            byte = f.write(self.binary_reconstruct)

    def assert_reconstruction_correct(self):
        if len(self.binary) != len(self.binary_reconstruct):
            raise ASDAParseError("Reconstruction is different: wrong length: expected {}, got {}".format(len(self.binary), len(self.binary_reconstruct)))
        for position, (orig, our) in enumerate(zip(self.binary, self.binary_reconstruct)):
            if orig != our:
                raise ASDAParseError("Reconstruction is different at position 0x{:04X}: expected byte 0x{:02X}, recreated 0x{:02X}".format(position, orig, our))

    def swap_words(self, param):
        byte_str = struct.pack("<L", param)
        swapped = byte_str[2:4] + byte_str[0:2]
        return struct.unpack("<L", swapped)[0]

    def _check_equal(self, constant_name):
        constant = self.BINARY_CONSTANTS[constant_name]
        self._check_equal_array(constant)

    def _check_equal_array(self, array):
        for expected_byte in array:
            if self.binary[self.current_offset] != expected_byte:
                raise ASDAParseError("Wrong byte at position 0x{:04X}, expected byte 0x{:02X}, got 0x{:02X}".format(self.current_offset, expected_byte, self.binary[self.current_offset]))
            self.current_offset += 1

    def _load_storage_mode(self):
        value, = struct.unpack("<L", self.binary[self.current_offset : self.current_offset + 4])
        self.data["storage_mode"] = value
        if value not in [0x01, 0x03]:
            raise ASDAParseError("Unknown storage mode at position 0x{:04X}, got 0x{:04X}".format(self.current_offset, value))
        self.current_offset += 4

    def _load_asdasoft_version_string(self):
        encoded_version_string = self.binary[self.current_offset: self.current_offset + self.ASDASOFT_VERSION_STRING_LEN].split(b'\x00')[0]
        self.data["asdasoft_version_string"] = encoded_version_string.decode()
        self._check_equal_array(self._reconstruct_asdasoft_version_string_to_array())

    def _section_table_load_row(self):
        row_type, position = struct.unpack("<HL", self.binary[self.current_offset : self.current_offset + 6])
        self.current_offset += 6
        self._check_equal_array([0x00] * 10)
        self.data["section_table"].append({
            "section_type": row_type,
            "section_offset": position})

    def _load_section_table(self):
        self.data["section_table"] = []
        self._section_table_load_row()
        min_offset = min([x["section_offset"] for x in self.data["section_table"]])
        while self.current_offset < min_offset:
            self._section_table_load_row()
            min_offset = min([x["section_offset"] for x in self.data["section_table"]])

    def _load_sections(self):
        for section_number, section in enumerate(self.data["section_table"]):
            expected_end = self._load_and_check_section_header(section_number, section)

            if section["section_type"] == 0x0001:
                self._load_section_0001_firmware_version(expected_end)
            elif section["section_type"] == 0x0002:
                self._load_section_0002_unknown(expected_end)
            elif section["section_type"] == 0x0018:
                self._load_section_0018_current_params(expected_end)
            elif section["section_type"] == 0x0006:
                self._load_section_0006_max_min_default_unit_params(expected_end)
            elif section["section_type"] == 0x0007:
                self._load_section_0007_null_block(expected_end)
            elif section["section_type"] == 0x0008:
                self._load_section_0008_numbered_null_blocks(expected_end)
            else:
                raise ASDAParseError("Problem parsing section #{}: Unknown section type: 0x{:04X}".format(section_number, section["section_type"]))

            if self.current_offset != expected_end:
                raise ASDAParseError("Problem parsing section #{} (section type: 0x{:04X}): expected end = 0x{:04X}, but we finished parsing at position 0x{:04X}".format(section_number, section["section_type"], expected_end, self.current_offset))

    def _load_and_check_section_header(self, section_number, section):
        if section["section_offset"] != self.current_offset:
            raise ASDAParseError("Problem before parsing section #{} (section type: 0x{:04X}): it should start at offset 0x{:04X} (according to the section table), but we are at position 0x{:04X}".format(section_number, section["section_type"], section["section_offset"], self.current_offset))
        section_type, section_length = struct.unpack("<HL", self.binary[self.current_offset : self.current_offset + 6])
        self.current_offset += 6
        self._check_equal_array([0x00] * 10)

        if section["section_type"] != section_type:
            raise ASDAParseError("Problem parsing header of section #{}: expected section type: 0x{:04X} (according to the table), but we found type: 0x{:04X} (section offset: 0x{:04X}".format(section_number, section["section_type"], section_type, section["section_offset"]))

        expected_end = section["section_offset"] + section_length
        section["section_length"] = section_length
        return expected_end

    def _load_section_0001_firmware_version(self, expected_end):
        self._check_equal("0001_firmware_version_1")
        fw_1, fw_2 = struct.unpack("<LL", self.binary[self.current_offset : self.current_offset + 8])
        self.current_offset += 8

        self._check_equal("0001_firmware_version_2")
        sub_fw_1, sub_fw_2 = struct.unpack("<LL", self.binary[self.current_offset : self.current_offset + 8])
        self.current_offset += 8

        self._check_equal_array([0x00] * 100)

        if fw_1 != fw_2:
            raise ASDAParseError("Different firmware version in the header 0x{:04X} != 0x{:04X}".format(fw_1, fw_2))
        if sub_fw_1 != sub_fw_2:
            raise ASDAParseError("Different firmware sub_version in the header 0x{:04X} != 0x{:04X}".format(sub_fw_1, sub_fw_2))

        self.data["firmware_version"] = fw_1
        self.data["firmware_subversion"] = sub_fw_1


    def _load_section_0002_unknown(self, expected_end):
        self._check_equal("0002_unknown_1")
        unknown_1, = struct.unpack("<H", self.binary[self.current_offset : self.current_offset + 2])
        self.current_offset += 2
        self.data["0002_unknown_x"] = unknown_1
        self._check_equal("0002_unknown_2")

    def _load_one_current_param(self):
        block_id, param_id, value, = struct.unpack("<HHL", self.binary[self.current_offset : self.current_offset + 8])
        self.current_offset += 8
        is_end = block_id == 0 and param_id == 0 and value == 0
        return is_end, block_id, param_id, value

    def _load_section_0018_current_params(self, expected_end):
        self.data["params"] = {}
        is_end, block_id, param_id, value = self._load_one_current_param()
        while not is_end:
            key_name = "P{}-{:02d}".format(block_id, param_id)
            self.data["params"][key_name] = {
                    "current": value
                    }
            is_end, block_id, param_id, value = self._load_one_current_param()

    def _load_one_max_min_default_unit_param(self):
        block_id, param_id, max_value, min_value, default_value, = struct.unpack("<HHLLL", self.binary[self.current_offset : self.current_offset + 16])
        self.current_offset += 16
        max_value = self.swap_words(max_value)
        min_value = self.swap_words(min_value)
        default_value = self.swap_words(default_value)
        unit = 0

        is_end = block_id == 0 and param_id == 0 and max_value == 0 and min_value == 0 and default_value == 0
        if is_end:
            return is_end, block_id, param_id, max_value, min_value, default_value, unit

        unit, = struct.unpack("<H", self.binary[self.current_offset : self.current_offset + 2])
        self.current_offset += 2
        self._check_equal("0006_unit_param_unknown")
        return is_end, block_id, param_id, max_value, min_value, default_value, unit

    def _load_section_0006_max_min_default_unit_params(self, expected_end):
        is_end, block_id, param_id, max_value, min_value, default_value, unit = self._load_one_max_min_default_unit_param()
        while not is_end:
            key_name = "P{}-{:02d}".format(block_id, param_id)
            self.data["params"][key_name]["max"] = max_value
            self.data["params"][key_name]["min"] = min_value
            self.data["params"][key_name]["default"] = default_value
            self.data["params"][key_name]["unit"] = unit

            is_end, block_id, param_id, max_value, min_value, default_value, unit = self._load_one_max_min_default_unit_param()

    def _load_section_0007_null_block(self, expected_end):
        self._check_equal_array([0x00] * 0x30)

    def _load_section_0008_numbered_null_blocks(self, expected_end):
        null_block_count, = struct.unpack("<H", self.binary[self.current_offset : self.current_offset + 2])
        self.current_offset += 2
        self._check_equal_array([0x00] * 14)
        if null_block_count != 0x40:
            raise ASDAParseError("Section type 0x008: unexpected null_block_count {}".format(null_block_count))
        for null_id in range(null_block_count):
            real_null_block_id, = struct.unpack("<H", self.binary[self.current_offset : self.current_offset + 2])
            self.current_offset += 2
            if null_id != real_null_block_id:
                raise ASDAParseError("Section type 0x008: unexpected null_block_id {}, expected {}".format(real_null_block_id, null_id))
            self._check_equal_array([0x00] * (14 + 0x80))

    def _check_eof(self):
        if self.current_offset != len(self.binary):
            raise ASDAParseError("File has length {}, but we parsed {}".format(len(self.binary), self.current_offset))

    def parse(self):
        self.data = {}
        self.current_offset = 0
        self._check_equal("magic")
        self._load_storage_mode()
        self._load_asdasoft_version_string()
        self._check_equal("before_table")
        self._load_section_table()
        self._load_sections()
        self._check_eof()

    def _reconstruct_block_array(self, array):
        self.binary_reconstruct += bytes(array)

    def _reconstruct_block(self, constant_name):
        self._reconstruct_block_array(self.BINARY_CONSTANTS[constant_name])

    def _reconstruct_block_to_array(self, constant_name):
        return bytes(self.BINARY_CONSTANTS[constant_name])

    def _reconstruct_storage_mode(self):
        self.binary_reconstruct += struct.pack("<L", self.data["storage_mode"])

    def _reconstruct_asdasoft_version_string_to_array(self):
        reconstructed_encoded_version_string = self.data["asdasoft_version_string"].encode()
        version_length = len(reconstructed_encoded_version_string)
        reconstructed_string_binary = bytearray(b'\x00' * self.ASDASOFT_VERSION_STRING_LEN)
        reconstructed_string_binary[:version_length] = reconstructed_encoded_version_string
        return reconstructed_string_binary

    def _reconstruct_asdasoft_version_string(self):
        self.binary_reconstruct += self._reconstruct_asdasoft_version_string_to_array()

    def _reconstruct_section_table(self):
        for row in self.data["section_table"]:
            self.binary_reconstruct += struct.pack("<HL", row["section_type"], row["section_offset"])
            self._reconstruct_block_array([0x00] * 10)

    def _reconstruct_section_header_to_array(self, section_type, section_content_length):
        section_length = section_content_length + 16
        return struct.pack("<HL", section_type, section_length) + bytes([0x00] * 10)

    def _reconstruct_one_section_to_array(self, section_type):
        section_content_array = b''
        if section_type == 0x0001:
            section_content_array = self._reconstruct_section_0001_firmware_version_to_array()
        elif section_type == 0x0002:
            section_content_array = self._reconstruct_section_0002_unknown_to_array()
        elif section_type == 0x0018:
            section_content_array = self._reconstruct_section_0018_current_params_to_array()
        elif section_type == 0x0006:
            section_content_array = self._reconstruct_section_0006_max_min_default_unit_params_to_array()
        elif section_type == 0x0007:
            section_content_array = self._reconstruct_section_0007_null_block_to_array()
        elif section_type == 0x0008:
            section_content_array = self._reconstruct_section_0008_numbered_null_blocks_to_array()
        else:
            raise ASDAReconstructError("Cannot reconstruct unknown type 0x{:04X}".format(section_type))
        return self._reconstruct_section_header_to_array(section_type, len(section_content_array)) + section_content_array

    def _reconstruct_sections(self):
        for section_number, section in enumerate(self.data["section_table"]):
            if section["section_offset"] != len(self.binary_reconstruct):
                raise ASDAReconstructError("Offset error: we want to write section #{} (section type 0x{:04X}) at offset 0x{:04X}, but offset 0x{:04X} is specified in the section table".format(section_number, section["section_type"], len(self.binary_reconstruct), section["section_offset"]))

            section_array = self._reconstruct_one_section_to_array(section["section_type"])
            if section["section_length"] != len(section_array):
                raise ASDAReconstructError("Length error: we want to write section #{} (section type 0x{:04X}) with length 0x{:04X}, but length 0x{:04X} is specified in the section table".format(section_number, section["section_type"], len(section_array), section["section_length"]))
            self.binary_reconstruct += section_array

    def _reconstruct_section_0001_firmware_version_to_array(self):
        ret = self._reconstruct_block_to_array("0001_firmware_version_1")
        ret += struct.pack("<LL", self.data["firmware_version"], self.data["firmware_version"])
        ret += self._reconstruct_block_to_array("0001_firmware_version_2")
        ret += struct.pack("<LL", self.data["firmware_subversion"], self.data["firmware_subversion"])
        ret += bytes([0x00] * 100)
        return ret

    def _reconstruct_section_0002_unknown_to_array(self):
        ret = self._reconstruct_block_to_array("0002_unknown_1")
        ret += struct.pack("<H", self.data["0002_unknown_x"])
        ret += self._reconstruct_block_to_array("0002_unknown_2")
        return ret

    def _reconstruct_section_0018_current_params_to_array(self):
        ret = b''
        for key in sorted(self.data["params"].keys()):
            number_strings = re.findall(r'\d+', key)
            block_id, param_id = map(int, number_strings)
            ret += struct.pack("<HHL", block_id, param_id, self.data["params"][key]["current"])
        ret += struct.pack("<HHL", 0, 0, 0)
        return ret

    def _reconstruct_section_0006_max_min_default_unit_params_to_array(self):
        ret = b''
        for key in sorted(self.data["params"].keys()):
            number_strings = re.findall(r'\d+', key)
            block_id, param_id = map(int, number_strings)
            ret += struct.pack("<HHLLL", block_id, param_id,
                    self.swap_words(self.data["params"][key]["max"]),
                    self.swap_words(self.data["params"][key]["min"]),
                    self.swap_words(self.data["params"][key]["default"])
                    )
            ret += struct.pack("<H", self.data["params"][key]["unit"])
            ret += self._reconstruct_block_to_array("0006_unit_param_unknown")
        ret += struct.pack("<HHLLL", 0, 0, 0, 0, 0)
        return ret

    def _reconstruct_section_0007_null_block_to_array(self):
        return bytes([0x00] * 0x30)

    def _reconstruct_section_0008_numbered_null_blocks_to_array(self):
        null_block_count = 0x40
        ret = struct.pack("<H", null_block_count)
        ret += bytes([0x00] * 14)

        for null_id in range(null_block_count):
            ret += struct.pack("<H", null_id)
            ret += bytes([0x00] * (14 + 0x80))
        return ret

    def reconstruct(self):
        self.binary_reconstruct = b''
        self._reconstruct_block("magic")
        self._reconstruct_storage_mode()
        self._reconstruct_asdasoft_version_string()
        self._reconstruct_block("before_table")
        self._reconstruct_section_table()
        self._reconstruct_sections()

    def simple_print(self):
        print(self.to_json())

    def to_json(self):
        return json.dumps(self.data, indent=4, sort_keys=True)

    def from_json(self, json_string):
        self.data = json.loads(json_string)

    def from_json_file(self, json_file):
        with open(json_file, "r") as f:
            self.data = json.load(f)


def main():
    if len(sys.argv) in [2, 3]:
        filename_in = sys.argv[1]

        parser = ASDAParser()
        parser.load_param_file(filename_in)
        parser.parse()

        if len(sys.argv) == 2:
            parser.simple_print()
        else:
            filename_out = sys.argv[2]
            with open(filename_out, "w") as f:
                print(parser.to_json(), file=f)
        parser.reconstruct()
        parser.assert_reconstruction_correct()
    else:
        print("Usage: python3 {} input_file.par [output_file.json]".format(sys.argv[0]), file=sys.stderr)


if __name__ == "__main__":
    main()
