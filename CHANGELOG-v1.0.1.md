# Changelog v1.0.1

## [1.0.1] - 2026-07-11

### Added
- `repository` metadata with URL, source, and GitHub repo ID
- `website_url` field pointing to GitHub Pages dashboard
- `remotes` array for streamable-http transport (replaces single `remote` object)

### Fixed
- Empty `repository` field in Official MCP Registry entry (caused Artifacta.io and other leaderboards to skip us)

### Infrastructure
- Added `.gitignore` for MCP publisher tokens (security fix)
- Updated README with remote MCP server installation option
- Updated mcp-submission-guide.md with 18 tracked platforms

### Registry
- Name: `io.github.hbhqq9/bde-score`
- Published to: Official MCP Registry
- Status: pending (v1.0.1)
