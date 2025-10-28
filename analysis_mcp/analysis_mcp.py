"""
Analysis MCP Server
Provides MCP tools for document analysis, table extraction, and data processing
"""
import os
import json
import asyncio
from typing import Optional
from fastmcp import FastMCP
import sys
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from analysis_mcp.utils import (
    extract_tables_to_excel,
    load_filenames_in_directory,
    generate_pdf_report_from_excel
)

# Initialize FastMCP server
mcp = FastMCP("Analysis Tools")


# ============================================================================
# MCP TOOL 1: EXTRACT TABLES TO EXCEL
# ============================================================================

@mcp.tool()
async def extract_tables_from_pdf_to_excel(
    input_path: str,
    output_file: str,
    include_subdirs: bool = True
) -> str:
    """
    Extract all tables from PDF file(s) and save to an Excel file.
    Each table is saved as a separate sheet with format: filename_pageX_tableY
    
    Args:
        input_path: Path to a PDF file or directory containing PDFs
        output_file: Output Excel file path (e.g., "extracted_tables.xlsx")
        include_subdirs: Whether to include subdirectories when input is a directory
        
    Returns:
        JSON string with extraction results including file count, table count, and output path
    """
    try:
        # Get API key from environment
        api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not api_key:
            return json.dumps({
                "success": False,
                "error": "UNSTRUCTURED_API_KEY not found in environment variables"
            }, indent=2)
        
        # Validate input path
        if not os.path.exists(input_path):
            return json.dumps({
                "success": False,
                "error": f"Input path does not exist: {input_path}"
            }, indent=2)
        
        # Ensure output file has .xlsx extension
        if not output_file.endswith('.xlsx'):
            output_file = f"{output_file}.xlsx"
        
        # Extract tables and create Excel
        result = await extract_tables_to_excel(
            input_path=input_path,
            output_file=output_file,
            api_key=api_key,
            include_subdirs=include_subdirs
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# ============================================================================
# MCP TOOL 2: LIST FILES IN DIRECTORY (for analysis)
# ============================================================================

@mcp.tool()
def list_files_for_analysis(
    directory_path: str,
    include_subdirs: bool = True
) -> str:
    """
    List all non-JSON files in a directory that can be analyzed.
    
    Args:
        directory_path: Absolute path to the directory
        include_subdirs: Whether to search subdirectories
        
    Returns:
        JSON string with list of files available for analysis
    """
    try:
        files = load_filenames_in_directory(directory_path, include_subdirs)
        
        # Get file details
        file_details = []
        for file_path in files:
            file_size = os.path.getsize(file_path)
            file_details.append({
                "name": os.path.basename(file_path),
                "path": file_path,
                "size": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "extension": os.path.splitext(file_path)[1]
            })
        
        return json.dumps({
            "success": True,
            "directory": directory_path,
            "file_count": len(file_details),
            "files": file_details
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# ============================================================================
# MCP TOOL 3: GENERATE CHARTS FROM EXCEL TO PDF
# ============================================================================

@mcp.tool()
async def generate_charts_from_excel_to_pdf(
    excel_file: str,
    output_pdf: str,
    report_title: str = "Data Analysis Report",
    include_charts: bool = True,
    max_sheets: int = 10
) -> str:
    """
    Generate a comprehensive PDF report with charts and visualizations from an Excel file.
    The PDF includes proper descriptions, headings, data previews, and visualizations for each sheet.
    
    Args:
        excel_file: Path to the Excel file to analyze
        output_pdf: Output PDF file path (e.g., "analysis_report.pdf")
        report_title: Title for the PDF report
        include_charts: Whether to include charts and visualizations
        max_sheets: Maximum number of sheets to process (default: 10)
        
    Returns:
        JSON string with generation results including sheet count, charts generated, and output path
    """
    try:
        # Validate Excel file
        if not os.path.exists(excel_file):
            return json.dumps({
                "success": False,
                "error": f"Excel file does not exist: {excel_file}"
            }, indent=2)
        
        if not excel_file.endswith('.xlsx') and not excel_file.endswith('.xls'):
            return json.dumps({
                "success": False,
                "error": f"File must be an Excel file (.xlsx or .xls): {excel_file}"
            }, indent=2)
        
        # Ensure output file has .pdf extension
        if not output_pdf.endswith('.pdf'):
            output_pdf = f"{output_pdf}.pdf"
        
        # Generate PDF report
        result = generate_pdf_report_from_excel(
            excel_file=excel_file,
            output_pdf=output_pdf,
            title=report_title,
            include_charts=include_charts,
            max_sheets=max_sheets
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# ============================================================================
# MCP TOOL 4: EXTRACT TABLES AND GENERATE PDF REPORT (Combined)
# ============================================================================

@mcp.tool()
async def extract_tables_and_generate_report(
    input_path: str,
    output_excel: str = "extracted_tables.xlsx",
    output_pdf: str = "analysis_report.pdf",
    report_title: str = "Table Extraction and Analysis Report",
    include_subdirs: bool = True,
    include_charts: bool = True
) -> str:
    """
    Complete workflow: Extract tables from PDF(s) to Excel, then generate a PDF report with charts.
    This is a convenience tool that combines table extraction and chart generation.
    
    Args:
        input_path: Path to a PDF file or directory containing PDFs
        output_excel: Output Excel file path (default: "extracted_tables.xlsx")
        output_pdf: Output PDF report file path (default: "analysis_report.pdf")
        report_title: Title for the PDF report
        include_subdirs: Whether to include subdirectories when input is a directory
        include_charts: Whether to include charts in the PDF report
        
    Returns:
        JSON string with combined results from both extraction and report generation
    """
    try:
        # Get API key from environment
        api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not api_key:
            return json.dumps({
                "success": False,
                "error": "UNSTRUCTURED_API_KEY not found in environment variables"
            }, indent=2)
        
        # Validate input path
        if not os.path.exists(input_path):
            return json.dumps({
                "success": False,
                "error": f"Input path does not exist: {input_path}"
            }, indent=2)
        
        # Ensure output files have correct extensions
        if not output_excel.endswith('.xlsx'):
            output_excel = f"{output_excel}.xlsx"
        if not output_pdf.endswith('.pdf'):
            output_pdf = f"{output_pdf}.pdf"
        
        # Step 1: Extract tables to Excel
        extraction_result = await extract_tables_to_excel(
            input_path=input_path,
            output_file=output_excel,
            api_key=api_key,
            include_subdirs=include_subdirs
        )
        
        if not extraction_result.get("success"):
            return json.dumps(extraction_result, indent=2)
        
        # Step 2: Generate PDF report from Excel
        report_result = generate_pdf_report_from_excel(
            excel_file=output_excel,
            output_pdf=output_pdf,
            title=report_title,
            include_charts=include_charts
        )
        
        # Combine results
        combined_result = {
            "success": True,
            "extraction": extraction_result,
            "report": report_result,
            "output_excel": output_excel,
            "output_pdf": output_pdf
        }
        
        return json.dumps(combined_result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# ============================================================================
# Main entry point for the MCP server
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport='streamable-http',port=8007)
