#!/usr/bin/env python3
# Script to extract files from a TNEF file using tnefparse

import sys
import struct
from tnefparse import TNEF

def extract_tnef(tnef_file):
    try:
        with open(tnef_file, 'rb') as f:
            tnef_data = f.read()
        
        # Print raw data for debugging
        print(f"TNEF file size: {len(tnef_data)} bytes")
        print(f"TNEF signature (first 4 bytes): 0x{tnef_data[0:4].hex()}")
        
        # Try to parse the TNEF data
        try:
            tnef = TNEF(tnef_data)
            
            print(f"TNEF version: {tnef.version}")
            print(f"Message attributes: {len(tnef.mapiprops)}")
            print(f"Attachments: {len(tnef.attachments)}")
            
            for i, attachment in enumerate(tnef.attachments):
                print(f"\nAttachment {i+1}:")
                
                # Handle potential encoding issues with filenames
                try:
                    name = attachment.name.decode('utf-8') if isinstance(attachment.name, bytes) else attachment.name
                except (AttributeError, UnicodeDecodeError):
                    name = f"attachment_{i+1}"
                
                try:
                    long_name = attachment.long_filename.decode('utf-8') if isinstance(attachment.long_filename, bytes) else attachment.long_filename
                except (AttributeError, UnicodeDecodeError):
                    long_name = None
                
                print(f"  Filename: {name}")
                print(f"  Long filename: {long_name}")
                print(f"  Size: {len(attachment.data) if hasattr(attachment, 'data') else 'unknown'} bytes")
                
                # Save the attachment
                filename = long_name or name
                if filename and hasattr(attachment, 'data'):
                    with open(filename, 'wb') as f:
                        f.write(attachment.data)
                    print(f"  Saved as: {filename}")
                else:
                    print("  No filename or data found, not saving")
        
        except Exception as e:
            print(f"Error parsing TNEF data: {e}")
            
            # Try manual extraction of the embedded filename
            try:
                # Look for the attAttachTitle attribute (0x8010)
                title_marker = b'\x02\x10\x80\x00\x01'
                title_pos = tnef_data.find(title_marker)
                
                if title_pos > 0:
                    # Skip the marker and get the length (4 bytes)
                    length_pos = title_pos + len(title_marker)
                    length = struct.unpack("<I", tnef_data[length_pos:length_pos+4])[0]
                    
                    # Get the filename (null-terminated string)
                    filename_pos = length_pos + 4
                    filename_bytes = tnef_data[filename_pos:filename_pos+length]
                    
                    # Remove null terminator if present
                    if filename_bytes.endswith(b'\x00'):
                        filename_bytes = filename_bytes[:-1]
                    
                    filename = filename_bytes.decode('utf-8', errors='replace')
                    print(f"Found embedded filename: {filename}")
                    
                    # Look for the attAttachData attribute (0x800f)
                    data_marker = b'\x02\x0f\x80\x00\x06'
                    data_pos = tnef_data.find(data_marker)
                    
                    if data_pos > 0:
                        # Skip the marker and get the length (4 bytes)
                        data_length_pos = data_pos + len(data_marker)
                        data_length = struct.unpack("<I", tnef_data[data_length_pos:data_length_pos+4])[0]
                        
                        # Get the file data
                        data_start = data_length_pos + 4
                        file_data = tnef_data[data_start:data_start+data_length]
                        
                        # Save the file
                        with open(filename, 'wb') as f:
                            f.write(file_data)
                        print(f"Saved file: {filename} ({len(file_data)} bytes)")
                    else:
                        print("Could not find file data")
                else:
                    print("Could not find embedded filename")
            
            except Exception as e2:
                print(f"Error in manual extraction: {e2}")
    
    except Exception as e:
        print(f"Error extracting TNEF file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <tnef_file>")
        sys.exit(1)
    
    extract_tnef(sys.argv[1])

