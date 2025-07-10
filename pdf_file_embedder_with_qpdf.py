#!/usr/bin/env python3
"""
PDF File Embedder with Custom Object Numbers using pikepdf and qpdf

This script embeds files into PDF documents and allows specifying custom object numbers
for both the embedded file and the file specification. It uses pikepdf for the basic
embedding functionality and then uses qpdf command-line tool for manipulating object numbers.

Usage:
    python pdf_file_embedder_with_qpdf.py input.pdf file_to_embed output.pdf --obj-num 10 --filespec-obj-num 20
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Name, Dictionary, Array, Stream


def analyze_pdf_objects(pdf):
    """
    Analyze the PDF objects and return information about them.
    
    Args:
        pdf: A pikepdf.Pdf object
        
    Returns:
        tuple: (used_obj_nums, max_obj_num, free_obj_nums)
    """
    used_obj_nums = set()
    
    # Iterate through all objects in the PDF
    for obj_num, obj in enumerate(pdf.objects):
        if obj is not None:
            used_obj_nums.add(obj_num)
    
    # Find the maximum object number
    max_obj_num = max(used_obj_nums) if used_obj_nums else 0
    
    # Find available object numbers (starting from max_obj_num + 1)
    free_obj_nums = [i for i in range(max_obj_num + 1, max_obj_num + 100) if i not in used_obj_nums]
    
    return used_obj_nums, max_obj_num, free_obj_nums


def get_object_number(obj):
    """
    Get the object number of a pikepdf object.
    
    Args:
        obj: A pikepdf object
        
    Returns:
        int: The object number, or 0 if not available
    """
    try:
        if hasattr(obj, 'objgen'):
            obj_num, gen = obj.objgen
            return obj_num
    except Exception:
        pass
    return 0


def embed_file(pdf, file_path, mime_type=None):
    """
    Embed a file into the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        file_path: Path to the file to embed
        mime_type: Optional MIME type for the embedded file
        
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


def extract_embedded_file(pdf, output_dir='.'):
    """
    Extract embedded files from the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        output_dir: Directory to save extracted files
        
    Returns:
        list: List of extracted file paths
    """
    extracted_files = []
    
    # Check if the PDF has embedded files
    if '/Names' in pdf.Root and '/EmbeddedFiles' in pdf.Root.Names:
        names_array = pdf.Root.Names.EmbeddedFiles.Names
        
        # Process the Names array (name, filespec pairs)
        for i in range(0, len(names_array), 2):
            if i + 1 < len(names_array):
                file_name = str(names_array[i])
                filespec = names_array[i + 1]
                
                # Get the embedded file stream
                if '/EF' in filespec and '/F' in filespec.EF:
                    embedded_file = filespec.EF.F
                    
                    # Extract the file data
                    file_data = embedded_file.read_bytes()
                    
                    # Save the file
                    output_path = os.path.join(output_dir, file_name)
                    with open(output_path, 'wb') as f:
                        f.write(file_data)
                    
                    extracted_files.append(output_path)
                    print(f"Extracted: {file_name} -> {output_path}")
    
    if not extracted_files:
        print("No embedded files found in the PDF.")
    
    return extracted_files


def verify_embedded_file(pdf, file_name):
    """
    Verify that a file is embedded in the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        file_name: Name of the file to verify
        
    Returns:
        bool: True if the file is embedded, False otherwise
    """
    if '/Names' in pdf.Root and '/EmbeddedFiles' in pdf.Root.Names:
        names_array = pdf.Root.Names.EmbeddedFiles.Names
        
        # Process the Names array (name, filespec pairs)
        for i in range(0, len(names_array), 2):
            if i + 1 < len(names_array):
                name = str(names_array[i])
                if name == file_name:
                    return True
    
    return False


def modify_object_numbers_with_qpdf(input_pdf, output_pdf, obj_map):
    """
    Use qpdf command-line tool to modify object numbers in a PDF.
    
    Args:
        input_pdf: Path to the input PDF
        output_pdf: Path to the output PDF
        obj_map: Dictionary mapping original object numbers to desired object numbers
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary file for the qpdf JSON operations
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_file = f.name
            
            # Create the JSON operations for qpdf
            operations = []
            for orig_obj, new_obj in obj_map.items():
                operations.append({
                    "op": "copy-object",
                    "from": orig_obj,
                    "to": new_obj
                })
            
            # Write the operations to the JSON file
            import json
            json.dump(operations, f)
        
        # Run qpdf with the JSON operations
        cmd = [
            "qpdf", 
            "--json-operations", json_file,
            input_pdf,
            output_pdf
        ]
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode != 0:
            print(f"Error running qpdf: {result.stderr}")
            return False
        
        # Clean up the temporary file
        os.unlink(json_file)
        
        return True
    except Exception as e:
        print(f"Error modifying object numbers: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Embed a file into a PDF with custom object numbers')
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
    
    # Check if the input PDF exists
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input PDF file '{args.input_pdf}' does not exist.")
        return 1
    
    # Create output directory if it doesn't exist
    if args.extract and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Open the PDF
    try:
        with Pdf.open(args.input_pdf) as pdf:
            # Analyze the PDF objects
            used_obj_nums, max_obj_num, free_obj_nums = analyze_pdf_objects(pdf)
            
            # Print PDF information
            print(f"PDF Version: {pdf.pdf_version}")
            print(f"Number of Pages: {len(pdf.pages)}")
            print(f"Total objects: {len(used_obj_nums)}")
            print(f"Maximum object number: {max_obj_num}")
            print(f"Available free object numbers: {free_obj_nums[:10]}...")
            
            # If analyze-only, print detailed object information
            if args.analyze_only:
                print("\nDetailed object information:")
                for obj_num in sorted(used_obj_nums):
                    obj = pdf.get_object(obj_num, 0)
                    print(f"Object {obj_num} (Generation 0): {type(obj).__name__}")
                return 0
            
            # If extract, extract embedded files
            if args.extract:
                print("\nExtracting embedded files...")
                extract_embedded_file(pdf, args.output_dir)
                return 0
            
            # Check if file_to_embed and output_pdf are provided
            if args.file_to_embed is None or args.output_pdf is None:
                print("Error: Both file_to_embed and output_pdf must be provided for embedding.")
                return 1
            
            # Check if the file to embed exists
            if not os.path.exists(args.file_to_embed):
                print(f"Error: File to embed '{args.file_to_embed}' does not exist.")
                return 1
            
            # Create a temporary file for the intermediate PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_pdf_path = temp_file.name
            
            # Embed the file
            print(f"\nEmbedding file: {args.file_to_embed}")
            embedded_file, filespec = embed_file(pdf, args.file_to_embed, args.mime_type)
            
            # Get the assigned object numbers
            embedded_file_num = get_object_number(embedded_file)
            filespec_num = get_object_number(filespec)
            
            print(f"Original embedded file object number: {embedded_file_num}")
            print(f"Original file specification object number: {filespec_num}")
            
            # Save the intermediate PDF
            pdf.save(temp_pdf_path)
            
            # Check if custom object numbers are requested
            if args.obj_num is not None or args.filespec_obj_num is not None:
                # Create object mapping
                obj_map = {}
                
                if args.obj_num is not None and embedded_file_num != 0:
                    obj_map[embedded_file_num] = args.obj_num
                
                if args.filespec_obj_num is not None and filespec_num != 0:
                    obj_map[filespec_num] = args.filespec_obj_num
                
                if obj_map:
                    print(f"Attempting to modify object numbers using qpdf: {obj_map}")
                    
                    # Try to modify object numbers using qpdf
                    success = modify_object_numbers_with_qpdf(temp_pdf_path, args.output_pdf, obj_map)
                    
                    if success:
                        print("Successfully modified object numbers.")
                        
                        # Verify the changes
                        with Pdf.open(args.output_pdf) as modified_pdf:
                            print("\nVerifying embedded file...")
                            file_name = os.path.basename(args.file_to_embed)
                            if verify_embedded_file(modified_pdf, file_name):
                                print(f"Verification successful: Found embedded file '{file_name}'")
                            else:
                                print(f"Verification failed: Could not find embedded file '{file_name}'")
                        
                        # Clean up the temporary file
                        os.unlink(temp_pdf_path)
                        return 0
                    else:
                        print("Failed to modify object numbers. Using original PDF.")
            
            # If we get here, either no custom object numbers were requested or the modification failed
            # Save the original PDF to the output file
            pdf.save(args.output_pdf)
            print(f"Modified PDF saved to: {args.output_pdf}")
            
            # Verify the embedding
            print("\nVerifying embedded file...")
            file_name = os.path.basename(args.file_to_embed)
            if verify_embedded_file(pdf, file_name):
                print(f"Verification successful: Found embedded file '{file_name}'")
            else:
                print(f"Verification failed: Could not find embedded file '{file_name}'")
            
            # Clean up the temporary file if it exists
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            
            return 0
    
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

