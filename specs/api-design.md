# Azure HayMaker Monitoring API Specification

## Executive Summary

This document defines the production-ready HTTP API for monitoring and querying the Azure HayMaker orchestration service. The API provides real-time visibility into execution status, scenario progress, resource inventory, and operational logs across up to 50 concurrent scenarios.

**API Version**: v1
**Base URL**: `https://{function-app-name}.azurewebsites.net/api/v1`
**Authentication**: Azure AD + API Key (fallback)
**Protocol**: HTTPS only (TLS 1.2+)

---

## Design Principles

1. **RESTful Pragmatism**: Standard REST patterns with action endpoints where clearer
2. **Single Purpose**: Each endpoint has one clear responsibility
3. **Consistent Errors**: Standard error format across all endpoints
4. **Filtering First**: Query parameters for filtering, not separate endpoints
5. **Pagination Built-in**: All list endpoints paginated by default
6. **Real-time Ready**: Support for long-polling where appropriate
7. **No Breaking Changes**: Additive changes only in v1

---

## OpenAPI 3.0 Specification

### Complete API Contract

```yaml
openapi: 3.0.0
info:
  title: Azure HayMaker Monitoring API
  version: 1.0.0
  description: |
    Production monitoring API for Azure HayMaker orchestration service.
    Provides real-time visibility into execution status, scenarios, resources, and logs.
  contact:
    name: Azure HayMaker Team
    email: haymaker-support@example.com

servers:
  - url: https://{function-app-name}.azurewebsites.net/api/v1
    description: Production environment
    variables:
      function-app-name:
        default: azurehaymaker-orchestrator-func

security:
  - AzureAD: []
  - ApiKey: []

paths:
  /status:
    get:
      summary: Get overall orchestrator status
      description: Returns current execution status, active run information, and health indicators
      operationId: getStatus
      tags:
        - Status
      responses:
        '200':
          description: Status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrchestratorStatus'
              examples:
                running:
                  summary: Orchestrator actively executing
                  value:
                    status: running
                    health: healthy
                    current_run_id: "550e8400-e29b-41d4-a716-446655440000"
                    started_at: "2025-11-14T12:00:00Z"
                    scheduled_end_at: "2025-11-14T20:00:00Z"
                    phase: monitoring
                    scenarios_count: 15
                    scenarios_completed: 8
                    scenarios_running: 6
                    scenarios_failed: 1
                idle:
                  summary: Orchestrator idle between runs
                  value:
                    status: idle
                    health: healthy
                    current_run_id: null
                    started_at: null
                    scheduled_end_at: null
                    phase: null
                    next_scheduled_run: "2025-11-14T18:00:00Z"
        '500':
          $ref: '#/components/responses/InternalServerError'
        '503':
          $ref: '#/components/responses/ServiceUnavailable'

  /runs:
    get:
      summary: List execution runs
      description: Returns paginated list of execution runs with filtering options
      operationId: listRuns
      tags:
        - Runs
      parameters:
        - $ref: '#/components/parameters/PageParameter'
        - $ref: '#/components/parameters/PageSizeParameter'
        - name: status
          in: query
          description: Filter by run status
          schema:
            type: string
            enum: [completed, in_progress, failed]
        - name: start_date
          in: query
          description: Filter runs started after this date (ISO 8601)
          schema:
            type: string
            format: date-time
        - name: end_date
          in: query
          description: Filter runs started before this date (ISO 8601)
          schema:
            type: string
            format: date-time
      responses:
        '200':
          description: Runs retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RunsListResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}:
    get:
      summary: Get detailed run information
      description: Returns comprehensive details for a specific execution run
      operationId: getRun
      tags:
        - Runs
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
      responses:
        '200':
          description: Run details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RunDetails'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/scenarios:
    get:
      summary: List scenarios for a run
      description: Returns all scenarios executed in a specific run with status and metrics
      operationId: listScenarios
      tags:
        - Scenarios
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
        - name: status
          in: query
          description: Filter by scenario status
          schema:
            type: string
            enum: [pending, running, completed, failed, cleanup_complete]
      responses:
        '200':
          description: Scenarios retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScenariosListResponse'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/scenarios/{scenario_name}:
    get:
      summary: Get detailed scenario information
      description: Returns detailed execution information for a specific scenario
      operationId: getScenario
      tags:
        - Scenarios
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
        - name: scenario_name
          in: path
          required: true
          description: Scenario identifier
          schema:
            type: string
            example: "ai-ml-01-cognitive-services-vision"
      responses:
        '200':
          description: Scenario details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScenarioDetails'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/resources:
    get:
      summary: List all resources created in a run
      description: Returns paginated list of Azure resources with lifecycle tracking
      operationId: listResources
      tags:
        - Resources
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
        - $ref: '#/components/parameters/PageParameter'
        - $ref: '#/components/parameters/PageSizeParameter'
        - name: scenario_name
          in: query
          description: Filter by scenario
          schema:
            type: string
        - name: resource_type
          in: query
          description: Filter by Azure resource type
          schema:
            type: string
            example: "Microsoft.Compute/virtualMachines"
        - name: status
          in: query
          description: Filter by resource status
          schema:
            type: string
            enum: [created, exists, deleted, deletion_failed]
      responses:
        '200':
          description: Resources retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourcesListResponse'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/service-principals:
    get:
      summary: List service principals created in a run
      description: Returns all ephemeral service principals with lifecycle status
      operationId: listServicePrincipals
      tags:
        - Service Principals
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
        - name: status
          in: query
          description: Filter by service principal status
          schema:
            type: string
            enum: [created, exists, deleted, deletion_failed]
      responses:
        '200':
          description: Service principals retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServicePrincipalsListResponse'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/logs:
    get:
      summary: Get aggregated execution logs
      description: Returns paginated agent logs with filtering and search capabilities
      operationId: listLogs
      tags:
        - Logs
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
        - $ref: '#/components/parameters/PageParameter'
        - $ref: '#/components/parameters/PageSizeParameter'
        - name: scenario_name
          in: query
          description: Filter by scenario
          schema:
            type: string
        - name: event_type
          in: query
          description: Filter by event type
          schema:
            type: string
            enum: [agent_started, resource_created, operation, cleanup_complete, error]
        - name: severity
          in: query
          description: Filter by severity
          schema:
            type: string
            enum: [info, warning, error]
        - name: start_time
          in: query
          description: Filter logs after this timestamp (ISO 8601)
          schema:
            type: string
            format: date-time
        - name: end_time
          in: query
          description: Filter logs before this timestamp (ISO 8601)
          schema:
            type: string
            format: date-time
        - name: search
          in: query
          description: Full-text search in log messages
          schema:
            type: string
      responses:
        '200':
          description: Logs retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LogsListResponse'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/logs/stream:
    get:
      summary: Stream logs in real-time
      description: Long-polling endpoint for real-time log streaming (Server-Sent Events)
      operationId: streamLogs
      tags:
        - Logs
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
        - name: scenario_name
          in: query
          description: Filter by scenario
          schema:
            type: string
        - name: since
          in: query
          description: Only return logs after this timestamp (ISO 8601)
          schema:
            type: string
            format: date-time
      responses:
        '200':
          description: Log stream established
          content:
            text/event-stream:
              schema:
                type: string
                description: Server-Sent Events stream of log entries
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /runs/{run_id}/cleanup-report:
    get:
      summary: Get cleanup verification report
      description: Returns detailed cleanup report showing resources deleted and any failures
      operationId: getCleanupReport
      tags:
        - Cleanup
      parameters:
        - $ref: '#/components/parameters/RunIdParameter'
      responses:
        '200':
          description: Cleanup report retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CleanupReport'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /health:
    get:
      summary: Health check endpoint
      description: Returns service health status (unauthenticated)
      operationId: getHealth
      tags:
        - Health
      security: []
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthCheck'
        '503':
          $ref: '#/components/responses/ServiceUnavailable'

  /metrics:
    get:
      summary: Get aggregated metrics
      description: Returns system-wide metrics and statistics
      operationId: getMetrics
      tags:
        - Metrics
      parameters:
        - name: period
          in: query
          description: Time period for metrics aggregation
          schema:
            type: string
            enum: [hour, day, week, month]
            default: day
      responses:
        '200':
          description: Metrics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Metrics'
        '500':
          $ref: '#/components/responses/InternalServerError'

components:
  securitySchemes:
    AzureAD:
      type: oauth2
      description: Azure Active Directory OAuth2 authentication
      flows:
        implicit:
          authorizationUrl: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
          scopes:
            api://azurehaymaker/.default: Access Azure HayMaker API

    ApiKey:
      type: apiKey
      description: API key authentication (fallback)
      name: X-API-Key
      in: header

  parameters:
    RunIdParameter:
      name: run_id
      in: path
      required: true
      description: Unique execution run identifier (UUID)
      schema:
        type: string
        format: uuid
        example: "550e8400-e29b-41d4-a716-446655440000"

    PageParameter:
      name: page
      in: query
      description: Page number (1-indexed)
      schema:
        type: integer
        minimum: 1
        default: 1

    PageSizeParameter:
      name: page_size
      in: query
      description: Number of items per page
      schema:
        type: integer
        minimum: 1
        maximum: 500
        default: 100

  schemas:
    OrchestratorStatus:
      type: object
      required:
        - status
        - health
      properties:
        status:
          type: string
          enum: [idle, running, error]
          description: Current orchestrator execution state
        health:
          type: string
          enum: [healthy, degraded, unhealthy]
          description: Overall service health
        current_run_id:
          type: string
          format: uuid
          nullable: true
          description: Current active run ID if running
        started_at:
          type: string
          format: date-time
          nullable: true
          description: Current run start time
        scheduled_end_at:
          type: string
          format: date-time
          nullable: true
          description: Expected completion time
        phase:
          type: string
          enum: [validation, selection, provisioning, monitoring, cleanup, reporting]
          nullable: true
          description: Current execution phase
        scenarios_count:
          type: integer
          nullable: true
          description: Total scenarios in current run
        scenarios_completed:
          type: integer
          nullable: true
          description: Scenarios that completed successfully
        scenarios_running:
          type: integer
          nullable: true
          description: Scenarios currently executing
        scenarios_failed:
          type: integer
          nullable: true
          description: Scenarios that encountered errors
        next_scheduled_run:
          type: string
          format: date-time
          nullable: true
          description: Next scheduled execution time

    RunsListResponse:
      type: object
      required:
        - runs
        - pagination
      properties:
        runs:
          type: array
          items:
            $ref: '#/components/schemas/RunSummary'
        pagination:
          $ref: '#/components/schemas/PaginationMetadata'

    RunSummary:
      type: object
      required:
        - run_id
        - started_at
        - status
        - scenarios_count
      properties:
        run_id:
          type: string
          format: uuid
        started_at:
          type: string
          format: date-time
        ended_at:
          type: string
          format: date-time
          nullable: true
        status:
          type: string
          enum: [completed, in_progress, failed]
        scenarios_count:
          type: integer
          minimum: 0
        scenarios_completed:
          type: integer
          minimum: 0
        scenarios_failed:
          type: integer
          minimum: 0
        resources_created:
          type: integer
          minimum: 0
        cleanup_status:
          type: string
          enum: [verified, partial, failed, pending]

    RunDetails:
      type: object
      required:
        - run_id
        - started_at
        - status
        - scenarios
        - cleanup_verification
      properties:
        run_id:
          type: string
          format: uuid
        started_at:
          type: string
          format: date-time
        ended_at:
          type: string
          format: date-time
          nullable: true
        status:
          type: string
          enum: [completed, in_progress, failed]
        phase:
          type: string
          enum: [validation, selection, provisioning, monitoring, cleanup, reporting, completed]
        simulation_size:
          type: string
          enum: [small, medium, large]
        scenarios:
          type: array
          items:
            $ref: '#/components/schemas/ScenarioSummary'
        total_resources:
          type: integer
          minimum: 0
        total_service_principals:
          type: integer
          minimum: 0
        cleanup_verification:
          $ref: '#/components/schemas/CleanupVerification'
        errors:
          type: array
          items:
            $ref: '#/components/schemas/ExecutionError'

    ScenarioSummary:
      type: object
      required:
        - scenario_name
        - status
      properties:
        scenario_name:
          type: string
          example: "ai-ml-01-cognitive-services-vision"
        technology_area:
          type: string
          example: "AI/ML"
        agent_id:
          type: string
          description: Container App name
        sp_name:
          type: string
          example: "AzureHayMaker-vision-admin"
        status:
          type: string
          enum: [pending, running, completed, failed, cleanup_complete]
        started_at:
          type: string
          format: date-time
          nullable: true
        ended_at:
          type: string
          format: date-time
          nullable: true
        resources_created:
          type: integer
          minimum: 0
        cleanup_status:
          type: string
          enum: [pending, in_progress, complete, failed]

    ScenariosListResponse:
      type: object
      required:
        - run_id
        - scenarios
      properties:
        run_id:
          type: string
          format: uuid
        scenarios:
          type: array
          items:
            $ref: '#/components/schemas/ScenarioSummary'

    ScenarioDetails:
      type: object
      required:
        - scenario_name
        - run_id
        - status
      properties:
        scenario_name:
          type: string
        run_id:
          type: string
          format: uuid
        technology_area:
          type: string
        agent_id:
          type: string
        container_app_resource_id:
          type: string
        sp_name:
          type: string
        sp_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, running, completed, failed, cleanup_complete]
        started_at:
          type: string
          format: date-time
          nullable: true
        ended_at:
          type: string
          format: date-time
          nullable: true
        duration_seconds:
          type: integer
          minimum: 0
          nullable: true
        phase:
          type: string
          enum: [deployment, operations, cleanup, completed]
          nullable: true
        resources:
          type: array
          items:
            $ref: '#/components/schemas/Resource'
        operations_performed:
          type: integer
          minimum: 0
        errors:
          type: array
          items:
            $ref: '#/components/schemas/ExecutionError'

    ResourcesListResponse:
      type: object
      required:
        - run_id
        - resources
        - pagination
      properties:
        run_id:
          type: string
          format: uuid
        resources:
          type: array
          items:
            $ref: '#/components/schemas/Resource'
        pagination:
          $ref: '#/components/schemas/PaginationMetadata'

    Resource:
      type: object
      required:
        - resource_id
        - resource_type
        - scenario_name
        - status
      properties:
        resource_id:
          type: string
          description: Azure resource ID
          example: "/subscriptions/12345/resourceGroups/haymaker-rg/providers/Microsoft.Storage/storageAccounts/haymakerstorage"
        resource_type:
          type: string
          description: Azure resource type
          example: "Microsoft.Storage/storageAccounts"
        resource_name:
          type: string
          example: "haymakerstorage"
        scenario_name:
          type: string
        created_at:
          type: string
          format: date-time
        deleted_at:
          type: string
          format: date-time
          nullable: true
        status:
          type: string
          enum: [created, exists, deleted, deletion_failed]
        deletion_attempts:
          type: integer
          minimum: 0
          default: 0
        tags:
          type: object
          additionalProperties:
            type: string
          example:
            AzureHayMaker-managed: "true"
            RunId: "550e8400-e29b-41d4-a716-446655440000"
            Scenario: "ai-ml-01-cognitive-services-vision"

    ServicePrincipalsListResponse:
      type: object
      required:
        - run_id
        - service_principals
      properties:
        run_id:
          type: string
          format: uuid
        service_principals:
          type: array
          items:
            $ref: '#/components/schemas/ServicePrincipal'

    ServicePrincipal:
      type: object
      required:
        - sp_name
        - sp_id
        - scenario_name
        - status
      properties:
        sp_name:
          type: string
          example: "AzureHayMaker-vision-admin"
        sp_id:
          type: string
          format: uuid
          description: Application (client) ID
        principal_id:
          type: string
          format: uuid
          description: Object ID in Entra ID
        scenario_name:
          type: string
        created_at:
          type: string
          format: date-time
        deleted_at:
          type: string
          format: date-time
          nullable: true
        status:
          type: string
          enum: [created, exists, deleted, deletion_failed]
        roles_assigned:
          type: array
          items:
            type: string
          example:
            - "User Access Administrator"
            - "Contributor"

    LogsListResponse:
      type: object
      required:
        - run_id
        - logs
        - pagination
      properties:
        run_id:
          type: string
          format: uuid
        logs:
          type: array
          items:
            $ref: '#/components/schemas/LogEntry'
        pagination:
          $ref: '#/components/schemas/PaginationMetadata'

    LogEntry:
      type: object
      required:
        - timestamp
        - event_type
        - scenario_name
        - message
        - severity
      properties:
        timestamp:
          type: string
          format: date-time
        event_type:
          type: string
          enum: [agent_started, resource_created, operation, cleanup_complete, error]
        scenario_name:
          type: string
        agent_id:
          type: string
        sp_name:
          type: string
        message:
          type: string
        resource_id:
          type: string
          nullable: true
        resource_type:
          type: string
          nullable: true
        severity:
          type: string
          enum: [info, warning, error]
        details:
          type: object
          additionalProperties: true
          nullable: true

    CleanupReport:
      type: object
      required:
        - run_id
        - status
        - verification
        - deletions
      properties:
        run_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [verified, partial, failed]
        verification:
          $ref: '#/components/schemas/CleanupVerification'
        deletions:
          type: array
          items:
            $ref: '#/components/schemas/ResourceDeletion'
        service_principals_deleted:
          type: array
          items:
            type: string
        forced_cleanup_required:
          type: boolean
        forced_cleanup_executed_at:
          type: string
          format: date-time
          nullable: true

    CleanupVerification:
      type: object
      required:
        - expected_deleted
        - actually_deleted
        - forced_deletions
      properties:
        expected_deleted:
          type: integer
          minimum: 0
          description: Number of resources expected to be deleted
        actually_deleted:
          type: integer
          minimum: 0
          description: Number of resources confirmed deleted
        forced_deletions:
          type: integer
          minimum: 0
          description: Number of resources force-deleted by orchestrator
        deletion_failures:
          type: integer
          minimum: 0
          description: Number of resources that failed to delete

    ResourceDeletion:
      type: object
      required:
        - resource_id
        - status
        - attempts
      properties:
        resource_id:
          type: string
        resource_type:
          type: string
        status:
          type: string
          enum: [deleted, failed]
        attempts:
          type: integer
          minimum: 1
        deleted_at:
          type: string
          format: date-time
          nullable: true
        error:
          type: string
          nullable: true

    ExecutionError:
      type: object
      required:
        - timestamp
        - error_code
        - message
      properties:
        timestamp:
          type: string
          format: date-time
        error_code:
          type: string
          example: "SP_CREATION_FAILED"
        message:
          type: string
        scenario_name:
          type: string
          nullable: true
        phase:
          type: string
          nullable: true
        details:
          type: object
          additionalProperties: true
          nullable: true

    HealthCheck:
      type: object
      required:
        - status
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        version:
          type: string
          example: "1.0.0"
        checks:
          type: object
          properties:
            key_vault:
              type: string
              enum: [pass, fail]
            service_bus:
              type: string
              enum: [pass, fail]
            storage:
              type: string
              enum: [pass, fail]
            azure_api:
              type: string
              enum: [pass, fail]

    Metrics:
      type: object
      properties:
        period:
          type: string
          enum: [hour, day, week, month]
        total_runs:
          type: integer
          minimum: 0
        successful_runs:
          type: integer
          minimum: 0
        failed_runs:
          type: integer
          minimum: 0
        total_scenarios_executed:
          type: integer
          minimum: 0
        total_resources_created:
          type: integer
          minimum: 0
        total_resources_deleted:
          type: integer
          minimum: 0
        cleanup_success_rate:
          type: number
          format: float
          minimum: 0
          maximum: 1
          description: Percentage of successful cleanups (0-1)
        average_execution_duration_seconds:
          type: integer
          minimum: 0
        average_resources_per_scenario:
          type: number
          format: float

    PaginationMetadata:
      type: object
      required:
        - page
        - page_size
        - total_items
        - total_pages
      properties:
        page:
          type: integer
          minimum: 1
        page_size:
          type: integer
          minimum: 1
        total_items:
          type: integer
          minimum: 0
        total_pages:
          type: integer
          minimum: 0
        has_next:
          type: boolean
        has_previous:
          type: boolean

    Error:
      type: object
      required:
        - error
      properties:
        error:
          type: object
          required:
            - code
            - message
          properties:
            code:
              type: string
              description: Machine-readable error code
              example: "RUN_NOT_FOUND"
            message:
              type: string
              description: Human-readable error message
              example: "Run with ID '550e8400-e29b-41d4-a716-446655440000' not found"
            details:
              type: object
              additionalProperties: true
              description: Additional error context
            trace_id:
              type: string
              description: Request trace ID for debugging

  responses:
    BadRequest:
      description: Invalid request parameters
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            error:
              code: "INVALID_PARAMETER"
              message: "Invalid page_size: must be between 1 and 500"
              details:
                parameter: "page_size"
                value: 1000
              trace_id: "abc123"

    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            error:
              code: "RUN_NOT_FOUND"
              message: "Run with ID '550e8400-e29b-41d4-a716-446655440000' not found"
              details:
                run_id: "550e8400-e29b-41d4-a716-446655440000"
              trace_id: "xyz789"

    InternalServerError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            error:
              code: "INTERNAL_ERROR"
              message: "An unexpected error occurred while processing your request"
              trace_id: "err456"

    ServiceUnavailable:
      description: Service temporarily unavailable
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            error:
              code: "SERVICE_UNAVAILABLE"
              message: "Service is temporarily unavailable. Please try again later."
              trace_id: "svc789"
```

---

## Authentication and Authorization

### Primary: Azure Active Directory (OAuth2)

**Flow**: Implicit or Authorization Code with PKCE

**Token Endpoint**: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`

**Required Scope**: `api://azurehaymaker/.default`

**Example Request**:
```http
GET /api/v1/status HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**RBAC Roles**:
- `HayMaker.Reader`: Read-only access to all endpoints
- `HayMaker.Operator`: Read access + ability to trigger manual cleanup (future)
- `HayMaker.Admin`: Full access (future administrative endpoints)

**Token Validation**:
- Validate token signature using Azure AD public keys
- Check token expiration (`exp` claim)
- Verify audience (`aud` claim matches API app ID)
- Verify issuer (`iss` claim matches tenant)

### Fallback: API Key

**Use Case**: Automated monitoring systems, non-interactive clients

**Storage**: API keys stored in Azure Key Vault

**Header**: `X-API-Key: <api-key>`

**Example Request**:
```http
GET /api/v1/status HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
X-API-Key: hm_prod_a1b2c3d4e5f6g7h8i9j0
```

**Key Format**: `hm_{environment}_{32-char-random}`

**Rotation**: Monthly rotation recommended, old keys valid for 7 days overlap

**Rate Limiting**: 1000 requests per hour per API key

---

## Error Handling

### Standard Error Format

All errors return consistent JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "value"
    },
    "trace_id": "unique-request-id"
  }
}
```

### Error Codes

| Code | HTTP Status | Description | Retry? |
|------|-------------|-------------|--------|
| `INVALID_PARAMETER` | 400 | Invalid query parameter or request body | No |
| `MISSING_PARAMETER` | 400 | Required parameter not provided | No |
| `INVALID_RUN_ID` | 400 | Run ID format is invalid (not UUID) | No |
| `UNAUTHORIZED` | 401 | Authentication credentials missing or invalid | No |
| `FORBIDDEN` | 403 | Insufficient permissions for requested resource | No |
| `RUN_NOT_FOUND` | 404 | Run ID does not exist | No |
| `SCENARIO_NOT_FOUND` | 404 | Scenario not found in specified run | No |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests, rate limit exceeded | Yes (after delay) |
| `INTERNAL_ERROR` | 500 | Unexpected server error | Yes (with backoff) |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable | Yes (with backoff) |
| `STORAGE_ERROR` | 500 | Error accessing storage account | Yes (with backoff) |
| `KEY_VAULT_ERROR` | 500 | Error accessing Key Vault | Yes (with backoff) |

### Error Response Examples

**Invalid Parameter**:
```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid status filter value: 'running_fast'. Allowed values: completed, in_progress, failed",
    "details": {
      "parameter": "status",
      "provided_value": "running_fast",
      "allowed_values": ["completed", "in_progress", "failed"]
    },
    "trace_id": "req-123-abc"
  }
}
```

**Run Not Found**:
```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Run with ID '550e8400-e29b-41d4-a716-446655440000' not found",
    "details": {
      "run_id": "550e8400-e29b-41d4-a716-446655440000"
    },
    "trace_id": "req-456-def"
  }
}
```

**Rate Limit Exceeded**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Maximum 1000 requests per hour.",
    "details": {
      "limit": 1000,
      "reset_at": "2025-11-14T13:00:00Z"
    },
    "trace_id": "req-789-ghi"
  }
}
```

---

## Rate Limiting

### Limits by Authentication Method

| Authentication | Requests per Minute | Requests per Hour |
|----------------|---------------------|-------------------|
| Azure AD Token | 600 | 10,000 |
| API Key | 60 | 1,000 |
| Unauthenticated (health only) | 60 | 600 |

### Rate Limit Headers

Every response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 542
X-RateLimit-Reset: 1699977600
Retry-After: 30
```

**Headers**:
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds to wait before retrying (only on 429 responses)

### Rate Limit Strategy

**Algorithm**: Sliding window counter per authentication principal

**Scope**: Per Azure AD user or per API key

**Enforcement**: Azure API Management or Azure Functions rate limiting

**Burst Allowance**: Brief bursts up to 2x limit allowed, averaged over minute

---

## Versioning Strategy

### Version 1 (Current)

**Base URL**: `/api/v1`

**Stability Promise**: No breaking changes in v1

**Additive Changes Allowed**:
- New optional query parameters
- New fields in response bodies (clients must ignore unknown fields)
- New endpoints
- New enum values (clients must handle unknown values gracefully)

**Breaking Changes** (would require v2):
- Removing endpoints
- Removing response fields
- Changing field types
- Making optional parameters required
- Changing URL structure
- Changing authentication requirements

### Future Versioning

**When to Version**: Only when breaking changes unavoidable

**Version Format**: Major version in URL path (`/api/v2`)

**Deprecation Policy**:
- v1 supported for 12 months after v2 release
- 6-month deprecation notice before removal
- `Sunset` header indicates deprecation date

**Example Sunset Header**:
```http
HTTP/1.1 200 OK
Sunset: Wed, 14 Nov 2026 00:00:00 GMT
Link: <https://docs.azurehaymaker.com/api/v2>; rel="alternate"
```

---

## Performance and Caching

### Response Times (p95)

| Endpoint | Target | Implementation Note |
|----------|--------|---------------------|
| `GET /status` | < 200ms | Cached, 10s TTL |
| `GET /runs` | < 500ms | Indexed storage queries |
| `GET /runs/{run_id}` | < 300ms | Cached, 30s TTL |
| `GET /runs/{run_id}/resources` | < 1000ms | Paginated, indexed |
| `GET /runs/{run_id}/logs` | < 1500ms | Paginated, blob storage |
| `GET /health` | < 100ms | No external dependencies |

### Caching Strategy

**Status Endpoint** (`GET /status`):
- Cache duration: 10 seconds
- Cache key: `status:current`
- Invalidation: On orchestrator state change

**Run Details** (`GET /runs/{run_id}`):
- Cache duration: 30 seconds for in-progress runs
- Cache duration: 1 hour for completed runs
- Cache key: `run:{run_id}`
- Invalidation: On run state change

**Cache Headers**:
```http
Cache-Control: private, max-age=30
ETag: "v1-run-550e8400"
Last-Modified: Wed, 14 Nov 2025 12:00:00 GMT
```

**Client Caching**:
- Clients should respect `Cache-Control` headers
- Use `If-None-Match` with ETags for efficient polling
- 304 Not Modified returned when content unchanged

### Pagination Best Practices

**Default Page Size**: 100 items

**Maximum Page Size**: 500 items

**Pagination Links** (future enhancement):
```json
{
  "runs": [...],
  "pagination": {
    "page": 2,
    "page_size": 100,
    "total_items": 450,
    "total_pages": 5,
    "has_next": true,
    "has_previous": true
  },
  "links": {
    "first": "/api/v1/runs?page=1&page_size=100",
    "previous": "/api/v1/runs?page=1&page_size=100",
    "next": "/api/v1/runs?page=3&page_size=100",
    "last": "/api/v1/runs?page=5&page_size=100"
  }
}
```

---

## Real-Time Features

### Log Streaming (Server-Sent Events)

**Endpoint**: `GET /runs/{run_id}/logs/stream`

**Protocol**: Server-Sent Events (SSE)

**Connection**: Long-lived HTTP connection (max 1 hour)

**Example Request**:
```http
GET /api/v1/runs/550e8400-e29b-41d4-a716-446655440000/logs/stream?scenario_name=ai-ml-01-cognitive-services-vision HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
Accept: text/event-stream
```

**Example Response**:
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: log
data: {"timestamp":"2025-11-14T12:05:23Z","event_type":"resource_created","scenario_name":"ai-ml-01-cognitive-services-vision","message":"Storage account created","severity":"info"}

event: log
data: {"timestamp":"2025-11-14T12:06:45Z","event_type":"operation","scenario_name":"ai-ml-01-cognitive-services-vision","message":"Uploaded test blob","severity":"info"}

event: heartbeat
data: {"timestamp":"2025-11-14T12:07:00Z"}
```

**Event Types**:
- `log`: Agent log entry
- `heartbeat`: Keep-alive (every 15 seconds)
- `error`: Error event
- `complete`: Run completed (connection will close)

**Client Implementation**:
```javascript
const eventSource = new EventSource('/api/v1/runs/550e8400-e29b-41d4-a716-446655440000/logs/stream');

eventSource.addEventListener('log', (event) => {
  const log = JSON.parse(event.data);
  console.log(log.message);
});

eventSource.addEventListener('error', (error) => {
  console.error('Connection error', error);
  eventSource.close();
});
```

**Limitations**:
- Maximum connection duration: 1 hour
- Automatic reconnection required by client
- No message replay (use regular log endpoint with `since` parameter for history)

---

## Request/Response Examples

### Example 1: Get Current Status

**Request**:
```http
GET /api/v1/status HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=10

{
  "status": "running",
  "health": "healthy",
  "current_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2025-11-14T12:00:00Z",
  "scheduled_end_at": "2025-11-14T20:00:00Z",
  "phase": "monitoring",
  "scenarios_count": 15,
  "scenarios_completed": 8,
  "scenarios_running": 6,
  "scenarios_failed": 1,
  "next_scheduled_run": null
}
```

### Example 2: List Recent Runs

**Request**:
```http
GET /api/v1/runs?page=1&page_size=5&status=completed HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "runs": [
    {
      "run_id": "450e8400-e29b-41d4-a716-446655440001",
      "started_at": "2025-11-13T18:00:00Z",
      "ended_at": "2025-11-14T02:05:23Z",
      "status": "completed",
      "scenarios_count": 15,
      "scenarios_completed": 14,
      "scenarios_failed": 1,
      "resources_created": 287,
      "cleanup_status": "verified"
    },
    {
      "run_id": "350e8400-e29b-41d4-a716-446655440002",
      "started_at": "2025-11-13T12:00:00Z",
      "ended_at": "2025-11-13T20:03:45Z",
      "status": "completed",
      "scenarios_count": 15,
      "scenarios_completed": 15,
      "scenarios_failed": 0,
      "resources_created": 302,
      "cleanup_status": "verified"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 5,
    "total_items": 42,
    "total_pages": 9,
    "has_next": true,
    "has_previous": false
  }
}
```

### Example 3: Get Run Details

**Request**:
```http
GET /api/v1/runs/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2025-11-14T12:00:00Z",
  "ended_at": "2025-11-14T20:05:23Z",
  "status": "completed",
  "phase": "completed",
  "simulation_size": "medium",
  "scenarios": [
    {
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "technology_area": "AI/ML",
      "agent_id": "container-app-vision-abc123",
      "sp_name": "AzureHayMaker-vision-admin",
      "status": "cleanup_complete",
      "started_at": "2025-11-14T12:05:00Z",
      "ended_at": "2025-11-14T20:02:15Z",
      "resources_created": 25,
      "cleanup_status": "complete"
    },
    {
      "scenario_name": "networking-02-vnet-peering",
      "technology_area": "Networking",
      "agent_id": "container-app-network-def456",
      "sp_name": "AzureHayMaker-network-admin",
      "status": "cleanup_complete",
      "started_at": "2025-11-14T12:06:30Z",
      "ended_at": "2025-11-14T20:03:45Z",
      "resources_created": 18,
      "cleanup_status": "complete"
    }
  ],
  "total_resources": 287,
  "total_service_principals": 15,
  "cleanup_verification": {
    "expected_deleted": 287,
    "actually_deleted": 287,
    "forced_deletions": 3,
    "deletion_failures": 0
  },
  "errors": []
}
```

### Example 4: Get Resources for Run

**Request**:
```http
GET /api/v1/runs/550e8400-e29b-41d4-a716-446655440000/resources?scenario_name=ai-ml-01-cognitive-services-vision&page=1&page_size=10 HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "resources": [
    {
      "resource_id": "/subscriptions/12345/resourceGroups/haymaker-vision-rg",
      "resource_type": "Microsoft.Resources/resourceGroups",
      "resource_name": "haymaker-vision-rg",
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "created_at": "2025-11-14T12:05:30Z",
      "deleted_at": "2025-11-14T20:02:00Z",
      "status": "deleted",
      "deletion_attempts": 1,
      "tags": {
        "AzureHayMaker-managed": "true",
        "RunId": "550e8400-e29b-41d4-a716-446655440000",
        "Scenario": "ai-ml-01-cognitive-services-vision"
      }
    },
    {
      "resource_id": "/subscriptions/12345/resourceGroups/haymaker-vision-rg/providers/Microsoft.CognitiveServices/accounts/haymaker-vision-cs",
      "resource_type": "Microsoft.CognitiveServices/accounts",
      "resource_name": "haymaker-vision-cs",
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "created_at": "2025-11-14T12:08:15Z",
      "deleted_at": "2025-11-14T20:01:30Z",
      "status": "deleted",
      "deletion_attempts": 1,
      "tags": {
        "AzureHayMaker-managed": "true",
        "RunId": "550e8400-e29b-41d4-a716-446655440000",
        "Scenario": "ai-ml-01-cognitive-services-vision"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 25,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false
  }
}
```

### Example 5: Get Logs with Filtering

**Request**:
```http
GET /api/v1/runs/550e8400-e29b-41d4-a716-446655440000/logs?event_type=error&page=1&page_size=20 HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "logs": [
    {
      "timestamp": "2025-11-14T14:23:45Z",
      "event_type": "error",
      "scenario_name": "compute-03-vm-scale-set",
      "agent_id": "container-app-compute-xyz789",
      "sp_name": "AzureHayMaker-compute-admin",
      "message": "Failed to create VM scale set: QuotaExceeded",
      "resource_id": null,
      "resource_type": null,
      "severity": "error",
      "details": {
        "error_code": "QuotaExceeded",
        "quota_type": "cores",
        "requested": 16,
        "available": 8
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

### Example 6: Get Cleanup Report

**Request**:
```http
GET /api/v1/runs/550e8400-e29b-41d4-a716-446655440000/cleanup-report HTTP/1.1
Host: azurehaymaker-orchestrator-func.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "verified",
  "verification": {
    "expected_deleted": 287,
    "actually_deleted": 287,
    "forced_deletions": 3,
    "deletion_failures": 0
  },
  "deletions": [
    {
      "resource_id": "/subscriptions/12345/resourceGroups/haymaker-storage-rg/providers/Microsoft.Storage/storageAccounts/haymakerstorage123",
      "resource_type": "Microsoft.Storage/storageAccounts",
      "status": "deleted",
      "attempts": 2,
      "deleted_at": "2025-11-14T20:03:15Z",
      "error": null
    },
    {
      "resource_id": "/subscriptions/12345/resourceGroups/haymaker-db-rg/providers/Microsoft.Sql/servers/haymakerdb",
      "resource_type": "Microsoft.Sql/servers",
      "status": "deleted",
      "attempts": 1,
      "deleted_at": "2025-11-14T20:01:45Z",
      "error": null
    }
  ],
  "service_principals_deleted": [
    "AzureHayMaker-vision-admin",
    "AzureHayMaker-network-admin",
    "AzureHayMaker-storage-admin"
  ],
  "forced_cleanup_required": true,
  "forced_cleanup_executed_at": "2025-11-14T20:03:00Z"
}
```

---

## Implementation Guidance for Builder Agent

### Module Structure

```
src/orchestrator/api/
├── __init__.py
├── function_app.py          # Azure Functions app definition
├── auth.py                  # Authentication/authorization middleware
├── handlers/
│   ├── __init__.py
│   ├── status.py            # Status endpoint handler
│   ├── runs.py              # Runs endpoints handlers
│   ├── scenarios.py         # Scenarios endpoints handlers
│   ├── resources.py         # Resources endpoints handlers
│   ├── service_principals.py # SPs endpoints handlers
│   ├── logs.py              # Logs endpoints handlers
│   ├── cleanup.py           # Cleanup report handler
│   ├── health.py            # Health check handler
│   └── metrics.py           # Metrics handler
├── models.py                # Pydantic models for request/response
├── errors.py                # Error handling utilities
├── pagination.py            # Pagination utilities
├── cache.py                 # Caching layer
└── rate_limiter.py          # Rate limiting logic
```

### Key Implementation Points

1. **Azure Functions HTTP Triggers**:
   - Use Python v2 programming model
   - One function per endpoint (or route group)
   - Async handlers for all I/O operations

2. **Authentication Middleware**:
   - Validate Azure AD tokens using `azure-identity`
   - Validate API keys against Key Vault
   - Attach principal information to request context

3. **Response Models**:
   - Use Pydantic for all response serialization
   - Consistent JSON formatting (snake_case)
   - Automatic validation

4. **Storage Queries**:
   - Read from Azure Storage (execution-state, execution-reports)
   - Use blob metadata for efficient filtering
   - Implement server-side pagination

5. **Caching**:
   - Use Azure Redis Cache or in-memory cache
   - Cache status endpoint (10s TTL)
   - Cache completed run details (1h TTL)
   - Generate ETags for conditional requests

6. **Rate Limiting**:
   - Use Azure API Management for rate limiting
   - Or implement with Azure Redis (sliding window counter)
   - Return proper 429 responses with Retry-After header

7. **Error Handling**:
   - Catch all exceptions at handler level
   - Map to standard error format
   - Generate trace IDs for correlation
   - Log errors to Application Insights

8. **Testing**:
   - Unit tests for all handlers (mock storage)
   - Integration tests with test storage account
   - Contract tests against OpenAPI spec
   - Load tests for rate limiting validation

### Example Handler Implementation

```python
# src/orchestrator/api/handlers/status.py

import azure.functions as func
from typing import Dict, Any
from ..models import OrchestratorStatus
from ..cache import cache_response
from ..errors import handle_errors

@handle_errors
@cache_response(ttl_seconds=10)
async def get_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/v1/status
    Returns current orchestrator status
    """
    # Read current state from storage
    state = await read_execution_state()

    # Build response
    status = OrchestratorStatus(
        status=state.get("status", "idle"),
        health="healthy",
        current_run_id=state.get("run_id"),
        started_at=state.get("started_at"),
        scheduled_end_at=state.get("scheduled_end_at"),
        phase=state.get("phase"),
        scenarios_count=state.get("scenarios_count"),
        scenarios_completed=state.get("scenarios_completed"),
        scenarios_running=state.get("scenarios_running"),
        scenarios_failed=state.get("scenarios_failed"),
        next_scheduled_run=calculate_next_run()
    )

    return func.HttpResponse(
        body=status.model_dump_json(),
        status_code=200,
        mimetype="application/json"
    )
```

---

## Security Considerations

### Input Validation

1. **Path Parameters**:
   - Validate `run_id` is valid UUID format
   - Validate `scenario_name` matches allowed pattern `^[a-z0-9-]+$`

2. **Query Parameters**:
   - Validate enum values match allowed values
   - Validate numeric ranges (page_size: 1-500)
   - Validate date formats (ISO 8601)
   - Sanitize search strings to prevent injection

3. **Rate Limiting**:
   - Enforce per-principal limits
   - Block repeated 401/403 attempts (potential attack)
   - Exponential backoff for failed auth attempts

### Data Protection

1. **Secrets Redaction**:
   - Never return service principal secrets
   - Redact sensitive fields in logs endpoint
   - Scrub API keys from error messages

2. **Authorization Checks**:
   - Verify principal has access to requested run
   - Future: Multi-tenant isolation (if needed)

3. **Audit Logging**:
   - Log all API access to Application Insights
   - Include principal, endpoint, status code
   - Flag suspicious patterns (bulk data access)

---

## Monitoring and Observability

### Metrics to Track

1. **API Metrics** (Application Insights):
   - Request count by endpoint
   - Response time (p50, p95, p99)
   - Error rate by endpoint
   - Rate limit hits
   - Cache hit rate

2. **Business Metrics**:
   - Most queried runs
   - Most queried scenarios
   - Average client session duration
   - Unique API consumers per day

### Alerts

1. **Critical**:
   - API error rate > 5% (5 min window)
   - API availability < 99% (15 min window)
   - Authentication failures > 100/min

2. **Warning**:
   - Response time p95 > 2s (5 min window)
   - Rate limit hits > 50/min
   - Cache miss rate > 80%

### Application Insights Queries

**API Response Times**:
```kusto
requests
| where timestamp > ago(1h)
| where url contains "/api/v1/"
| summarize
    p50=percentile(duration, 50),
    p95=percentile(duration, 95),
    p99=percentile(duration, 99)
  by operation_Name
| order by p95 desc
```

**Error Rate by Endpoint**:
```kusto
requests
| where timestamp > ago(1h)
| where url contains "/api/v1/"
| summarize
    total=count(),
    errors=countif(resultCode >= 500)
  by operation_Name
| extend error_rate = todouble(errors) / todouble(total) * 100
| order by error_rate desc
```

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 80% minimum

**Test Cases**:
- Valid requests return expected responses
- Invalid parameters return 400 errors
- Missing authentication returns 401
- Non-existent resources return 404
- Rate limiting enforced correctly
- Pagination works correctly
- Filtering works correctly
- Error format is consistent

**Example Test**:
```python
@pytest.mark.asyncio
async def test_get_status_returns_current_run():
    # Arrange
    mock_storage = create_mock_storage({
        "status": "running",
        "run_id": "550e8400-e29b-41d4-a716-446655440000"
    })

    # Act
    response = await get_status(mock_request, mock_storage)

    # Assert
    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["status"] == "running"
    assert data["current_run_id"] == "550e8400-e29b-41d4-a716-446655440000"
```

### Integration Tests

**Test Environment**: Dedicated test storage account

**Test Cases**:
- End-to-end API calls with real storage
- Authentication with test Azure AD tokens
- Pagination across multiple pages
- Log streaming connection stability
- Cache behavior verification

### Contract Tests

**Tool**: Schemathesis or Dredd

**Purpose**: Validate API responses match OpenAPI spec

**Execution**: Run against deployed test environment

### Load Tests

**Tool**: Azure Load Testing or Locust

**Scenarios**:
- 100 concurrent clients polling status endpoint
- 50 concurrent clients streaming logs
- 1000 requests/min distributed across all endpoints

**Success Criteria**:
- p95 response time < 2s
- Error rate < 1%
- No rate limit false positives

---

## Deployment Checklist

### Pre-Deployment

- [ ] OpenAPI spec validated (no errors)
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Contract tests passing against spec
- [ ] Load tests passing
- [ ] Security review completed
- [ ] Authentication configured (Azure AD + API keys)
- [ ] Rate limiting configured
- [ ] Caching configured
- [ ] Monitoring dashboards created
- [ ] Alerts configured
- [ ] Documentation published

### Post-Deployment

- [ ] Smoke test all endpoints
- [ ] Verify authentication works
- [ ] Verify rate limiting works
- [ ] Verify caching works
- [ ] Monitor for errors (24 hours)
- [ ] Monitor performance metrics
- [ ] Test log streaming with real run
- [ ] Verify API keys work
- [ ] Test from external monitoring tool

---

## Future Enhancements (Not in v1)

1. **Webhooks**: Push notifications for run completion, errors
2. **GraphQL**: Alternative query interface for complex filtering
3. **Bulk Export**: Export all run data as JSON/CSV
4. **Run Comparison**: Compare two runs side-by-side
5. **Scenario Analytics**: Historical scenario success rates
6. **Cost Tracking**: Per-run cost breakdown
7. **Manual Triggers**: API to trigger manual runs (POST /runs)
8. **Run Cancellation**: API to cancel in-progress runs (DELETE /runs/{run_id})
9. **Live Updates**: WebSocket alternative to SSE
10. **API SDK**: Python/TypeScript client libraries

---

## Appendix A: Complete Error Code Reference

| Code | HTTP | Category | Description | Client Action |
|------|------|----------|-------------|---------------|
| `INVALID_PARAMETER` | 400 | Validation | Invalid query parameter | Fix parameter value |
| `MISSING_PARAMETER` | 400 | Validation | Required parameter missing | Add parameter |
| `INVALID_RUN_ID` | 400 | Validation | Run ID format invalid | Use valid UUID |
| `INVALID_DATE_FORMAT` | 400 | Validation | Date not ISO 8601 | Use ISO 8601 format |
| `PAGE_SIZE_EXCEEDED` | 400 | Validation | page_size > 500 | Use page_size <= 500 |
| `UNAUTHORIZED` | 401 | Auth | Auth missing/invalid | Provide valid auth |
| `TOKEN_EXPIRED` | 401 | Auth | Azure AD token expired | Refresh token |
| `INVALID_API_KEY` | 401 | Auth | API key invalid | Check API key |
| `FORBIDDEN` | 403 | Auth | Insufficient permissions | Check RBAC roles |
| `RUN_NOT_FOUND` | 404 | Resource | Run does not exist | Verify run_id |
| `SCENARIO_NOT_FOUND` | 404 | Resource | Scenario not in run | Verify scenario_name |
| `RESOURCE_NOT_FOUND` | 404 | Resource | Generic not found | Verify resource exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Throttling | Too many requests | Wait and retry |
| `INTERNAL_ERROR` | 500 | Server | Unexpected error | Retry with backoff |
| `STORAGE_ERROR` | 500 | Server | Storage access failed | Retry with backoff |
| `KEY_VAULT_ERROR` | 500 | Server | Key Vault access failed | Retry with backoff |
| `SERVICE_UNAVAILABLE` | 503 | Server | Service down | Retry with backoff |

---

## Appendix B: API Client Examples

### Python Client Example

```python
import requests
from typing import List, Dict, Any

class AzureHayMakerClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json"
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        response = requests.get(
            f"{self.base_url}/api/v1/status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def list_runs(self, status: str = None, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """List execution runs with optional filtering"""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status

        response = requests.get(
            f"{self.base_url}/api/v1/runs",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_run_details(self, run_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific run"""
        response = requests.get(
            f"{self.base_url}/api/v1/runs/{run_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_run_resources(self, run_id: str, scenario_name: str = None) -> List[Dict[str, Any]]:
        """Get all resources for a run, optionally filtered by scenario"""
        params = {}
        if scenario_name:
            params["scenario_name"] = scenario_name

        all_resources = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(
                f"{self.base_url}/api/v1/runs/{run_id}/resources",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            all_resources.extend(data["resources"])

            if not data["pagination"]["has_next"]:
                break

            page += 1

        return all_resources

# Usage
client = AzureHayMakerClient(
    base_url="https://azurehaymaker-orchestrator-func.azurewebsites.net",
    api_key="hm_prod_a1b2c3d4e5f6g7h8i9j0"
)

status = client.get_status()
print(f"Current status: {status['status']}")

if status['current_run_id']:
    run_details = client.get_run_details(status['current_run_id'])
    print(f"Run has {run_details['total_resources']} resources")
```

### cURL Examples

**Get Status**:
```bash
curl -X GET \
  "https://azurehaymaker-orchestrator-func.azurewebsites.net/api/v1/status" \
  -H "X-API-Key: hm_prod_a1b2c3d4e5f6g7h8i9j0"
```

**List Runs**:
```bash
curl -X GET \
  "https://azurehaymaker-orchestrator-func.azurewebsites.net/api/v1/runs?status=completed&page=1&page_size=10" \
  -H "X-API-Key: hm_prod_a1b2c3d4e5f6g7h8i9j0"
```

**Get Run Details**:
```bash
curl -X GET \
  "https://azurehaymaker-orchestrator-func.azurewebsites.net/api/v1/runs/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: hm_prod_a1b2c3d4e5f6g7h8i9j0"
```

**Stream Logs**:
```bash
curl -X GET \
  -N \
  -H "Accept: text/event-stream" \
  -H "X-API-Key: hm_prod_a1b2c3d4e5f6g7h8i9j0" \
  "https://azurehaymaker-orchestrator-func.azurewebsites.net/api/v1/runs/550e8400-e29b-41d4-a716-446655440000/logs/stream"
```

---

## Document Metadata

**Version**: 1.0
**Date**: 2025-11-14
**Author**: Claude Code (API Designer Agent)
**Status**: Ready for Review
**Related Documents**:
- [Architecture Specification](architecture.md)
- [Requirements](requirements.md)

**Next Steps**:
1. Stakeholder review of API design
2. Security review of authentication/authorization
3. Approval for implementation
4. Handoff to builder agent for implementation

---

**End of API Design Specification**
