# GPT RAG Semantic Kernel Model Context Protocol Server
Part of [GPT‑RAG](https://aka.ms/gpt-rag)

The GPT-RAG MCP service deploys an MCP server that is used to enable agentic features in AI Chat Applications. Documentation on the Model Context Protocol can be found here: [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro)

## Prerequisites

Before deploying the application, you must provision the infrastructure as described in the [GPT-RAG](https://github.com/azure/gpt-rag) repo. This includes creating all necessary Azure resources required to support the application runtime.

<details markdown="block">
<summary>Click to view <strong>software</strong> prerequisites</summary>
<br>
The machine used to customize and or deploy the service should have:

* Azure CLI: [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
* Azure Developer CLI (optional, if using azd): [Install azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
* Git: [Download Git](https://git-scm.com/downloads)
* Python 3.12: [Download Python 3.12](https://www.python.org/downloads/release/python-3120/)
* Docker CLI: [Install Docker](https://docs.docker.com/get-docker/)
* VS Code (recommended): [Download VS Code](https://code.visualstudio.com/download)
</details>

##### Initialize the template:
- Ensure the .azure directory is present in the root
- `azd deploy`

### Deploying the app with a shell script

To deploy using a script, first clone the repository, set the App Configuration endpoint, and then run the deployment script.

##### PowerShell (Windows)
```powershell
$env:APP_CONFIG_ENDPOINT = "https://<your-app-config-name>.azconfig.io"
cd gpt-rag-mcp
.\scripts\deploy.ps1
```

#### Instructions Post Deployment (Must be executed for MCP Server to work properly)
- Navigate to App Configuration resource in Azure portal
- Update `AGENT_STRATEGY` variable to `mcp`
- Update `MCP_SERVER_URL` variable to `<container_app_url>/mcp` (e.g. `https://{container-app-name}.{container-app-region}.azurecontainerapps.io/mcp`) or the desired MCP Server URL (if external)
- In Azure Portal, Stop Orchestrator Container App, then restart it
- Open frontend URL in your browser and ask "What tools are available to you?" If the MCP Server is working properly, it will list tools and their functionality.

### Start MCP Model Inspector to Test MCP connection

- Run the following command in bash or pwsh
```bash
npx @modelcontextprotocol/inspector
```
- Click on the link displayed in terminal that says "MCP Inspector is up and running at..."
- Plug in your container Application URL (found on container app overview page in Azure portal) followed by `/mcp` (e.g. `https://<container_app_name>.eastus.azurecontainerapps.io/mcp`)


## Deploy Locally
- Create a directory .vscode in your root
- Move launch.json into .vscode
- Update the app configuration resource
- Run VS Code Debugger