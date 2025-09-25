# RecuDL

A modern video downloader for Recu.me with a sleek web interface and powerful CLI tools.

![RecuDL Web Interface](https://img.shields.io/badge/Interface-Web%20%2B%20CLI-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/License-GPL--3.0-blue)

## ✨ Features

### 🎬 **Video Downloading**
- Download videos from Recu.me with full authentication support
- **Time range downloads**: Download specific segments using `URL,START,END,TOTAL` format
- **Multiple download modes**: Parallel (default), Series, Hybrid
- **Resume capability**: Continue interrupted downloads
- **Batch downloads**: Multiple videos simultaneously

### 🌐 **Modern Web Interface**
- **Real-time dashboard** with live progress monitoring
- **⚡ Instant cookie setup** with drag-and-drop bookmarklet (30 seconds!)
- **Configuration editor** for authentication and settings
- **Download history** with search and retry functionality
- **Built-in documentation** (Get Started guide + FAQ)
- **Responsive design** works on desktop and mobile

### 🔧 **Post-Processing Pipeline**
- **MP4 conversion**: Automatic TS to MP4 remuxing (lossless)
- **Thumbnail generation**: Preview images at 25% duration
- **File organization**: Automatic sorting into directories
- **M3U8 cleanup**: Removes temporary playlist files
- **JSON reports**: Detailed download information

## 🚀 Quick Start

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/GitResetHard/RecuDL.git
   cd RecuDL
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (optional, for MP4 conversion)
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add to your system PATH

4. **Any Browser** (for cookie setup)
   - Use the built-in bookmarklet method (works in any browser)
   - No downloads or installations needed

### Web Interface (Recommended)

1. **Start the web server**
   ```bash
   python -m recudl --web-ui
   ```

2. **Open your browser**
   ```
   http://127.0.0.1:8080
   ```

3. **Configure authentication** (Configuration page)
   - Use the **bookmarklet method** for instant cookie setup (30 seconds!)
   - Or manually copy Cookie and User-Agent from browser DevTools
   - See the Get Started guide for detailed instructions

4. **Start downloading** (Dashboard page)
   - Paste video URLs (one per line)
   - For time ranges: `https://recu.me/video/user/play,10:00,25:00,30:00`
   - Click "Start Download"

### Command Line Interface

```bash
# Basic download
python -m recudl config.json parallel

# Series download (one at a time)
python -m recudl config.json series

# Hybrid download (parallel across hosts)
python -m recudl config.json hybrid

# Playlist only (no video download)
python -m recudl config.json playlist
```

## 📋 Configuration

### Authentication Setup

1. **Login to Recu.me** in your browser
2. **Open Developer Tools** (F12)
3. **Go to Network tab** and refresh the page
4. **Find any request** to recu.me
5. **Copy Cookie and User-Agent** from Request Headers
6. **Add to configuration** via web interface or config.json

### Time Range Format

Download specific segments using this format:
```
https://recu.me/video/username/play,START,END,TOTAL
```

**Examples:**
- Full video: `https://recu.me/video/user/play`
- Last 30 minutes: `https://recu.me/video/user/play,60:00,90:00,90:00`
- Skip first 5 minutes: `https://recu.me/video/user/play,5:00,60:00,60:00`
- Middle section: `https://recu.me/video/user/play,15:00,45:00,60:00`

### Configuration File (config.json)

```json
{
    "urls": [
        "https://recu.me/video/user1/play",
        "https://recu.me/video/user2/play,10:00,25:00,30:00"
    ],
    "header": {
        "Cookie": "your-cookie-here",
        "User-Agent": "your-user-agent-here"
    },
    "post_process": {
        "remux_to_mp4": true,
        "generate_thumbnail": true,
        "organize_output": true,
        "output_dir": "downloads",
        "reports_dir": "reports",
        "thumbnails_dir": "thumbnails"
    }
}
```

## 🏗️ Architecture

### Package Structure
```
recudl/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── config.py            # Configuration management
├── console.py           # Terminal UI utilities
├── playlist.py          # M3U8 playlist handling
├── post_process.py      # Post-download processing
├── recu.py              # Core download engine
├── state.py             # Download state management
├── tools.py             # Utility functions
├── web_server.py        # Flask web server
└── templates/           # Web UI templates
    ├── base.html
    ├── dashboard.html
    ├── config.html
    ├── history.html
    ├── get_started.html
    └── faq.html
```

### Download Process
1. **Authentication** → Validate credentials with Recu.me
2. **URL Processing** → Parse video URLs and time ranges
3. **Playlist Retrieval** → Get M3U8 playlist from API
4. **Segment Download** → Download video segments (TS files)
5. **Post-Processing** → Convert to MP4, generate thumbnails
6. **Organization** → Move files to output directories
7. **Cleanup** → Remove temporary files

## 🛠️ Development

### Requirements
- Python 3.8+
- Flask 3.0+
- Rich 13.7+
- Requests 2.31+
- FFmpeg (optional)

### Running in Development
```bash
# Web interface with debug mode
python -m recudl --web-ui 127.0.0.1 8080 --debug

# CLI with verbose output
python -m recudl config.json parallel --verbose
```

### Project Structure
- **CLI Interface**: `__main__.py` - Command-line argument parsing and execution
- **Web Interface**: `web_server.py` - Flask routes and API endpoints
- **Core Engine**: `recu.py` - Video downloading logic
- **Configuration**: `config.py` - Settings management and validation
- **Post-Processing**: `post_process.py` - File conversion and organization

## 📖 Documentation

### Web Interface Documentation
- **Get Started Guide**: Step-by-step setup instructions
- **FAQ**: Common questions and troubleshooting
- **Configuration Help**: Authentication and settings guide

### CLI Help
```bash
python -m recudl --help
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

### GPL-3.0 License Summary
- ✅ **Freedom to use** - Use the software for any purpose
- ✅ **Freedom to study** - Access and modify the source code
- ✅ **Freedom to share** - Distribute copies to help others
- ✅ **Freedom to improve** - Distribute modified versions
- ⚠️ **Copyleft** - Derivative works must also be GPL-3.0 licensed

## ⚠️ Disclaimer

This tool is for educational purposes only. Users are responsible for complying with Recu.me's terms of service and applicable laws. The developers are not responsible for any misuse of this software.

## 🔗 Links

- **Issues**: [Report bugs or request features](https://github.com/GitResetHard/RecuDL/issues)
- **Discussions**: [Community discussions](https://github.com/GitResetHard/RecuDL/discussions)
- **Releases**: [Download latest version](https://github.com/GitResetHard/RecuDL/releases)

---

**Made with ❤️ for the community**
