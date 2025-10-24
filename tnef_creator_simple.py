#!/usr/bin/env python3
# Simple TNEF Creator - Generate TNEF files with custom embedded filenames
# This script creates a TNEF file (winmail.dat) with a custom embedded filename
# Compatible with standard TNEF extraction tools including --number-backups option

import struct
import os
import argparse
import random
import time
import datetime

# TNEF Constants
TNEF_SIGNATURE = 0x223e9f78  # TNEF signature
LVL_MESSAGE = 0x01  # Message level
LVL_ATTACHMENT = 0x02  # Attachment level

# TNEF Attribute IDs
attMessageClass = 0x8008
attSubject = 0x8004
attAttachTitle = 0x8010
attAttachData = 0x800f
attAttachTransportFilename = 0x9001

# TNEF Data Types
atpString = 0x0001
atpText = 0x0002
atpByte = 0x0006

def calculate_checksum(data):
    """Calculate TNEF checksum (16-bit sum of bytes modulo 65536)"""
    checksum = 0
    for b in data:
        checksum = (checksum + b) % 65536
    return checksum

def create_tnef_attribute(level, attr_id, attr_type, data):
    """Create a TNEF attribute with the given level, ID, type, and data"""
    # Pack the attribute ID and type
    packed_id = struct.pack("<HH", attr_id, attr_type)
    
    # Pack the length of the data
    length = struct.pack("<I", len(data))
    
    # Calculate checksum for the data
    checksum = calculate_checksum(data)
    checksum_bytes = struct.pack("<H", checksum)
    
    # Combine all parts
    attribute = bytes([level]) + packed_id + length + data + checksum_bytes
    
    return attribute

def create_tnef_file(output_file, embedded_filename, file_content=None):
    """Create a TNEF file with a custom embedded filename"""
    if file_content is None:
        # Create some dummy content if none provided
        file_content = b"This is a test file created by TNEF Creator."
    
    # Generate a random key (16-bit unsigned integer)
    key = random.randint(1, 65535)
    key_bytes = struct.pack("<H", key)
    
    # Start with TNEF signature and key
    tnef_data = struct.pack("<I", TNEF_SIGNATURE) + key_bytes
    
    # Add message-level attributes
    # Message Class
    msg_class = b"IPM.Note\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attMessageClass, atpString, msg_class)
    
    # Subject
    subject = b"TNEF Test Message\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attSubject, atpString, subject)
    
    # Add attachment-level attributes
    
    # 1. Attachment Title (filename)
    # Ensure filename is null-terminated
    if isinstance(embedded_filename, str):
        filename_bytes = embedded_filename.encode('utf-8') + b'\x00'
    else:
        filename_bytes = embedded_filename + b'\x00'
    
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTitle, atpString, filename_bytes)
    
    # 2. Transport Filename (often needed for proper extraction)
    transport_filename = b"winmail.dat\x00"
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTransportFilename, atpString, transport_filename)
    
    # 3. Attachment Data
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachData, atpByte, file_content)
    
    # Write the TNEF data to the output file
    with open(output_file, 'wb') as f:
        f.write(tnef_data)
    
    print(f"TNEF file created: {output_file}")
    print(f"Embedded filename: {embedded_filename}")
    print(f"File size: {len(tnef_data)} bytes")

def main():
    parser = argparse.ArgumentParser(description='Create a TNEF file with a custom embedded filename')
    parser.add_argument('-o', '--output', default='winmail.dat', help='Output TNEF file (default: winmail.dat)')
    parser.add_argument('-f', '--filename', required=True, help='Custom embedded filename')
    parser.add_argument('-c', '--content', help='File to use as content for the embedded file')
    
    args = parser.parse_args()
    
    file_content = None
    if args.content:
        try:
            with open(args.content, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            print(f"Error reading content file: {e}")
            return
    
    create_tnef_file(args.output, args.filename, file_content)

if __name__ == "__main__":
    main()

