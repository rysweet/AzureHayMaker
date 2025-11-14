# Azure HayMaker - Generate Benign Service Telemetry for a Azure Tenant Simulation

We are going to start a new project.
This project's purpose is to run a service that generates benign telemetry meant to simulate ordinary service operations within an existing azure tenant. To this end it will employ a large number o different service principals performing a wide range of administrative actions on a target tenant.

## Preparation

Create a new public open source GitHub repo in the rysweet GitHub account called "AzureHayMaker".
Set the default branch to main.
Require PRs for merging to main.
Configure to always offer to update a PR branch if it's out of date.
Initialize the git repo in the current dir.
Project language: python, using uv, pytest, ruff, pyright
Create project scaffolding for a python project, including pre-commit hooks for listing, formatting, type safety, and running tests.

## Groundwork - creating agentic operations scenarios

Please use the Azure Architecture Center Website (https://learn.microsoft.com/en-us/azure/architecture/) and build Claude code skills with progressive disclosure (https://code.claude.com/docs/en/skills) that implement the architecture guidance there for each of the main Technology Areas described on the site. This same skill must also have excellent references to or knowledge of the usage of azure cli, terraform on azure, azure bicep, and EntraID admin. Please ensure the skill either has these docs or clear instructions on how to use them. It should also know how to install the tools if needed.
For each of the Technology Areas, we are going to create five scenarios - for each scenario follow the links and capture/document/design scenarios for how a fictional small to mid-size company would deploy or implement a minimal version of a solution in that technology area. Each scenario should involve or include all of the commands required to use automation (terraform, bicep, azure cli - whatever is easiest) to deploy and manage and then later cleanup that infrastructure, including any user accounts, role assignments, etc. There should be a discrete set of steps for 1) Deployment and Validation, 2) mid-day operations and management, 3) Cleanup and tear-down. We don't care about preserving data. Store the scenarios in the repo in the docs/scenarios directory - include detailed links and resources to the relevant azure documentation and to any documentation for any automation tools used. We should end up with a minimum of 50 distinct scenarios.
For each scenario, in this repo, under src/agents we will generate a new goal seeking agent using https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/blob/main/docs/GOAL_AGENT_GENERATOR_GUIDE.md - including in its prompt file the scenario doc itself and all the necessary links to tools, azure docs, or other info that it needs to manage that scenario. Its objective should be to instantiate the scenario in the target tenant, stay active throughout at least eight hours, performing benign management operations on the scenario, and then to cleanup/teardown the scenario. As a goal seeking agent - if it encounters any problems with the process, it should attempt to resolve them autonomously. Each agent must keep a log of all of its actions, and must post its logs to the control program (see below). All resources created must be tagged with "AzureHayMaker-managed" Each resource created should have name that is unique to this run of the scenario (not reused).


## What it must do

There will be a program that runs on a schedule (initial schedule is four times a day: once for us regions, once for Asia regions, once for Middle East, once for Europe).

Configuration required:
Target tenant ID
Target tenant SP (Client id and secret)
ANTHROPIC_API_KEY
Simulation size

The program will do the following:
Startup, validate that it has required configuration, credentials, required tools (az cli, terraform, bicep, others) and can use this credentials to access the configured tenant, can access anthropic api, can web fetch as needed.
Random select N scenario docs + agents as a function of simulation size
Create a new dedicated SP for each scenario, with a name of AzureHayMaker-<Scenario>-admin
Start a service to listen for agent logs (can be an event bus where agents put their log messages)
Starts all of the scenario agents, each in a separate azure container app (use a largeish size for each container app instance - at least 64GB RAM, 2 cpus).
Ensure that each scenario is passed the details of its SP in the environment for startup
Ensures that the container apps image has all the required reps installed.
Monitors the agent execution log messages on the bus, records these and in particular keeps a record of all of the resources provisioned.
Should have an endpoint we can query to get execution stats and lists of resources and sp names
After eight hours checks that all resources created by each scenario have been cleaned up/removed, and then force removes any remaining resources.
 ## Arch guidance
Please come up with the best design you can, consider using https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-scheduled-function to run the service.
Identify the specific azure credentials/role assignments that the sp for the service will need. Likely each delegate sp that a scenario will use will require both user assignment role and contributor.
Please think about how to protect the credentials for each SP during the operations.
## How to build it
Follow the full default workflow.
Do the groundwork portion first - be thorough as you research the azure docs, but then keep the scenarios themselves as simple and procedural as possible - focus not he azure operations each scenario should perform. All scenario operations must be scoped to a single tenant and subscription, even if the azure docs call for something else - in those cases we will have to accept simplification. In short, a scenario should reduce to almost a collection of az cli or terraform commands to run, for setup, operations, and then teardown.
After you have the groundwork portion, design the service. Come up with a design and have it reviewed multiple times by several of your various subagent specialists.
Build the code for the service, using test driven development. Go through the code review cycles of the normal default workflow.
Do two extra passes to investigate for adherence to the dev team philosophy, in particular the zero-bs philosophy - no stubs, todos, faked apis, or faked data. Prefer Quality over speed of implementation. Review and fix these issue in a loop two separate times.
