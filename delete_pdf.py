#!/usr/bin/env python3
"""
Delete PDF Ingestion Script

Removes all documents associated with a PDF file from Qdrant vector stores.

Usage:
    python delete_pdf.py RIVIAN.pdf
    python delete_pdf.py "CLOUD WEB.pdf"
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qdrant_client import models
from vector_store.load_dbs import load_vector_database


def delete_pdf_from_qdrant(file_name: str) -> dict:
    """
    Delete all documents associated with a PDF file from Qdrant.
    
    Args:
        file_name: Name of the PDF file (e.g., "RIVIAN.pdf")
        
    Returns:
        dict: Deletion result with status and details
    """
    result = {
        "success": False,
        "file_name": file_name,
        "text_deleted": 0,
        "image_deleted": 0,
        "error": None
    }
    
    try:
        # Initialize database
        db_init = load_vector_database()
        
        # Get vector stores
        _, text_vectorstore, _ = db_init.get_text_retriever()
        image_vectorstore, _, _ = db_init.get_image_retriever()
        
        # Delete from text collection
        try:
            print(f"\n=== Deleting {file_name} from text collection ===")
            text_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.source_file",
                        match=models.MatchValue(value=file_name)
                    )
                ]
            )
            
            # Count matching points first
            count_response = text_vectorstore.client.count(
                collection_name=text_vectorstore.collection_name,
                count_filter=text_filter
            )
            text_count = count_response.count
            print(f"Found {text_count} text document(s) to delete")
            
            if text_count > 0:
                # Delete the points
                text_vectorstore.client.delete(
                    collection_name=text_vectorstore.collection_name,
                    points_selector=models.FilterSelector(filter=text_filter)
                )
                print(f"✓ Deleted {text_count} text document(s)")
                result["text_deleted"] = text_count
        except Exception as e:
            print(f"⚠ Error deleting from text collection: {e}")
        
        # Delete from image collection
        try:
            print(f"\n=== Deleting {file_name} from image collection ===")
            image_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.source_file",
                        match=models.MatchValue(value=file_name)
                    )
                ]
            )
            
            # Count matching points first
            count_response = image_vectorstore.client.count(
                collection_name=image_vectorstore.collection_name,
                count_filter=image_filter
            )
            image_count = count_response.count
            print(f"Found {image_count} image document(s) to delete")
            
            if image_count > 0:
                # Delete the points
                image_vectorstore.client.delete(
                    collection_name=image_vectorstore.collection_name,
                    points_selector=models.FilterSelector(filter=image_filter)
                )
                print(f"✓ Deleted {image_count} image document(s)")
                result["image_deleted"] = image_count
        except Exception as e:
            print(f"⚠ Error deleting from image collection: {e}")
        
        # Final status
        result["success"] = True
        total_deleted = result["text_deleted"] + result["image_deleted"]
        
        if total_deleted == 0:
            print(f"\n⚠ No documents found for {file_name}")
        else:
            print(f"\n✓ Successfully deleted {total_deleted} document(s)")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"\n✗ Error: {e}")
    
    return result


def format_result(result: dict) -> str:
    """Format the deletion result for display."""
    lines = [
        "\n" + "="*60,
        "PDF DELETION RESULT",
        "="*60,
        f"File: {result['file_name']}",
        f"Status: {'✓ SUCCESS' if result['success'] else '✗ FAILED'}",
        ""
    ]
    
    if result['error']:
        lines.append(f"Error: {result['error']}")
    else:
        lines.extend([
            "DELETION SUMMARY:",
            f"  - Text documents deleted: {result['text_deleted']}",
            f"  - Image documents deleted: {result['image_deleted']}",
            f"  - Total deleted: {result['text_deleted'] + result['image_deleted']}",
        ])
    
    lines.append("="*60 + "\n")
    return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python delete_pdf.py <pdf_file_name>")
        print("\nExample: python delete_pdf.py RIVIAN.pdf")
        print("         python delete_pdf.py \"CLOUD WEB.pdf\"")
        sys.exit(1)
    
    # Join all arguments to handle file names with spaces
    file_name = ' '.join(sys.argv[1:])
    
    # Ensure it ends with .pdf
    if not file_name.lower().endswith('.pdf'):
        file_name += '.pdf'
    
    print(f"Attempting to delete: {file_name}")
    result = delete_pdf_from_qdrant(file_name)
    
    # Display formatted result
    print(format_result(result))
    
    # Return appropriate exit code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
