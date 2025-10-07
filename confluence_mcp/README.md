# Confluence MCP Tools

This package provides Model Context Protocol (MCP) tools for interacting with Confluence, similar to the Jira MCP tools. It includes comprehensive functionality for searching, downloading, and ingesting Confluence content and attachments.

## Features

### Core Operations
- **Space Management**: List and get detailed information about Confluence spaces
- **Content Search**: Flexible content search with filters for type, author, dates, and text
- **Content Retrieval**: Get detailed content information by ID or title
- **Attachment Management**: List, download, and organize attachments from spaces or specific content
- **Statistics Generation**: Comprehensive analytics for spaces and content
- **Document Ingestion**: Automatic download and ingestion of attachments into vector database

### Available Tools

1. **list_spaces()** - List all accessible Confluence spaces
2. **get_space_info()** - Get detailed information about a specific space
3. **search_content()** - Search content with flexible filters
4. **get_content_details()** - Get comprehensive details for specific content
5. **get_content_by_title()** - Find content by exact title within a space
6. **list_attachments()** - List attachments in spaces or content
7. **download_attachments()** - Download attachments with organization options
8. **get_space_statistics()** - Generate comprehensive space analytics
9. **download_and_ingest_content_attachments()** - Download and ingest content attachments
10. **download_and_ingest_space_attachments()** - Download and ingest all space attachments
11. **get_space_content_list()** - Get organized list of content from a space

## Setup

### 1. Environment Variables
Create a `.env` file with your Confluence credentials:

```bash
CONFLUENCE_URL=your-confluence-instance.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-api-token
OPENAI_API_KEY=your-openai-api-key
```

### 2. Dependencies
The tools require the same dependencies as the Jira MCP tools:

```bash
pip install fastmcp langchain-openai langchain-mcp-adapters langgraph python-dotenv aiohttp requests
```

### 3. Running the MCP Server
Start the Confluence MCP server:

```bash
python confluence_mcp/confluence_mcp.py
```

The server will run on `http://localhost:8001/mcp`

### 4. Running the LangGraph Agent
In a separate terminal, run the agent:

```bash
python confluence_mcp/confluence_agent.py
```

## Usage Examples

### Basic Content Search
```python
# Search for pages in a specific space
await search_content(
    space_key="TEAM",
    content_type="page",
    title_search="meeting",
    limit=20
)

# Search by author and date range
await search_content(
    space_key="DOCS",
    author="john.doe",
    created_after="2024-01-01",
    modified_after="2024-06-01"
)
```

### Attachment Operations
```python
# List all PDF attachments in a space
await list_attachments(
    space_key="TEAM",
    file_types=["pdf"]
)

# Download all attachments from specific content
await download_attachments(
    content_id="123456789",
    file_types=["pdf", "docx", "pptx"]
)
```

### Document Ingestion
```python
# Download and ingest all PDF attachments from a space
await download_and_ingest_space_attachments(
    space_key="DOCS",
    file_types=["pdf"],
    company_name="My Company",
    cleanup_after_ingest=True
)

# Download and ingest attachments from specific content
await download_and_ingest_content_attachments(
    content_id="123456789",
    file_types=["pdf"],
    cleanup_after_ingest=True
)
```

### Analytics
```python
# Get comprehensive space statistics
await get_space_statistics(
    space_key="TEAM",
    max_content=500
)
```

## Architecture

### Confluence Client
- Handles Confluence REST API authentication and requests
- Supports both Cloud and Server instances
- Implements proper error handling and rate limiting

### Confluence Utils
- Content filtering and CQL query building
- Attachment processing and organization
- Statistics generation and data analysis
- File download management

### MCP Tools Integration
- FastMCP 2.0 framework implementation
- Streamable HTTP transport for real-time communication
- LangGraph agent integration for complex workflows

## Content Query Language (CQL)

The tools automatically build CQL queries from your filters. Examples of generated queries:

```sql
-- Search pages in TEAM space with "project" in title
space = "TEAM" AND type = "page" AND title ~ "project"

-- Search content by author and date
space = "DOCS" AND creator = "john.doe" AND created >= "2024-01-01"

-- Search with text content
space = "TEAM" AND text ~ "quarterly report" AND type = "page"
```

## File Organization

Downloaded files are organized as:
```
confluence_attachments/
├── TEAM/                    # Space key
│   ├── Project Overview/    # Content title (sanitized)
│   │   ├── document1.pdf
│   │   └── presentation.pptx
│   └── Meeting Notes/
│       └── agenda.docx
└── DOCS/
    └── API Documentation/
        └── api-guide.pdf
```

## Integration with Vector Database

The ingestion tools automatically process PDF files using your existing PDF processor (`utility.pdf_processor1`) and add them to your vector database with proper metadata including:

- Source: Confluence
- Space key and name
- Content title and ID
- Author information
- Creation and modification dates
- File metadata

## Error Handling

The tools include comprehensive error handling for:
- Authentication failures
- Network connectivity issues
- Invalid space keys or content IDs
- Missing attachments or download failures
- PDF processing errors
- File system operations

## Comparison with Jira MCP Tools

| Feature | Jira MCP | Confluence MCP |
|---------|----------|----------------|
| Authentication | ✅ Basic Auth | ✅ Basic Auth |
| Search | JQL | CQL |
| Content Types | Issues | Pages, Blog posts |
| Attachments | ✅ | ✅ |
| Statistics | Issue analytics | Content analytics |
| Ingestion | ✅ | ✅ |
| Agent Integration | ✅ | ✅ |

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify CONFLUENCE_URL format (without /wiki)
   - Check API token permissions
   - Ensure email address is correct

2. **No Content Found**
   - Verify space key exists and is accessible
   - Check user permissions for the space
   - Try broader search filters

3. **Download Failures**
   - Check network connectivity
   - Verify attachment permissions
   - Ensure sufficient disk space

4. **Ingestion Issues**
   - Verify PDF processor is working
   - Check file formats (only PDF supported)
   - Review vector database connection

### Logging
The tools provide detailed logging for debugging:
- Download progress and results
- Processing status and errors
- File organization and cleanup
- Ingestion success/failure messages

## Extending the Tools

You can extend the Confluence MCP tools by:

1. Adding new tools to `confluence_mcp.py`
2. Extending the `ConfluenceUtils` class
3. Adding new content types or formats
4. Implementing custom filtering logic
5. Adding integration with other services

## Security Considerations

- API tokens are transmitted securely using HTTPS
- Downloaded files are stored locally temporarily
- Cleanup options remove files after processing
- No sensitive data is logged
- Authentication headers are properly managed

## Performance

- Concurrent download support for multiple attachments
- Efficient CQL queries with proper limits
- Streaming file downloads for large attachments
- Memory-efficient PDF processing
- Configurable batch sizes for bulk operations