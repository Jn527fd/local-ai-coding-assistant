# Sample Code Repository

This small repository is a fixture for testing the Local AI Coding Assistant's
repository indexing endpoint.

It intentionally contains:

- Python source code
- JavaScript source code
- JSON and YAML configuration
- HTML and CSS assets
- Nested directories
- A `node_modules/` file that the indexer must ignore
- An unsupported `.txt` file that the indexer must ignore

From the root of the main project, obtain its absolute path with:

```bash
realpath sample-code-repository
```

The expected repository name in the API response is
`sample-code-repository`.

After indexing, use that name to test repository RAG:

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

The returned sources should include `app.py` and
`sample_app/calculator.py`.
