# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability within Computer, please send an email to me@mihaisafta.com. All security vulnerabilities will be promptly addressed.

Please include the following information in your report:

- Type of vulnerability
- Full path of the affected file(s)
- Location of the affected code (line number)
- Proof of concept or exploit code (if possible)
- Impact of the vulnerability

## Security Model

Computer is designed with several security measures to protect against common vulnerabilities:

### Code Execution Sandbox

The Python code execution feature is:
- Disabled by default (`ENABLE_CODE_EXECUTION=false`)
- When enabled, uses a sandbox implementation that:
  - Restricts access to dangerous modules and functions
  - Sets CPU and memory resource limits
  - Executes code in a separate process with a timeout
  - Validates code for dangerous patterns before execution

### SQL Validation

All SQL operations are validated before execution:
- Checks for common SQL injection patterns
- Prevents dangerous operations like DROP TABLE
- Validates input parameters

### Authentication

The web API is protected with HTTP Basic Authentication:
- Username and password are configured via environment variables
- All API endpoints require authentication

### Environment Variables

Sensitive information is managed through environment variables:
- API keys and credentials are never hardcoded
- The `.env.example` file provides a template without actual credentials
- The `.gitignore` file prevents committing `.env` files

## Best Practices for Deployment

When deploying Computer, follow these security best practices:

1. **Use strong, unique passwords** for the AUTH_USERNAME and AUTH_PASSWORD
2. **Keep code execution disabled** unless absolutely necessary
3. **Run in an isolated environment** such as a container or virtual machine
4. **Regularly update dependencies** to patch security vulnerabilities
5. **Limit network access** to the application
6. **Use HTTPS** for all communications
7. **Regularly back up your database**

## Security Features Roadmap

Future security enhancements planned for Computer include:

1. Role-based access control
2. Rate limiting for API endpoints
3. Enhanced logging for security events
4. Improved input validation
5. Support for OAuth authentication