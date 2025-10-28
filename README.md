# 🎯 Visual Trade Copilot

A browser extension that provides real-time market structure analysis using Smart Money Concepts (SMC) and supply/demand principles. The system analyzes trading charts visually and provides actionable guidance through an AI-powered assistant.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.2-green.svg)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4%20Vision-orange.svg)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Project Structure

```
trading-project/
├── server/                 # FastAPI backend server
│   ├── app.py             # Main FastAPI application
│   ├── decision.py        # Analysis logic and rule-based filters
│   ├── requirements.txt   # Python dependencies
│   └── .env.example       # Environment variables template
├── extension/             # Chrome extension (to be implemented)
├── docs/
│   └── SRS.md            # Software Requirements Specification
└── README.md             # This file
```

## Features

- **Real-time Chart Analysis**: Analyzes trading charts using GPT-4 Vision API
- **Smart Money Concepts**: Focuses on SMC principles including supply/demand zones, liquidity sweeps, and displacement
- **Rule-based Validation**: Post-processes AI analysis to ensure consistency with trading rules
- **Privacy-first**: Runs locally, only sends chart images to OpenAI API
- **Low Latency**: Designed for 2-5 second analysis cycles
- **Flexible Image Processing**: Works with or without Pillow for image optimization

## Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/ArgusOnline01/trading-ai-extension.git
   cd trading-ai-extension
   ```

2. **Create and activate a virtual environment:**
   ```bash
   cd server
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the FastAPI server:**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8765
   ```

The server will be available at `http://localhost:8765`

### Testing the API

You can test the `/analyze` endpoint using curl or any HTTP client:

```bash
curl -X POST "http://localhost:8765/analyze" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@path/to/your/chart.png"
```

Or use the interactive API docs at `http://localhost:8765/docs`

## API Endpoints

- `GET /` - Health check
- `POST /analyze` - Analyze a trading chart image
- `GET /prompt` - Get the current analysis prompt (for debugging)

## Analysis Output

The `/analyze` endpoint returns a JSON response with:

```json
{
  "success": true,
  "analysis": {
    "bias": "bullish|bearish|neutral",
    "inPOI": true|false,
    "hasSweep": true|false,
    "hasDisplacement": true|false,
    "hasFVG": true|false,
    "fiftyPctMitigation": true|false,
    "verdict": "enter|wait|invalid",
    "rationale": "Brief explanation of the analysis"
  },
  "image_info": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG"
  }
}
```

## Trading Rules

The system applies rule-based validation to ensure analysis consistency:

1. **Enter Requirements**: Must have either sweep+displacement or 50% mitigation+displacement
2. **POI Requirement**: Enter signals should be in or near a Point of Interest
3. **Signal Validation**: All signal fields must be boolean values
4. **Bias Validation**: Bias must be bullish, bearish, or neutral

## Development

### Running in Development Mode

```bash
cd server
uvicorn app:app --reload --host 0.0.0.0 --port 8765
```

### Project Status

- ✅ **Phase 1**: Backend API (FastAPI server) - Complete
- 🔄 **Phase 2**: Chrome Extension - In Progress
- ⏳ **Phase 3**: Advanced Features - Planned

## License

This project is for educational purposes. Not financial advice.

## Support

For issues or questions, please refer to the SRS document in the `docs/` folder.
