# MCP Tools Reference

## Confluence MCP Tools

- `list_spaces` — List accessible Confluence spaces.
- `get_space_info` — Retrieve detailed information about a specific space.
- `search_content` — Search for content using flexible filters (space, title, text, author, dates).
- `get_content_details` — Get comprehensive details for a specific content item, including body and attachments.
- `get_content_by_title` — Find content by exact title within a space.
- `list_attachments` — List attachments for a space or specific content (filterable by file type).
- `download_attachments` — Download attachments from a space or content to a local directory.
- `get_space_statistics` — Generate statistics for content within a space.
- `download_and_ingest_content_attachments` — Download attachments from a content item and ingest them into the vector DB.
- `download_and_ingest_space_attachments` — Download attachments across a space and ingest into the vector DB.
- `get_space_content_list` — Return a list of content items in a space (optionally include body).
- `create_page` — Create a new Confluence page in a space.
- `create_page_and_upload_file` — Create a page and upload a file to it in one operation.
- `upload_file_to_page_or_create` — Upload a file to a page, creating the page if it doesn't exist.
- `upload_file_to_content` — Upload a file to an existing content item as an attachment.
- `upload_file_to_page_by_title` — Upload a file by locating a page by title and attaching the file.
- `upload_multiple_files_to_content` — Upload multiple files to a content item as attachments.
- `upload_and_ingest_file_to_content` — Upload a file to content and ingest it into the vector DB (PDFs supported).
- `upload_and_ingest_file_to_page_by_title` — Upload to a page found by title and ingest into the vector DB.
- `create_page_and_upload_and_ingest_file` — Create a page, upload a file to it, and ingest the file into the vector DB.
- `upload_and_ingest_file_to_page_or_create` — Upload and ingest a file to a page, creating the page if necessary.

## Jira MCP Tools

- `list_projects` — List accessible Jira projects.
- `get_project_info` — Retrieve detailed project information.
- `search_issues` — Search for issues using filters (project, type, status, assignee, priority, text).
- `get_issue_details` — Get full issue details including comments, changelog, and attachments.
- `list_attachments` — List attachments for a project or a specific issue (filterable by file type).
- `download_attachments` — Download attachments from an issue or project to a local directory.
- `get_issue_statistics` — Generate statistics across issues in a project.
- `download_and_ingest_issue_attachments` — Download attachments from an issue and ingest into the vector DB.
- `download_and_ingest_project_attachments` — Download attachments across a project and ingest into the vector DB.
- `create_issue` — Create a new issue in a project with options for type, priority, assignee, and parent.
- `create_issue_and_upload_file` — Create an issue and upload a file to it in one operation.
- `upload_file_to_issue_or_create` — Upload a file to an issue, or create the issue first if it doesn't exist.
- `create_issue_and_upload_and_ingest_file` — Create an issue, upload a file to it, and ingest the file into the vector DB.
- `upload_and_ingest_file_to_issue_or_create` — Upload and ingest to an issue, auto-creating the issue if needed.
- `upload_file_to_issue` — Upload a single file as an attachment to an existing issue.
- `upload_multiple_files_to_issue` — Upload multiple files as attachments to an existing issue.
- `upload_and_ingest_file_to_issue` — Upload a file to an issue and ingest it into the vector DB (PDFs supported).

---


