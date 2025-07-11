#!/usr/bin/env python3
# TNEF Creator Compatible - Generate TNEF files with custom embedded filenames
# This script creates a TNEF file (winmail.dat) with a custom embedded filename
# Compatible with standard TNEF extraction tools including --number-backups option

import struct
import os
import argparse
import random
import time
import datetime
import binascii

# TNEF Constants
TNEF_SIGNATURE = 0x223e9f78  # TNEF signature
LVL_MESSAGE = 0x01  # Message level
LVL_ATTACHMENT = 0x02  # Attachment level

# TNEF Attribute IDs
attMessageClass = 0x8008
attSubject = 0x8004
attDateSent = 0x8005
attDateReceived = 0x8006
attMessageStatus = 0x8007
attMessageID = 0x8009
attBody = 0x800c
attEndOfAttachments = 0x800d
attAttachTitle = 0x8010
attAttachData = 0x800f
attAttachCreateDate = 0x8012
attAttachModifyDate = 0x8013
attDateModified = 0x8020
attAttachTransportFilename = 0x9001
attAttachRenddata = 0x9002
attMAPIProps = 0x9003
attRecipTable = 0x9004
attAttachment = 0x9005
attTnefVersion = 0x9006
attOemCodepage = 0x9007
attOriginalMessageClass = 0x9008

# TNEF Data Types
atpTriples = 0x0000
atpString = 0x0001
atpText = 0x0002
atpDate = 0x0003
atpShort = 0x0004
atpLong = 0x0005
atpByte = 0x0006
atpWord = 0x0007
atpDword = 0x0008
atpMax = 0x0009

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

def get_date_as_tnef_date():
    """Get current date in TNEF date format"""
    # TNEF date format is a 14-byte structure
    # Use a fixed date for compatibility
    # Format: year (2 bytes), month (2 bytes), day (2 bytes), hour (2 bytes), 
    # minute (2 bytes), second (2 bytes), dayofweek (2 bytes)
    return struct.pack("<HHHHHHH", 2023, 1, 1, 12, 0, 0, 0)

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
    
    # Message ID
    msg_id = b"<message-id@example.com>\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attMessageID, atpString, msg_id)
    
    # Subject
    subject = b"TNEF Test Message\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attSubject, atpString, subject)
    
    # Date Sent
    date_sent = get_date_as_tnef_date()
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attDateSent, atpDate, date_sent)
    
    # Date Received
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attDateReceived, atpDate, date_sent)
    
    # Body
    body = b"This is a TNEF message with a custom embedded file.\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attBody, atpText, body)
    
    # Add attachment-level attributes
    
    # Attachment Rendering Data
    rend_data = struct.pack("<HII", 0, 0, 0)
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachRenddata, atpDword, rend_data)
    
    # Attachment Title (filename)
    # Ensure filename is null-terminated
    if isinstance(embedded_filename, str):
        filename_bytes = embedded_filename.encode('utf-8') + b'\x00'
    else:
        filename_bytes = embedded_filename + b'\x00'
    
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTitle, atpString, filename_bytes)
    
    # Transport Filename
    transport_filename = b"winmail.dat\x00"
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTransportFilename, atpString, transport_filename)
    
    # Attachment Creation Date
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachCreateDate, atpDate, date_sent)
    
    # Attachment Modification Date
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachModifyDate, atpDate, date_sent)
    
    # Attachment Data
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachData, atpByte, file_content)
    
    # End of Attachments marker
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attEndOfAttachments, atpByte, b'')
    
    # Write the TNEF data to the output file
    with open(output_file, 'wb') as f:
        f.write(tnef_data)
    
    print(f"TNEF file created: {output_file}")
    print(f"Embedded filename: {embedded_filename}")
    print(f"File size: {len(tnef_data)} bytes")
    
    # Print hex dump of the first 64 bytes for debugging
    print("\nHex dump of first 64 bytes:")
    hex_dump = binascii.hexlify(tnef_data[:64]).decode('ascii')
    for i in range(0, len(hex_dump), 32):
        print(hex_dump[i:i+32])

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

