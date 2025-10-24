#!/usr/bin/env python3
# Manual TNEF extractor

import sys
import struct
import os

# TNEF Constants
TNEF_SIGNATURE = 0x223e9f78  # TNEF signature
LVL_MESSAGE = 0x01  # Message level
LVL_ATTACHMENT = 0x02  # Attachment level

# TNEF Attribute IDs
attAttachTitle = 0x8010
attAttachData = 0x800f

def extract_tnef_manual(tnef_file):
    try:
        with open(tnef_file, 'rb') as f:
            data = f.read()
        
        # Check TNEF signature
        if len(data) < 6:
            print("File too small to be a TNEF file")
            return
        
        signature = struct.unpack("<I", data[0:4])[0]
        if signature != TNEF_SIGNATURE:
            print(f"Invalid TNEF signature: 0x{signature:08x}, expected 0x{TNEF_SIGNATURE:08x}")
            return
        
        key = struct.unpack("<H", data[4:6])[0]
        print(f"TNEF signature: 0x{signature:08x}")
        print(f"TNEF key: 0x{key:04x}")
        
        # Parse attributes
        pos = 6
        filename = None
        file_data = None
        
        while pos < len(data):
            if pos + 8 > len(data):
                print("Unexpected end of file while parsing attribute header")
                break
            
            level = data[pos]
            pos += 1
            
            attr_id = struct.unpack("<H", data[pos:pos+2])[0]
            pos += 2
            
            attr_type = struct.unpack("<H", data[pos:pos+2])[0]
            pos += 2
            
            length = struct.unpack("<I", data[pos:pos+4])[0]
            pos += 4
            
            if pos + length + 2 > len(data):
                print(f"Unexpected end of file while parsing attribute data (level={level}, id=0x{attr_id:04x}, type=0x{attr_type:04x}, length={length})")
                break
            
            attr_data = data[pos:pos+length]
            pos += length
            
            checksum = struct.unpack("<H", data[pos:pos+2])[0]
            pos += 2
            
            # Calculate checksum
            calc_checksum = sum(attr_data) % 65536
            
            print(f"Attribute: level={level}, id=0x{attr_id:04x}, type=0x{attr_type:04x}, length={length}, checksum=0x{checksum:04x} (calculated: 0x{calc_checksum:04x})")
            
            # Check for filename (attAttachTitle)
            if level == LVL_ATTACHMENT and attr_id == attAttachTitle:
                # Remove null terminator if present
                if attr_data.endswith(b'\x00'):
                    attr_data = attr_data[:-1]
                
                filename = attr_data.decode('utf-8', errors='replace')
                print(f"Found filename: {filename}")
            
            # Check for file data (attAttachData)
            if level == LVL_ATTACHMENT and attr_id == attAttachData:
                file_data = attr_data
                print(f"Found file data: {len(file_data)} bytes")
        
        # Save the file if both filename and data were found
        if filename and file_data:
            with open(filename, 'wb') as f:
                f.write(file_data)
            print(f"Saved file: {filename} ({len(file_data)} bytes)")
        else:
            if not filename:
                print("No filename found")
            if not file_data:
                print("No file data found")
    
    except Exception as e:
        print(f"Error extracting TNEF file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <tnef_file>")
        sys.exit(1)
    
    extract_tnef_manual(sys.argv[1])

