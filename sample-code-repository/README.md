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
