# Detailed Setup Guide

Complete installation instructions for the Wincher MCP Server.

## System Requirements

- **Operating System:** macOS, Windows, or Linux
- **Python:** 3.10 or higher
- **Claude Desktop:** Latest version ([download here](https://claude.ai/download))
- **Wincher Account:** With API access enabled

## Step-by-Step Installation

### 1. Install Python (if needed)

**macOS:**
```bash
# Check if Python 3.10+ is installed
python3 --version

# If not installed, use Homebrew
brew install python@3.11
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

**Linux:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
```

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/wincher-mcp-server.git
cd wincher-mcp-server
```

### 3. Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv wincher-mcp-env
source wincher-mcp-env/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv wincher-mcp-env
wincher-mcp-env\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv wincher-mcp-env
.\wincher-mcp-env\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

Verify installation:
```bash
pip list | grep mcp
pip list | grep httpx
```

You should see both packages listed.

### 5. Get Your Wincher API Key

1. Log into your Wincher account at https://www.wincher.com
2. Click your profile icon → **Settings**
3. Navigate to **Personal Access Tokens**
4. Click **"Generate New Token"**
5. Give it a name (e.g., "Claude MCP Server")
6. Copy the generated token immediately (you won't see it again!)

### 6. Find Your File Paths

You need the absolute paths to:
1. Your Python executable in the virtual environment
2. Your `wincher_mcp_server.py` file

**Get Python path:**
```bash
# macOS/Linux (while virtual env is activated)
which python

# Windows
where python
```

**Get script path:**
```bash
# macOS/Linux
pwd
# This shows your current directory. Add /wincher_mcp_server.py to the end

# Windows
cd
# This shows your current directory. Add \wincher_mcp_server.py to the end
```

Example paths:
- **macOS:** `/Users/yourname/wincher-mcp-server/wincher-mcp-env/bin/python`
- **Windows:** `C:\Users\yourname\wincher-mcp-server\wincher-mcp-env\Scripts\python.exe`

### 7. Configure Claude Desktop

**Find your config file:**

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Edit the file:**

If the file doesn't exist, create it. If it exists and has other MCP servers, add the Wincher configuration to the existing `mcpServers` object.

**New config file:**
```json
{
  "mcpServers": {
    "wincher": {
      "command": "/absolute/path/to/wincher-mcp-env/bin/python",
      "args": [
        "/absolute/path/to/wincher_mcp_server.py"
      ],
      "env": {
        "WINCHER_API_KEY": "your_actual_api_key_here"
      }
    }
  }
}
```

See [MCP_CONFIG.example.json](MCP_CONFIG.example.json). For optional staging, add `"--use-staging"` to `args` and set `WINCHER_STAGING_API_HOST` in `env` on your machine only (never commit the host value).

**Adding to existing config:**
```json
{
  "mcpServers": {
    "existing-server": {
      "command": "...",
      "args": ["..."]
    },
    "wincher": {
      "command": "/absolute/path/to/wincher-mcp-env/bin/python",
      "args": [
        "/absolute/path/to/wincher_mcp_server.py"
      ],
      "env": {
        "WINCHER_API_KEY": "your_actual_api_key_here"
      }
    }
  }
}
```

**Important:**
- Use **absolute paths** (full paths starting from root)
- Replace `your_actual_api_key_here` with your Wincher API key
- On Windows, use forward slashes `/` or escaped backslashes `\\` in paths
- Ensure the JSON is valid (no trailing commas, proper quotes)

### 8. Restart Claude Desktop

**Completely quit Claude Desktop:**
- **macOS:** Cmd+Q or Claude → Quit Claude
- **Windows:** File → Exit

**Restart the application**

### 9. Test the Connection

Open Claude Desktop and try:
```
"Show me my Wincher websites"
```

If successful, you'll see your tracked websites with keyword counts and competitor information.

## Troubleshooting

### "Connection refused" or "Server not responding"

**Check 1: Verify paths**
```bash
# Test that Python executable works
/your/path/to/wincher-mcp-env/bin/python --version

# Test that script exists
ls -la /your/path/to/wincher_mcp_server.py
```

**Check 2: Test the script manually**
```bash
cd /path/to/wincher-mcp-server
source wincher-mcp-env/bin/activate
export WINCHER_API_KEY="your_api_key"
python wincher_mcp_server.py
```

It should run without errors. Press Ctrl+C to stop.

**Check 3: Verify JSON syntax**
Use a JSON validator to check your `claude_desktop_config.json`:
```bash
# macOS/Linux
python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### "API Error: 401 Unauthorized"

Your API key is invalid or missing.

1. Check that your API key is correctly copied (no extra spaces)
2. Verify the key works with a direct API call:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.wincher.com/v1/websites
```
3. If it fails, generate a new API key in Wincher

### "API Error: 404 Not Found"

You might not have any websites tracked in Wincher yet.

1. Log into Wincher
2. Add at least one website to track
3. Add some keywords to that website
4. Wait a few minutes for initial ranking data
5. Try again in Claude

### Virtual Environment Issues

**"Command not found: python"**

Make sure you activated the virtual environment:
```bash
source wincher-mcp-env/bin/activate  # macOS/Linux
wincher-mcp-env\Scripts\activate      # Windows
```

You should see `(wincher-mcp-env)` in your terminal prompt.

### Windows-Specific Issues

**PowerShell execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Path with spaces:**
If your path has spaces, ensure they're inside the JSON quotes:
```json
"command": "C:/Users/First Last/wincher-mcp-server/wincher-mcp-env/Scripts/python.exe"
```

## Verifying Installation

Run these checks to ensure everything is set up correctly:
```bash
# 1. Virtual environment activated?
which python  # Should show path in wincher-mcp-env

# 2. Dependencies installed?
pip list | grep -E "mcp|httpx"

# 3. API key works?
curl -H "Authorization: Bearer YOUR_KEY" https://api.wincher.com/v1/websites

# 4. Config file exists and is valid JSON?
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool
```

## Updating

To update to the latest version:
```bash
cd wincher-mcp-server
git pull origin main
source wincher-mcp-env/bin/activate  # Activate virtual env
pip install -r requirements.txt --upgrade
```

Restart Claude Desktop after updating.

## Getting Help

1. Check the [main README](../README.md)
2. Review [example usage](EXAMPLES.md)
3. Open an issue on GitHub with:
   - Your operating system
   - Python version (`python --version`)
   - Error messages (if any)
   - Steps you've already tried

## Security Best Practices

- ✅ Never commit your API key to Git
- ✅ Use environment variables or config files (not in code)
- ✅ Keep your API key secure like a password
- ✅ Rotate your API key periodically
- ✅ Revoke unused API keys in Wincher settings

## Next Steps

Once installed, check out:
- [Usage Examples](EXAMPLES.md) - 50+ example prompts
- [Wincher API Docs](https://www.wincher.com/docs/api) - Learn about available data
- Test with your own tracked keywords and competitors!
