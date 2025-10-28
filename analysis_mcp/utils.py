"""
Utility functions for Analysis operations
Handles table extraction, data processing, and Excel generation
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import unstructured_client
from unstructured_client.models import shared, errors, operations
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table as RLTable, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile
from datetime import datetime


async def partition_file_via_api(filename: str, api_key: str) -> List[Dict]:
    """
    Partition a file using the Unstructured API.
    
    Args:
        filename: Path to the file to partition
        api_key: Unstructured API key
        
    Returns:
        List of elements from the partitioned file
    """
    try:
        client = unstructured_client.UnstructuredClient(api_key_auth=api_key)
        
        with open(filename, "rb") as f:
            files = shared.Files(
                content=f.read(),
                file_name=os.path.basename(filename),
            )

        req = operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy=shared.Strategy.HI_RES,
                infer_table_structure=True,
                split_pdf_page=True,
                split_pdf_allow_failed=True,
                split_pdf_concurrency_level=15,
            )
        )

        res = await client.general.partition_async(request=req)
        return res.elements

    except errors.UnstructuredClientError as e:
        raise Exception(f"Error partitioning {filename}: {e.message}")


def html_table_to_rows(html: str) -> List[List[str]]:
    """
    Convert HTML <table> to list of row lists with proper alignment.
    
    Args:
        html: HTML string containing a table
        
    Returns:
        List of rows, where each row is a list of cell values
    """
    rows = []
    if not html:
        return rows

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return rows

    for tr in table.find_all("tr"):
        row = []
        for cell in tr.find_all(["td", "th"]):
            colspan = int(cell.get("colspan", 1))
            text = cell.get_text(strip=True)
            row.extend([text] * colspan)
        rows.append(row)

    # Normalize to max length
    max_len = max(len(r) for r in rows) if rows else 0
    for r in rows:
        if len(r) < max_len:
            r.extend([""] * (max_len - len(r)))

    return rows


async def extract_tables_from_file(filename: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Extract all tables from a single file.
    
    Args:
        filename: Path to the file to extract tables from
        api_key: Unstructured API key
        
    Returns:
        List of table dictionaries with metadata and row data
    """
    elements = await partition_file_via_api(filename, api_key)

    tables = []
    table_index = 1

    for el in elements or []:
        if el.get("type", "").lower() == "table" or el.get("category", "").lower() == "table":
            metadata = el.get("metadata", {})
            html = metadata.get("text_as_html")
            rows = html_table_to_rows(html)
            
            if rows:
                tables.append({
                    "file": os.path.basename(filename),
                    "page_number": metadata.get("page_number"),
                    "table_index": table_index,
                    "rows": rows
                })
                table_index += 1
    
    return tables


def load_filenames_in_directory(input_dir: str, include_subdirs: bool = True) -> List[str]:
    """
    Load all non-JSON filenames from a directory.
    
    Args:
        input_dir: Directory path to scan
        include_subdirs: Whether to include subdirectories
        
    Returns:
        List of file paths
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Directory not found: {input_dir}")
    
    if not os.path.isdir(input_dir):
        raise ValueError(f"Path is not a directory: {input_dir}")
    
    filenames = []
    
    if include_subdirs:
        for root, _, files in os.walk(input_dir):
            for file in files:
                if not file.endswith('.json'):
                    filenames.append(os.path.join(root, file))
    else:
        for file in os.listdir(input_dir):
            file_path = os.path.join(input_dir, file)
            if os.path.isfile(file_path) and not file.endswith('.json'):
                filenames.append(file_path)
    
    return filenames


async def extract_tables_to_excel(
    input_path: str,
    output_file: str,
    api_key: str,
    include_subdirs: bool = True
) -> Dict[str, Any]:
    """
    Extract tables from PDF(s) and save to Excel file.
    
    Args:
        input_path: Path to a file or directory
        output_file: Output Excel file path
        api_key: Unstructured API key
        include_subdirs: Whether to include subdirectories (for directory input)
        
    Returns:
        Dictionary with extraction results
    """
    # Determine if input is a file or directory
    if os.path.isfile(input_path):
        filenames = [input_path]
    elif os.path.isdir(input_path):
        filenames = load_filenames_in_directory(input_path, include_subdirs)
    else:
        raise ValueError(f"Input path does not exist: {input_path}")

    if not filenames:
        return {
            "success": False,
            "error": "No files found to process"
        }

    # Extract all tables from all files
    all_tables = []
    processed_files = []
    failed_files = []
    
    for filename in filenames:
        try:
            print(f"Processing {filename}...")
            tables = await extract_tables_from_file(filename, api_key)
            all_tables.extend(tables)
            processed_files.append(filename)
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            failed_files.append({"file": filename, "error": str(e)})

    if not all_tables:
        return {
            "success": False,
            "error": "No tables extracted from any files",
            "processed_files": len(processed_files),
            "failed_files": failed_files
        }

    # Create Excel file with all tables as separate sheets
    sheets_created = []
    sheets_failed = []
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for table in all_tables:
            # Create DataFrame from rows
            df = pd.DataFrame(table["rows"])
            
            # Create sheet name: filename_pageX_tableY
            file_base = os.path.splitext(table["file"])[0]
            sheet_name = f"{file_base}_p{table['page_number']}_t{table['table_index']}"
            
            # Excel sheet names max 31 chars
            sheet_name = sheet_name[:31]
            
            # Write to Excel
            try:
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                sheets_created.append(sheet_name)
            except Exception as e:
                sheets_failed.append({"sheet": sheet_name, "error": str(e)})

    return {
        "success": True,
        "output_file": output_file,
        "total_files_processed": len(processed_files),
        "total_tables_extracted": len(all_tables),
        "sheets_created": len(sheets_created),
        "sheets_failed": len(sheets_failed),
        "failed_files": failed_files,
        "processed_files": processed_files
    }


# ============================================================================
# CHART GENERATION AND PDF REPORTING FUNCTIONS
# ============================================================================

def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze a DataFrame to determine appropriate chart types and insights.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "shape": df.shape,
        "columns": list(df.columns),
        "numeric_columns": [],
        "categorical_columns": [],
        "datetime_columns": [],
        "has_numeric": False,
        "has_categorical": False
    }
    
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            analysis["numeric_columns"].append(col)
            analysis["has_numeric"] = True
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            analysis["datetime_columns"].append(col)
        else:
            analysis["categorical_columns"].append(col)
            analysis["has_categorical"] = True
    
    return analysis


def generate_chart_from_dataframe(
    df: pd.DataFrame,
    chart_type: str = "auto",
    title: str = "Data Visualization",
    figsize: tuple = (10, 6)
) -> Optional[str]:
    """
    Generate a chart from DataFrame and save to temp file.
    
    Args:
        df: DataFrame to visualize
        chart_type: Type of chart (auto, bar, line, pie, scatter, heatmap)
        title: Chart title
        figsize: Figure size
        
    Returns:
        Path to saved chart image or None if generation failed
    """
    try:
        # Set style
        sns.set_style("whitegrid")
        plt.figure(figsize=figsize)
        
        # Analyze data
        analysis = analyze_dataframe(df)
        
        # Auto-detect chart type if needed
        if chart_type == "auto":
            if len(analysis["numeric_columns"]) >= 2:
                chart_type = "scatter"
            elif len(analysis["numeric_columns"]) == 1 and len(analysis["categorical_columns"]) >= 1:
                chart_type = "bar"
            elif len(analysis["numeric_columns"]) >= 1:
                chart_type = "line"
            else:
                chart_type = "bar"
        
        # Generate appropriate chart
        if chart_type == "bar":
            _generate_bar_chart(df, analysis, title)
        elif chart_type == "line":
            _generate_line_chart(df, analysis, title)
        elif chart_type == "pie":
            _generate_pie_chart(df, analysis, title)
        elif chart_type == "scatter":
            _generate_scatter_chart(df, analysis, title)
        elif chart_type == "heatmap":
            _generate_heatmap(df, analysis, title)
        else:
            # Default to simple visualization
            _generate_bar_chart(df, analysis, title)
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.tight_layout()
        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
        
    except Exception as e:
        print(f"Error generating chart: {str(e)}")
        plt.close()
        return None


def _generate_bar_chart(df: pd.DataFrame, analysis: Dict, title: str):
    """Generate a bar chart."""
    if analysis["numeric_columns"] and analysis["categorical_columns"]:
        # Use first categorical and first numeric column
        x_col = analysis["categorical_columns"][0]
        y_col = analysis["numeric_columns"][0]
        
        # Limit to top 15 categories if too many
        data = df.groupby(x_col)[y_col].sum().nlargest(15)
        data.plot(kind='bar', color=sns.color_palette("husl", len(data)))
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.xticks(rotation=45, ha='right')
    else:
        # Simple value counts
        df.iloc[:, 0].value_counts().head(15).plot(kind='bar', color=sns.color_palette("husl", 15))
        plt.xlabel(df.columns[0])
        plt.ylabel('Count')
        plt.xticks(rotation=45, ha='right')
    
    plt.title(title, fontsize=14, fontweight='bold')


def _generate_line_chart(df: pd.DataFrame, analysis: Dict, title: str):
    """Generate a line chart."""
    if analysis["numeric_columns"]:
        for i, col in enumerate(analysis["numeric_columns"][:5]):  # Max 5 lines
            plt.plot(df.index, df[col], marker='o', label=col, linewidth=2)
        plt.xlabel('Index')
        plt.ylabel('Value')
        plt.legend()
    else:
        plt.plot(df.iloc[:, 0].values, marker='o', linewidth=2)
        plt.xlabel('Index')
        plt.ylabel(df.columns[0])
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)


def _generate_pie_chart(df: pd.DataFrame, analysis: Dict, title: str):
    """Generate a pie chart."""
    if analysis["categorical_columns"]:
        col = analysis["categorical_columns"][0]
        data = df[col].value_counts().head(10)
    else:
        data = df.iloc[:, 0].value_counts().head(10)
    
    colors = sns.color_palette("husl", len(data))
    plt.pie(data.values, labels=data.index, autopct='%1.1f%%', colors=colors, startangle=90)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.axis('equal')


def _generate_scatter_chart(df: pd.DataFrame, analysis: Dict, title: str):
    """Generate a scatter chart."""
    if len(analysis["numeric_columns"]) >= 2:
        x_col = analysis["numeric_columns"][0]
        y_col = analysis["numeric_columns"][1]
        plt.scatter(df[x_col], df[y_col], alpha=0.6, s=100, c=sns.color_palette("husl", 1)[0])
        plt.xlabel(x_col)
        plt.ylabel(y_col)
    else:
        plt.scatter(df.index, df.iloc[:, 0], alpha=0.6, s=100)
        plt.xlabel('Index')
        plt.ylabel(df.columns[0])
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)


def _generate_heatmap(df: pd.DataFrame, analysis: Dict, title: str):
    """Generate a correlation heatmap."""
    if len(analysis["numeric_columns"]) >= 2:
        numeric_df = df[analysis["numeric_columns"]]
        corr = numeric_df.corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, 
                   square=True, linewidths=1, cbar_kws={"shrink": 0.8})
    else:
        # Show data as heatmap
        numeric_df = df.select_dtypes(include=[float, int]).head(20)
        sns.heatmap(numeric_df, cmap='YlOrRd', linewidths=0.5)
    
    plt.title(title, fontsize=14, fontweight='bold')


def generate_pdf_report_from_excel(
    excel_file: str,
    output_pdf: str,
    title: str = "Data Analysis Report",
    include_charts: bool = True,
    chart_types: Optional[Dict[str, str]] = None,
    max_sheets: int = 10
) -> Dict[str, Any]:
    """
    Generate a PDF report with charts from an Excel file.
    
    Args:
        excel_file: Path to Excel file
        output_pdf: Output PDF file path
        title: Report title
        include_charts: Whether to generate charts
        chart_types: Dict mapping sheet names to chart types (auto, bar, line, pie, scatter, heatmap)
        max_sheets: Maximum number of sheets to process
        
    Returns:
        Dictionary with generation results
    """
    try:
        # Read Excel file
        xl_file = pd.ExcelFile(excel_file)
        sheet_names = xl_file.sheet_names[:max_sheets]
        
        if not sheet_names:
            return {
                "success": False,
                "error": "No sheets found in Excel file"
            }
        
        # Create PDF
        doc = SimpleDocTemplate(output_pdf, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2e5090'),
            spaceAfter=12,
            spaceBefore=20
        )
        
        description_style = ParagraphStyle(
            'Description',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=10,
            leftIndent=20
        )
        
        # Add title page
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                              styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Data Source: {os.path.basename(excel_file)}", description_style))
        story.append(Paragraph(f"Total Sheets Analyzed: {len(sheet_names)}", description_style))
        story.append(PageBreak())
        
        # Process each sheet
        charts_generated = []
        charts_failed = []
        temp_files = []
        
        for idx, sheet_name in enumerate(sheet_names, 1):
            try:
                # Read sheet
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Add sheet heading
                story.append(Paragraph(f"{idx}. {sheet_name}", heading_style))
                story.append(Spacer(1, 0.1*inch))
                
                # Add description
                rows, cols = df.shape
                description = f"This dataset contains {rows} rows and {cols} columns. "
                
                # Analyze data types
                numeric_cols = df.select_dtypes(include=[float, int]).columns.tolist()
                if numeric_cols:
                    description += f"Numeric columns: {', '.join(numeric_cols[:5])}{'...' if len(numeric_cols) > 5 else ''}. "
                
                story.append(Paragraph(description, description_style))
                story.append(Spacer(1, 0.15*inch))
                
                # Add data summary table
                if rows > 0 and cols > 0:
                    # Show first few rows
                    preview_df = df.head(5)
                    table_data = [preview_df.columns.tolist()] + preview_df.values.tolist()
                    
                    # Truncate long values
                    table_data = [[str(cell)[:30] + ('...' if len(str(cell)) > 30 else '') 
                                  for cell in row] for row in table_data]
                    
                    t = RLTable(table_data, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 0.2*inch))
                
                # Generate chart if requested
                if include_charts and rows > 0 and cols > 0:
                    chart_type = chart_types.get(sheet_name, "auto") if chart_types else "auto"
                    chart_file = generate_chart_from_dataframe(
                        df,
                        chart_type=chart_type,
                        title=f"Visualization: {sheet_name}",
                        figsize=(10, 6)
                    )
                    
                    if chart_file:
                        temp_files.append(chart_file)
                        img = Image(chart_file, width=6*inch, height=3.6*inch)
                        story.append(Paragraph("Data Visualization:", description_style))
                        story.append(Spacer(1, 0.1*inch))
                        story.append(img)
                        charts_generated.append(sheet_name)
                    else:
                        charts_failed.append({"sheet": sheet_name, "error": "Chart generation failed"})
                
                # Add page break after each sheet
                if idx < len(sheet_names):
                    story.append(PageBreak())
                    
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {str(e)}")
                charts_failed.append({"sheet": sheet_name, "error": str(e)})
        
        # Build PDF
        doc.build(story)
        
        # Clean up temp files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        
        return {
            "success": True,
            "output_pdf": output_pdf,
            "sheets_processed": len(sheet_names),
            "charts_generated": len(charts_generated),
            "charts_failed": len(charts_failed),
            "failed_charts": charts_failed
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
