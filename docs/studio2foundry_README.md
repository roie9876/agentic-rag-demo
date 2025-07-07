# Studio2Foundry Deployment Tab

This tab provides a user-friendly interface for deploying Azure Functions from the `studio2foundry` folder to Azure AI Foundry.

## Features

- **Function Discovery**: Automatically scans the `studio2foundry` folder for Azure Functions
- **Code Editing**: View and edit function code directly in the UI
- **Flexible Configuration**: Uses environment variables instead of hardcoded values
- **Deployment Management**: Package and deploy functions with custom configurations
- **Environment Variables**: Configure function settings and environment variables

## Setup

1. Ensure `PROJECT_ENDPOINT` is set in your `.env` file:
   ```
   PROJECT_ENDPOINT=your-azure-ai-foundry-project-endpoint
   ```

2. Place your Azure Function code in the `studio2foundry` folder

3. The tab will automatically detect functions based on:
   - `function.json` files (for individual functions)
   - `function_app.py` (for the main function app)

## Usage

1. **Select Function**: Choose from the dropdown list of available functions
2. **Edit Code**: Use the built-in editor to modify function code
3. **Configure Deployment**: Set deployment parameters like environment, timeout, and memory
4. **Set Environment Variables**: Configure runtime environment variables
5. **Deploy**: Either create a deployment package or deploy directly to Azure

## Function Structure

The tab expects the following structure in the `studio2foundry` folder:

```
studio2foundry/
├── function_app.py          # Main function app file
├── host.json               # Function host configuration
├── requirements.txt        # Python dependencies
├── local.settings.json     # Local development settings
└── [function_name]/        # Individual function folders
    ├── function.json       # Function binding configuration
    └── __init__.py         # Function implementation
```

## Environment Variables

The following environment variables are automatically configured:

- `PROJECT_ENDPOINT`: Azure AI Foundry project endpoint (from .env)
- Custom variables can be added through the UI

## Security

- Uses Azure managed identity for authentication
- Environment variables are securely handled
- No hardcoded credentials in the function code

## Deployment Options

- **Package Only**: Create a ZIP deployment package for manual deployment
- **Deploy Now**: Directly deploy to the configured Azure environment

## Troubleshooting

- Ensure the `studio2foundry` folder exists and contains valid Azure Function files
- Check that `PROJECT_ENDPOINT` is properly set in your `.env` file
- Verify Azure credentials and permissions for deployment
