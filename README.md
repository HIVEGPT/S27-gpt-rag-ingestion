# GPT-RAG - Data Ingestion Component

Part of [GPT-RAG](https://github.com/Azure/gpt-rag)

## Table of Contents

1. [**GPT-RAG - Data Ingestion Component**](#gpt-rag---data-ingestion-component)
   - [1.1 Document Ingestion Process](#document-ingestion-process)
   - [1.2 Document Chunking Process](#document-chunking-process)
   - [1.3 NL2SQL Data Ingestion](#nl2sql-ingestion-process)
   - [1.4 Sharepoint Indexing](#sharepoint-indexing)   
2. [**How-to: Developer**](#how-to-developer)
   - [2.1 Redeploying the Ingestion Component](#redeploying-the-ingestion-component)
   - [2.2 Running Locally](#running-locally)
   - [2.3 Configuring Sharepoint Connector](#configuring-sharepoint-connector)      
3. [**How-to: User**](#how-to-user)
   - [3.1 Uploading Documents for Ingestion](#uploading-documents-for-ingestion)
   - [3.2 Reindexing Documents in AI Search](#reindexing-documents-in-ai-search)
4. [**Reference**](#reference)
   - [4.1 Supported Formats and Chunkers](#supported-formats-and-chunkers)
   - [4.2 External Resources](#external-resources)

## Concepts

### Document Ingestion Process

The diagram below provides an overview of the document ingestion pipeline, which handles various document types, preparing them for indexing and retrieval.

![Document Ingestion Pipeline](media/document_ingestion_pipeline.png)  
*Document Ingestion Pipeline*

**Workflow**

1) The `ragindex-indexer-chunk-documents` indexer reads new documents from the `documents` blob container.

2) For each document, it calls the `document-chunking` function app to segment the content into chunks and generate embeddings using the ADA model.

3) Finally, each chunk is indexed in the AI Search Index.

### Document Chunking Process

The `document_chunking` function breaks documents into smaller segments called chunks.

When a document is submitted, the system identifies its file type and selects the appropriate chunker to divide it into chunks suitable for that specific type.

- **For `.pdf` files**, the system uses the [DocAnalysisChunker](chunking/chunkers/doc_analysis_chunker.py) with the Document Intelligence API, which extracts structured elements, like tables and sections, converting them into Markdown. LangChain splitters then segment the content based on sections. When Document Intelligence API 4.0 is enabled, `.docx` and `.pptx` files are processed with this chunker as well.

- **For image files** such as `.bmp`, `.png`, `.jpeg`, and `.tiff`, the [DocAnalysisChunker](chunking/chunkers/doc_analysis_chunker.py) performs Optical Character Recognition (OCR) to extract text before chunking.

- **For specialized formats**, specific chunkers are applied:
    - `.vtt` files (video transcriptions) are handled by the [TranscriptionChunker](chunking/chunkers/transcription_chunker.py), chunking content by time codes.
    - `.xlsx` files (spreadsheets) are processed by the [SpreadsheetChunker](chunking/chunkers/spreadsheet_chunker.py), chunking by rows or sheets.

- **For text-based files** like `.txt`, `.md`, `.json`, and `.csv`, the [LangChainChunker](chunking/chunkers/langchain_chunker.py) uses LangChain splitters to divide the content by paragraphs or sections.

This setup ensures each document is processed by the most suitable chunker, leading to efficient and accurate chunking.

> **Important:** The file extension determines the choice of chunker as outlined above.

**Customization**

The chunking process is customizable. You can modify existing chunkers or create new ones to meet specific data processing needs, optimizing the pipeline.

### NL2SQL Ingestion Process

If you are using the **few-shot** or **few-shot scaled** NL2SQL strategies in your orchestration component, you may want to index NL2SQL content for use during the retrieval step. The idea is that this content will aid in SQL query creation with these strategies. More details about these NL2SQL strategies can be found in the [orchestrator repository](https://github.com/azure/gpt-rag-agentic).

The NL2SQL Ingestion Process indexes three content types:

- **query**: Examples of queries for both **few-shot** and **few-shot scaled** strategies.
- **table**: Descriptions of tables for the **few-shot scaled** scenario.
- **column**: Descriptions of columns for the **few-shot scaled** scenario.

> [!NOTE] 
> If you are using the **few-shot** strategy, you will only need to index queries.

Each item—whether a query, table, or column—is represented in a JSON file with information specific to the query, table, or column, respectively.

Here’s an example of a query file:

```json
{
    "question": "What are the top 5 most expensive products currently available for sale?",
    "query": "SELECT TOP 5 ProductID, Name, ListPrice FROM SalesLT.Product WHERE SellEndDate IS NULL ORDER BY ListPrice DESC",
    "selected_tables": [
        "SalesLT.Product"
    ],
    "selected_columns": [
        "SalesLT.Product-ProductID",
        "SalesLT.Product-Name",
        "SalesLT.Product-ListPrice",
        "SalesLT.Product-SellEndDate"
    ],
    "reasoning": "This query retrieves the top 5 products with the highest selling prices that are currently available for sale. It uses the SalesLT.Product table, selects relevant columns, and filters out products that are no longer available by checking that SellEndDate is NULL."
}
```

In the [**nl2sql**](samples/nl2sql) directory of this repository, you can find additional examples of queries, tables, and columns for the following Adventure Works sample SQL Database tables.

![Document Ingestion Pipeline](media/nl2sql_adventure_works.png)  
*Sample Adventure Works Database Tables*

> [!NOTE]  
> You can deploy this sample database in your [Azure SQL Database](https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure?view=sql-server-ver16&tabs=ssms#deploy-to-azure-sql-database).

The diagram below illustrates the NL2SQL data ingestion pipeline.

![NL2SQL Ingestion Pipeline](media/nl2sql_ingestion_pipeline.png)  
*NL2SQL Ingestion Pipeline*

**Workflow**

This outlines the ingestion workflow for **query** elements.

> **Note:**  
> The workflow for tables and columns is similar; just replace **queries** with **tables** or **columns** in the steps below.

1. The AI Search `queries-indexer` scans for new query files (each containing a single query) within the `queries` folder in the `nl2sql` storage container.

   > **Note:**  
   > Files are stored in the `queries` folder, not in the root of the `nl2sql` container. This setup also applies to `tables` and `columns`.

2. The `queries-indexer` then uses the `#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill` to create a vectorized representation of the question text using the Azure OpenAI Embeddings model.

   > **Note:**  
   > For query items, the question itself is vectorized. For tables and columns, their descriptions are vectorized.

3. Finally, the indexed content is added to the `nl2sql-queries` index.

### Sharepoint Indexing

Learn how the SharePoint Connector works in the [How It Works: SharePoint Connector](docs/HOW_SHAREPOINT_CONNECTOR_WORKS.md) section.

## How-to: Developer

### Redeploying the Ingestion Component
- Provision the infrastructure and deploy the solution using the [GPT-RAG](https://aka.ms/gpt-rag) template.

- **Redeployment Steps**:
  - Prerequisites: 
    - **Azure Developer CLI**
    - **PowerShell** (Windows only)
    - **Git**
    - **Python 3.11**
  - Redeployment commands:
    ```bash
    azd auth login  
    azd env refresh  
    azd deploy  
    ```
    > **Note:** Use the same environment name, subscription, and region as the initial deployment when running `azd env refresh`.

### Running Locally
- Instructions for testing the data ingestion component locally using in VS Code. See [Local Deployment Guide](docs/LOCAL_DEPLOYMENT.md).

### Configuring Sharepoint Connector

Follow the instructions to configure the SharePoint Connector in the [Configuration Guide: SharePoint Connector](docs/HOW_TO_SETUP_SHAREPOINT_CONNECTOR.md).

## How-to: User

### Uploading Documents for Ingestion
- Refer to the [GPT-RAG Admin & User Guide](https://github.com/Azure/GPT-RAG/blob/main/docs/GUIDE.md#uploading-documents-for-ingestion) for instructions.

### Reindexing Documents in AI Search
- See [GPT-RAG Admin & User Guide](https://github.com/Azure/GPT-RAG/blob/main/docs/GUIDE.md#reindexing-documents-in-ai-search) for reindexing instructions.

## Reference

### Supported Formats and Chunkers
Here are the formats supported by each chunker. The file extension determines which chunker is used.

#### Doc Analysis Chunker (Document Intelligence based)
| Extension | Doc Int API Version |
|-----------|---------------------|
| pdf       | 3.1, 4.0            |
| bmp       | 3.1, 4.0            |
| jpeg      | 3.1, 4.0            |
| png       | 3.1, 4.0            |
| tiff      | 3.1, 4.0            |
| xlsx      | 4.0                 |
| docx      | 4.0                 |
| pptx      | 4.0                 |

#### LangChain Chunker
| Extension | Format                        |
|-----------|-------------------------------|
| md        | Markdown document             |
| txt       | Plain text file               |
| html      | HTML document                 |
| shtml     | Server-side HTML document     |
| htm       | HTML document                 |
| py        | Python script                 |
| json      | JSON data file                |
| csv       | Comma-separated values file   |
| xml       | XML data file                 |

#### Transcription Chunker
| Extension | Format              |
|-----------|---------------------|
| vtt       | Video transcription |

#### Spreadsheet Chunker
| Extension | Format      |
|-----------|-------------|
| xlsx      | Spreadsheet |

### External Resources
- [AI Search Enrichment Pipeline](https://learn.microsoft.com/en-us/azure/search/cognitive-search-concept-intro)
- [Azure Open AI Embeddings Generator](https://github.com/Azure-Samples/azure-search-power-skills/tree/57214f6e8773029a638a8f56840ab79fd38574a2/Vector/EmbeddingGenerator)