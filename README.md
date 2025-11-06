# Trading Strategy Optimization System

A comprehensive trading strategy optimization and backtesting system with AI-powered strategy generation and web-based management interface.

## 🚀 Features

### Strategy Optimization
- **AI-Powered Optimization**: Uses DeepSeek AI for iterative strategy refinement
- **Single Symbol Optimization**: Optimize strategies for individual symbols
- **Universal Strategy**: Generate robust strategies across multiple symbols
- **Auto-Save**: Strategies saved with timestamps and performance metrics

### Strategy Scanning & Backtesting
- **Batch Scanning**: Test multiple symbols and strategies simultaneously
- **Multi-Strategy Support**: Test multiple strategies per symbol
- **Real Options Pricing**: Accurate option pricing based on historical data
- **Comprehensive Reports**: Detailed HTML reports with charts and trade analysis

### Web Application
- **Real-Time Monitoring**: Live log streaming from optimization tasks
- **Background Processing**: Tasks run without blocking the UI
- **Strategy Management**: Compare, analyze, and manage strategies
- **Interactive Reports**: View equity curves, performance metrics, and trade details

## 📦 Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd opt_exp_cur

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## 🎯 Quick Start

### Web Interface (Recommended)
```bash
streamlit run web_app.py
```
Then open http://localhost:8501 in your browser.

### Command Line

**Optimize a strategy:**
```bash
python run_iterative_optimization.py --symbol BABA --start 2025-01-01 --end 2025-12-01
```

**Scan multiple symbols:**
```bash
python run_strategy_scanner.py --symbols BABA NVDA --start 2025-01-01 --end 2025-12-01
```

**Universal strategy optimization:**
```bash
python run_universal_optimization.py --symbols BABA NVDA PLTR --start 2025-01-01 --end 2025-12-01
```

## 📁 Project Structure

```
opt_exp_cur/
├── web_app.py                      # Streamlit web application
├── run_iterative_optimization.py   # Single symbol optimization
├── run_universal_optimization.py   # Multi-symbol optimization
├── run_strategy_scanner.py         # Strategy scanning script
├── strategy_scanner.py             # Scanner core logic
├── iterative_optimizer.py          # Optimization engine
├── backtest_engine.py              # Backtesting engine
├── report_generator.py             # Report generation
├── signal_library.py               # Technical indicators
├── ai_rl_engine/                   # AI components
│   ├── deepseek_client.py         # DeepSeek AI integration
│   └── ...
└── strategies/                     # Strategy JSON files
    ├── BABA_ST.json
    └── NVDA_ST.json
```

## 🔧 Configuration

### Environment Variables (.env)
```env
DEEPSEEK_API_KEY=your_api_key_here
POLYGON_API_KEY=your_polygon_key_here
```

### Strategy Configuration
Strategies are stored as JSON files in the `strategies/` directory:

```json
{
  "name": "Strategy_Name",
  "signal_weights": {
    "macd_crossover": 0.25,
    "rsi_oversold": 0.20,
    "volume_surge": 0.15
  },
  "params": {
    "profit_target": 5.0,
    "stop_loss": -0.5,
    "max_holding_days": 30,
    "position_size": 0.1
  }
}
```

## 📊 Reports

Reports are automatically generated and saved to:
- **Equity Curves**: `report_assets/scan_equity_*.png`
- **Performance Charts**: `report_assets/scan_comparison_*.png`
- **HTML Reports**: `report_assets/scan_report.html`
- **CSV Data**: `report_assets/scan_results.csv`

## 🐳 Docker Support

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading involves risk. Past performance does not guarantee future results.

