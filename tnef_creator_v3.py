#!/usr/bin/env python3
# TNEF Creator V3 - Generate TNEF files with custom embedded filenames
# This script creates a TNEF file (winmail.dat) with a custom embedded filename
# Compatible with standard TNEF extraction tools including --number-backups option

import struct
import os
import argparse
import random
import binascii
import time
import datetime

# TNEF Constants
TNEF_SIGNATURE = 0x223e9f78  # TNEF signature
LVL_MESSAGE = 0x01  # Message level
LVL_ATTACHMENT = 0x02  # Attachment level

# TNEF Attribute IDs
attTnefVersion = 0x9002
attOemCodepage = 0x9007
attAttachRenddata = 0x9002
attAttachment = 0x9005
attAttachTitle = 0x8010
attAttachData = 0x800f  # Changed from 0x8011 to 0x800f which is standard
attAttachMetaFile = 0x9003
attAttachCreateDate = 0x8012
attAttachModifyDate = 0x8013
attAttachTransportFilename = 0x9001
attAttachMimeTag = 0x9008
attMessageClass = 0x8008
attOriginalMessageClass = 0x0006
attMessageID = 0x8009
attParentID = 0x800A
attConversationID = 0x800B
attBody = 0x800C
attPriority = 0x800D
attAttachSize = 0x8040
attSubject = 0x8004
attDateSent = 0x8005
attDateReceived = 0x8006
attAttachData = 0x800f
attAttachCreateDate = 0x8012
attAttachModifyDate = 0x8013
attDateModified = 0x8020
attAttachMethod = 0x9003
attAttachContentId = 0x9004
attAttachDisposition = 0x9006
attAttachContentLocation = 0x9007

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

def get_current_time_as_dos_date():
    """Convert current time to DOS date/time format for TNEF"""
    t = time.localtime()
    dos_date = ((t.tm_year - 1980) << 9) | (t.tm_mon << 5) | t.tm_mday
    dos_time = (t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2)
    return struct.pack("<HH", dos_time, dos_date)

def get_current_time_as_tnef_date():
    """Convert current time to TNEF date format"""
    now = datetime.datetime.now()
    # TNEF date format: year, month, day, hour, minute, second, dayofweek
    # All values are 16-bit integers
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minute = now.minute
    second = now.second
    dayofweek = now.weekday()  # 0-6, Monday is 0
    
    # Convert to Windows/TNEF day of week (0-6, Sunday is 0)
    dayofweek = (dayofweek + 1) % 7
    
    return struct.pack("<HHHHHH", year, month, day, hour, minute, second)

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
    
    # Message ID (required by some TNEF parsers)
    msg_id = b"<message-id@example.com>\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attMessageID, atpString, msg_id)
    
    # Subject
    subject = b"TNEF Test Message\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attSubject, atpString, subject)
    
    # Date Sent
    date_sent = get_current_time_as_tnef_date()
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attDateSent, atpDate, date_sent)
    
    # Date Received (same as sent for simplicity)
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attDateReceived, atpDate, date_sent)
    
    # Add a simple message body
    body = b"This is a TNEF message with a custom embedded file.\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attBody, atpText, body)
    
    # Priority (normal)
    priority = struct.pack("<H", 3)
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attPriority, atpShort, priority)
    
    # Add attachment-level attributes
    
    # 1. Attachment Rendering Data
    rend_data = struct.pack("<HII", 0, 0, 0)  # Simplified rendering data
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachRenddata, atpDword, rend_data)
    
    # 2. Attachment Title (filename)
    # Ensure filename is null-terminated
    if isinstance(embedded_filename, str):
        filename_bytes = embedded_filename.encode('utf-8') + b'\x00'
    else:
        filename_bytes = embedded_filename + b'\x00'
    
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTitle, atpString, filename_bytes)
    
    # 3. Transport Filename (often needed for proper extraction)
    transport_filename = b"winmail.dat\x00"
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTransportFilename, atpString, transport_filename)
    
    # 4. MIME Type
    mime_type = b"application/octet-stream\x00"
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachMimeTag, atpString, mime_type)
    
    # 5. Creation and Modification Dates
    date_data = get_current_time_as_dos_date()
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachCreateDate, atpDate, date_data)
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachModifyDate, atpDate, date_data)
    
    # 6. Attachment Size
    size_data = struct.pack("<I", len(file_content))
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachSize, atpLong, size_data)
    
    # 7. Attachment Method (standard value for embedded files)
    method_data = struct.pack("<I", 1)  # 1 = ATTACH_BY_VALUE
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachMethod, atpDword, method_data)
    
    # 8. Attachment Data
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachData, atpByte, file_content)
    
    # 9. Empty attachment marker (used by some TNEF parsers)
    empty_data = b""
    tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachment, atpByte, empty_data)
    
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

