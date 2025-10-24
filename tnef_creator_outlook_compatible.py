#!/usr/bin/env python3
# TNEF Creator Outlook Compatible - Generate TNEF files with multiple custom embedded filenames
# This script creates a TNEF file (winmail.dat) with multiple custom embedded files
# Compatible with Microsoft Outlook TNEF format and standard TNEF extraction tools

import struct
import os
import argparse
import random
import time
import datetime
import binascii
import json

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

def create_tnef_file_with_multiple_attachments(output_file, attachments):
    """Create a TNEF file with multiple custom embedded files
    
    Args:
        output_file (str): Path to the output TNEF file
        attachments (list): List of dictionaries with 'filename' and 'content' keys
    """
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
    body = b"This is a TNEF message with multiple custom embedded files.\x00"
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attBody, atpText, body)
    
    # Process each attachment
    for i, attachment in enumerate(attachments):
        # Ensure filename is null-terminated
        if isinstance(attachment['filename'], str):
            filename_bytes = attachment['filename'].encode('utf-8') + b'\x00'
        else:
            filename_bytes = attachment['filename'] + b'\x00'
        
        # Create a unique transport filename for each attachment
        transport_filename = f"winmail{i+1}.dat\x00".encode('utf-8')
        
        # 1. Start with Attachment Rendering Data
        rend_data = struct.pack("<HII", 0, 0, 0)
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachRenddata, atpDword, rend_data)
        
        # 2. Add Attachment Title (the custom filename)
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTitle, atpString, filename_bytes)
        
        # 3. Add Transport Filename
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachTransportFilename, atpString, transport_filename)
        
        # 4. Add Attachment Creation Date
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachCreateDate, atpDate, date_sent)
        
        # 5. Add Attachment Modification Date
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachModifyDate, atpDate, date_sent)
        
        # 6. Add Attachment Data
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachData, atpByte, attachment['content'])
        
        # 7. Add Attachment marker to indicate end of this attachment
        # This is a critical step for compatibility with standard TNEF tools
        tnef_data += create_tnef_attribute(LVL_ATTACHMENT, attAttachment, atpByte, b'')
    
    # Add End of Attachments marker at the message level
    # This is required to properly terminate the TNEF file
    tnef_data += create_tnef_attribute(LVL_MESSAGE, attEndOfAttachments, atpByte, b'')
    
    # Write the TNEF data to the output file
    with open(output_file, 'wb') as f:
        f.write(tnef_data)
    
    print(f"TNEF file created: {output_file}")
    print(f"Number of embedded files: {len(attachments)}")
    for i, attachment in enumerate(attachments, 1):
        print(f"  {i}. {attachment['filename']} ({len(attachment['content'])} bytes)")
    print(f"Total file size: {len(tnef_data)} bytes")
    
    # Print hex dump of the first 64 bytes for debugging
    print("\nHex dump of first 64 bytes:")
    hex_dump = binascii.hexlify(tnef_data[:64]).decode('ascii')
    for i in range(0, len(hex_dump), 32):
        print(hex_dump[i:i+32])

def parse_attachment_spec(spec):
    """Parse an attachment specification in the format 'file:name'"""
    if ':' in spec:
        file_path, custom_name = spec.split(':', 1)
    else:
        file_path = spec
        custom_name = os.path.basename(file_path)
    
    return file_path, custom_name

def main():
    parser = argparse.ArgumentParser(description='Create a TNEF file with multiple custom embedded files')
    parser.add_argument('-o', '--output', default='winmail.dat', help='Output TNEF file (default: winmail.dat)')
    
    # Multiple attachment options
    parser.add_argument('-a', '--attach', action='append', help='Attachment in format "file:name" (can be used multiple times)')
    parser.add_argument('-f', '--file', action='append', help='File to attach (can be used multiple times)')
    parser.add_argument('-n', '--name', action='append', help='Custom name for attached file (must match number of --file options)')
    parser.add_argument('-j', '--json', help='JSON file containing attachment specifications')
    
    args = parser.parse_args()
    
    attachments = []
    
    # Process --attach options
    if args.attach:
        for spec in args.attach:
            file_path, custom_name = parse_attachment_spec(spec)
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                attachments.append({'filename': custom_name, 'content': content})
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
    
    # Process --file and --name options
    if args.file:
        names = args.name if args.name else [None] * len(args.file)
        if len(names) < len(args.file):
            names.extend([None] * (len(args.file) - len(names)))
        
        for file_path, custom_name in zip(args.file, names):
            if custom_name is None:
                custom_name = os.path.basename(file_path)
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                attachments.append({'filename': custom_name, 'content': content})
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
    
    # Process --json option
    if args.json:
        try:
            with open(args.json, 'r') as f:
                json_data = json.load(f)
            
            for item in json_data:
                if 'file' in item and 'name' in item:
                    try:
                        with open(item['file'], 'rb') as f:
                            content = f.read()
                        attachments.append({'filename': item['name'], 'content': content})
                    except Exception as e:
                        print(f"Error reading file {item['file']}: {e}")
        except Exception as e:
            print(f"Error processing JSON file: {e}")
    
    # Check if we have any attachments
    if not attachments:
        print("Error: No attachments specified. Use --attach, --file/--name, or --json options.")
        parser.print_help()
        return
    
    create_tnef_file_with_multiple_attachments(args.output, attachments)

if __name__ == "__main__":
    main()

