# Contributing to Computer

Thank you for considering contributing to Computer! This document provides guidelines and instructions for contributing to this self-modifying AI assistant project.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check the existing issues to see if the problem has already been reported. If it hasn't, create a new issue with a clear title and description that includes:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- A clear, descriptive title
- A detailed description of the proposed enhancement
- Any potential implementation details you can provide
- Why this enhancement would be useful to most users

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure your changes don't break existing functionality
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines for Python code
- Use meaningful variable and function names
- Include docstrings for all functions, classes, and modules
- Keep functions focused on a single responsibility

### Testing

- Add tests for new features
- Ensure all tests pass before submitting a pull request
- Update tests when modifying existing functionality

### Security Considerations

- Never commit API keys or credentials
- Be cautious when implementing features that involve code execution or database operations
- Follow the security patterns established in the codebase

### Documentation

- Update documentation to reflect your changes
- Document new features, tools, or configuration options
- Keep the README.md up to date

## Tool Development

When adding a new tool to the assistant:

1. Create a new Python file in the `src/tools` directory
2. Implement your tool function with proper error handling
3. Add comprehensive docstrings
4. Consider security implications
5. Add the tool to the `TOOL_MAPPING` and `TOOLS` lists in the assistant file
6. Update the system prompt to include instructions for your tool

## License

By contributing to Computer, you agree that your contributions will be licensed under the project's [MIT License](LICENSE.md).