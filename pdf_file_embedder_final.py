#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF File Embedder using pikepdf

This script embeds a file into a PDF document by:
1. Scanning the PDF to find all used object numbers
2. Finding a free object number
3. Embedding the file using pikepdf
4. Tracking and reporting the assigned object numbers

Author: Codegen
License: MIT
"""

import os
import sys
import argparse
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Name, Dictionary, Array, Stream


def manually_set_object_number(pdf, obj, obj_num):
    """
    Attempt to manually set the object number for a pikepdf object.
    This is an experimental function and may not work in all cases.
    
    Args:
        pdf: A pikepdf.Pdf object
        obj: The pikepdf object to modify
        obj_num: The desired object number
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # This is a hacky way to try to set object numbers
        # It relies on internal pikepdf implementation details that may change
        
        # First, check if the object already has an object number
        if hasattr(obj, 'objgen'):
            current_obj_num, gen = obj.objgen
            if current_obj_num == obj_num:
                # Object already has the desired number
                return True
        
        # Try to access the internal _objects list
        if hasattr(pdf, '_objects'):
            # Make sure the list is long enough
            while len(pdf._objects) <= obj_num:
                pdf._objects.append(None)
            
            # Set the object at the desired position
            pdf._objects[obj_num] = obj
            return True
        
        # Alternative approach using lower-level access
        if hasattr(pdf, '_pikepdf'):
            # This is even more implementation-specific
            if hasattr(pdf._pikepdf, 'get_object_id'):
                # Try to set the object ID
                pdf._pikepdf.get_object_id(obj, obj_num, 0)
                return True
        
        return False
    except Exception as e:
        print(f"Warning: Failed to set object number: {e}")
        return False


def analyze_pdf_objects(pdf):
    """
    Analyze the PDF and return information about its objects.
    
    Args:
        pdf: A pikepdf.Pdf object
        
    Returns:
        dict: Information about PDF objects including:
            - objects: Dictionary mapping object numbers to their information
            - max_object_number: The highest object number in use
            - object_count: Total number of objects
            - free_numbers: List of available object numbers
    """
    # Get all indirect objects
    objects = {}
    max_obj_num = 0
    
    # Iterate through all objects in the PDF
    for obj in pdf.objects:
        if obj is not None and hasattr(obj, 'objgen'):
            obj_num, gen = obj.objgen
            objects[obj_num] = {
                'generation': gen,
                'type': type(obj).__name__,
                'object': obj
            }
            max_obj_num = max(max_obj_num, obj_num)
    
    # Find free object numbers
    free_numbers = [i for i in range(1, max_obj_num + 10) if i not in objects]
    
    return {
        'objects': objects,
        'max_object_number': max_obj_num,
        'object_count': len(objects),
        'free_numbers': free_numbers
    }


def embed_file(pdf, file_path, mime_type=None, filespec_obj_num=None):
    """
    Embed a file into the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        file_path: Path to the file to embed
        mime_type: Optional MIME type for the embedded file
        filespec_obj_num: Optional object number to use for the file specification
        
    Returns:
        tuple: (embedded_file_obj, filespec_obj) - The embedded file and filespec objects
    """
    # Read the file to embed
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # Create file specification dictionary
    file_name = os.path.basename(file_path)
    
    # Determine MIME type if not provided
    if mime_type is None:
        # Simple MIME type detection based on extension
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'text/xml',
            '.json': 'application/json',
            '.zip': 'application/zip',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }
        mime_type = mime_map.get(ext, 'application/octet-stream')
    
    # Create the embedded file stream with parameters
    params = {
        '/Type': Name.EmbeddedFile,
        '/Subtype': Name('/' + mime_type.split('/')[-1].capitalize()),
        '/Size': len(file_data)
    }
    embedded_file = Stream(pdf, file_data, params)
    
    # Create the file specification dictionary
    filespec = Dictionary(
        Type=Name.Filespec,
        F=file_name,
        UF=file_name,  # Unicode filename
        Desc=f"Embedded file: {file_name}",
        EF=Dictionary(
            F=embedded_file
        )
    )
    
    # Try to set the file specification object number if provided
    if filespec_obj_num is not None:
        success = manually_set_object_number(pdf, filespec, filespec_obj_num)
        if success:
            print(f"Successfully set file specification object number to {filespec_obj_num}")
        else:
            print(f"Warning: Failed to set file specification object number to {filespec_obj_num}")
    
    # Add the file to the PDF's embedded files
    if '/Names' not in pdf.Root:
        pdf.Root.Names = Dictionary()
    
    if '/EmbeddedFiles' not in pdf.Root.Names:
        pdf.Root.Names.EmbeddedFiles = Dictionary(
            Names=Array()
        )
    
    # Add the file to the Names array
    names_array = pdf.Root.Names.EmbeddedFiles.Names
    names_array.append(file_name)
    names_array.append(filespec)
    
    return embedded_file, filespec


def get_object_number(pdf_obj):
    """
    Get the object number of a pikepdf object.
    
    Args:
        pdf_obj: A pikepdf object
        
    Returns:
        int: The object number, or None if not available
    """
    if hasattr(pdf_obj, 'objgen'):
        obj_num, gen = pdf_obj.objgen
        return obj_num
    return None


def extract_embedded_file(pdf, output_dir='.'):
    """
    Extract all embedded files from a PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        output_dir: Directory to save extracted files
        
    Returns:
        list: Paths to extracted files
    """
    extracted_files = []
    
    # Check if the PDF has embedded files
    if '/Names' in pdf.Root and '/EmbeddedFiles' in pdf.Root.Names:
        names = pdf.Root.Names.EmbeddedFiles.Names
        
        # Process embedded files
        for i in range(0, len(names), 2):
            if i + 1 < len(names):
                filename = str(names[i])
                filespec = names[i + 1]
                
                if '/EF' in filespec and '/F' in filespec.EF:
                    embedded_file = filespec.EF.F
                    
                    # Get the object number
                    obj_num = get_object_number(embedded_file)
                    
                    # Create output filename with object number
                    base_name, ext = os.path.splitext(filename)
                    if obj_num is not None:
                        output_filename = f"{base_name}_obj{obj_num}{ext}"
                    else:
                        output_filename = filename
                    
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Extract and save the file
                    with open(output_path, 'wb') as f:
                        f.write(embedded_file.read_bytes())
                    
                    extracted_files.append(output_path)
    
    return extracted_files


def main():
    parser = argparse.ArgumentParser(description='Embed a file into a PDF using a free object number')
    parser.add_argument('input_pdf', help='Input PDF file')
    parser.add_argument('file_to_embed', nargs='?', help='File to embed in the PDF')
    parser.add_argument('output_pdf', nargs='?', help='Output PDF file')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze the PDF without embedding')
    parser.add_argument('--extract', action='store_true', help='Extract embedded files from the PDF')
    parser.add_argument('--output-dir', default='.', help='Directory to save extracted files (default: current directory)')
    parser.add_argument('--mime-type', help='MIME type for the embedded file')
    parser.add_argument('--obj-num', type=int, help='Specific object number to use for the embedded file')
    parser.add_argument('--filespec-obj-num', type=int, help='Specific object number to use for the file specification')
    
    args = parser.parse_args()
    
    # Check if input PDF exists
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input PDF file '{args.input_pdf}' does not exist")
        return 1
    
    try:
        # Open the PDF
        with Pdf.open(args.input_pdf) as pdf:
            # Print some information about the PDF
            print(f"PDF Version: {pdf.pdf_version}")
            print(f"Number of Pages: {len(pdf.pages)}")
            
            # Analyze PDF objects
            analysis = analyze_pdf_objects(pdf)
            print(f"Total objects: {analysis['object_count']}")
            print(f"Maximum object number: {analysis['max_object_number']}")
            print(f"Available free object numbers: {analysis['free_numbers'][:10]}...")
            
            if args.analyze_only:
                print("\nDetailed object information:")
                for obj_num, info in sorted(analysis['objects'].items()):
                    print(f"Object {obj_num} (Generation {info['generation']}): {info['type']}")
                return 0
            
            if args.extract:
                # Extract embedded files
                print("\nExtracting embedded files...")
                extracted = extract_embedded_file(pdf, args.output_dir)
                
                if extracted:
                    print(f"Extracted {len(extracted)} files:")
                    for path in extracted:
                        print(f"  - {path}")
                else:
                    print("No embedded files found in the PDF.")
                
                return 0
            
            # Check if file to embed and output PDF are provided
            if args.file_to_embed is None or args.output_pdf is None:
                print("Error: Both file_to_embed and output_pdf are required unless using --analyze-only or --extract")
                return 1
            
            # Check if file to embed exists
            if not os.path.exists(args.file_to_embed):
                print(f"Error: File to embed '{args.file_to_embed}' does not exist")
                return 1
            
            # Embed the file
            print(f"\nEmbedding file: {args.file_to_embed}")
            embedded_file, filespec = embed_file(pdf, args.file_to_embed, args.mime_type, args.filespec_obj_num)
            
            # Try to set the embedded file object number if provided
            if args.obj_num is not None:
                success = manually_set_object_number(pdf, embedded_file, args.obj_num)
                if success:
                    print(f"Successfully set embedded file object number to {args.obj_num}")
                else:
                    print(f"Warning: Failed to set embedded file object number to {args.obj_num}")
            
            # Get the assigned object numbers
            embedded_file_num = get_object_number(embedded_file)
            filespec_num = get_object_number(filespec)
            
            print(f"Embedded file object number: {embedded_file_num}")
            print(f"File specification object number: {filespec_num}")
            
            # Save the modified PDF
            pdf.save(args.output_pdf)
            print(f"Modified PDF saved to: {args.output_pdf}")
            
            # Verify the embedding
            print("\nVerifying embedded file...")
            with Pdf.open(args.output_pdf) as verify_pdf:
                if '/Names' in verify_pdf.Root and '/EmbeddedFiles' in verify_pdf.Root.Names:
                    names = verify_pdf.Root.Names.EmbeddedFiles.Names
                    if len(names) >= 2:
                        print(f"Verification successful: Found embedded file '{names[0]}'")
                    else:
                        print("Warning: Names array doesn't contain expected entries")
                else:
                    print("Warning: Could not find embedded files in the output PDF")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
