# *Computer* - Self-Modifying AI Assistant

A powerful, extensible AI assistant that can modify its own code, add new capabilities, and adapt to user needs in real-time.

## 🌟 Features

- **Self-Modifying Code**: The assistant can analyze and update its own source code
- **Dynamic Tool Addition**: Add new capabilities without manual intervention
- **Multiple LLM Support**: Works with OpenRouter (cloud) and Ollama (local) models
- **Database Integration**: Built-in PostgreSQL support for data persistence
- **Web Interface**: Modern, responsive chat UI
- **Slack Integration**: Deploy the assistant to your Slack workspace
- **Version Evolution**: Each modification creates a new version, maintaining history

## 🧩 Available Tools

- **SQL Database Operations**: Execute queries, create tables, and manage data
- **Python Code Execution**: Run code snippets for calculations and data processing
- **ASCII Art Generation**: Create text-based graphics for visual communication
- **Self-Code Update**: Add new tools and capabilities dynamically

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Slack app (for Slack bot functionality)
- Replit DB (for conversation history persistence)
- OpenRouter API key or Ollama installation

### Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:saftacatalinmihai/Computer.git
   cd ai-assistant
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file and fill in your configuration values.

4. Initialize the database:
   ```bash
   # Run the database initialization script if provided
   # or set up your PostgreSQL database manually
   ```

### Running the Application

Start the web server:
```bash
python src/main.py
```

## Configuration

The application is configured using environment variables. See `.env.example` for all available configuration options.

### Key Configuration Options

- `PORT`: Web server port (default: 8080)
- `HOST`: Web server host (default: 0.0.0.0)
- `POSTGRES_*`: PostgreSQL connection details
- `REPLIT_DB_URL`: URL for Replit Key Value Pair DB for conversation history
- `OPENROUTER_API_KEY`: API key for OpenRouter
- `OLLAMA_HOST`: URL for Ollama API (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use with Ollama (default: qwen2.5-coder:3b)
- `DEFAULT_LLM_MODEL`: Default model for OpenRouter (default: openai/gpt-4o-mini)
- `ENABLE_SLACK_BOT`: Enable Slack bot integration (default: false)
- `ENABLE_CODE_EXECUTION`: Enable Python code execution tool (default: false)
- `SANDBOX_EXECUTION`: Use sandbox for code execution (default: true)

## Security Considerations

- The application includes HTTP Basic Authentication for the web API
- Code execution is disabled by default and should only be enabled in trusted environments
- When enabled, code execution uses a sandbox to limit potential security risks
- All database queries are validated before execution

For detailed security information and best practices, see [SECURITY.md](SECURITY.md).

## 🏗️ Architecture

The application is built with a modular architecture that allows for easy extension and modification:

- **Assistant Versions**: Multiple assistant implementations (v1-v4) with increasing capabilities
- **Dynamic Loading**: Assistant versions can be loaded at runtime
- **Tool System**: Extensible tool framework for adding new capabilities
- **LLM Clients**: Support for multiple language models through different clients
- **Web & Slack Interfaces**: Multiple ways to interact with the assistant

For a detailed overview of the system architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🛠️ Development

### Adding a New Tool

The assistant can add tools to itself, or you can manually add them:

1. Create a new Python file in the `src/tools` directory
2. Implement your tool function
3. Add the tool to the `TOOL_MAPPING` and `TOOLS` lists in the assistant file
4. Update the system prompt to include instructions for your tool

### Modifying the Assistant

The assistant can modify itself using the `self-code-update` tool, which:

1. Creates a new version file (e.g., assistant_v5.py)
2. Implements the requested changes
3. Maintains backward compatibility

## 📚 API Reference

### HTTP Endpoints

- `GET /`: Web interface
- `POST /computer`: Send messages to the assistant
- `GET /new_conversation`: Start a new conversation

## 🤝 Contributing

We welcome contributions to Computer! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🙏 Acknowledgements

- [OpenRouter](https://openrouter.ai/) for providing access to various LLMs
- [Ollama](https://ollama.ai/) for local LLM support
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Slack API](https://api.slack.com/) for bot integration