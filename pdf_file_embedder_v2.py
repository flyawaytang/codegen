#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF File Embedder using pikepdf (Version 2)

This script embeds a file into a PDF document by:
1. Scanning the PDF to find all used object numbers
2. Finding a free object number
3. Embedding the file and tracking the assigned object number
4. Providing detailed information about the embedding process
"""

import os
import sys
import argparse
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Name, Dictionary, Array, Stream


def analyze_pdf_objects(pdf):
    """
    Analyze the PDF and return information about its objects.
    
    Args:
        pdf: A pikepdf.Pdf object
        
    Returns:
        dict: Information about PDF objects
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
                'type': type(obj).__name__
            }
            max_obj_num = max(max_obj_num, obj_num)
    
    # Find free object numbers
    free_numbers = [i for i in range(1, max_obj_num + 10) if i not in objects]
    
    return {
        'objects': objects,
        'max_object_number': max_obj_num,
        'object_count': len(objects),
        'free_numbers': free_numbers[:10]  # Return first 10 free numbers
    }


def embed_file(pdf, file_path):
    """
    Embed a file into the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        file_path: Path to the file to embed
        
    Returns:
        tuple: (embedded_file_obj, filespec_obj) - The embedded file and filespec objects
    """
    # Read the file to embed
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # Create file specification dictionary
    file_name = os.path.basename(file_path)
    
    # Create the embedded file stream
    embedded_file = Stream(pdf, file_data)
    
    # Create the file specification dictionary
    filespec = Dictionary(
        Type=Name.Filespec,
        F=file_name,
        EF=Dictionary(
            F=embedded_file
        )
    )
    
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


def main():
    parser = argparse.ArgumentParser(description='Embed a file into a PDF using a free object number')
    parser.add_argument('input_pdf', help='Input PDF file')
    parser.add_argument('file_to_embed', help='File to embed in the PDF')
    parser.add_argument('output_pdf', help='Output PDF file')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze the PDF without embedding')
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input PDF file '{args.input_pdf}' does not exist")
        return 1
    
    if not args.analyze_only and not os.path.exists(args.file_to_embed):
        print(f"Error: File to embed '{args.file_to_embed}' does not exist")
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
            print(f"First 10 free object numbers: {analysis['free_numbers']}")
            
            if args.analyze_only:
                print("\nDetailed object information:")
                for obj_num, info in sorted(analysis['objects'].items()):
                    print(f"Object {obj_num} (Generation {info['generation']}): {info['type']}")
                return 0
            
            # Embed the file
            print(f"\nEmbedding file: {args.file_to_embed}")
            embedded_file, filespec = embed_file(pdf, args.file_to_embed)
            
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
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

