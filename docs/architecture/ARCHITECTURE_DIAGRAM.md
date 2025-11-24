# Container Manager Architecture Diagrams

## 1. Class Structure and Delegation Flow

```mermaid
classDiagram
    class ContainerManager {
        -OrchestratorConfig config
        -ContainerDeployer _deployer
        -ContainerMonitor _monitor
        -ContainerLifecycle _lifecycle
        -ImageVerifier _verifier
        +deploy(scenario, sp) string
        +get_status(app_name) string
        +delete(app_name) bool
        +_generate_app_name(name) string
        +_build_container(app, sp) dict
        +_build_configuration(sp) dict
    }

    class ContainerDeployer {
        -OrchestratorConfig config
        -string resource_group_name
        -string subscription_id
        +deploy(scenario, sp) string
        +_generate_app_name(name) string
        +_build_container(app, sp) dict
        +_build_template(container) dict
        +_build_configuration(sp) dict
        +_get_region() string
        -_validate_resources() void
        -_validate_vnet() void
    }

    class ContainerMonitor {
        -string resource_group_name
        -string subscription_id
        +get_status(app_name) string
    }

    class ContainerLifecycle {
        -string resource_group_name
        -string subscription_id
        +delete(app_name) bool
    }

    class ImageVerifier {
        +verify_signature(image_ref, client) bool
    }

    class OrchestratorConfig {
        +string target_tenant_id
        +string target_subscription_id
        +string container_registry
        +string container_image
        +string key_vault_url
        +bool vnet_integration_enabled
        +int container_memory_gb
        +int container_cpu_cores
    }

    ContainerManager --> ContainerDeployer : delegates
    ContainerManager --> ContainerMonitor : delegates
    ContainerManager --> ContainerLifecycle : delegates
    ContainerManager --> ImageVerifier : delegates
    ContainerDeployer --> OrchestratorConfig : uses
    ContainerManager --> OrchestratorConfig : owns
```

## 2. Configuration Injection Flow

```mermaid
graph TD
    A[OrchestratorConfig<br/>Full configuration] --> B[ContainerManager Facade]
    B --> C[ContainerDeployer<br/>Receives: Full Config]
    B --> D[ContainerMonitor<br/>Receives: RG + Subscription]
    B --> E[ContainerLifecycle<br/>Receives: RG + Subscription]
    B --> F[ImageVerifier<br/>Receives: Nothing]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1e1
    style D fill:#e1ffe1
    style E fill:#f0e1ff
    style F fill:#ffe1f0
```

## 3. Deployment Flow Sequence

```mermaid
sequenceDiagram
    participant Client
    participant Facade as ContainerManager
    participant Verifier as ImageVerifier
    participant Deployer as ContainerDeployer
    participant Azure as Azure SDK

    Client->>Facade: deploy(scenario, sp)
    Facade->>Verifier: verify_signature(image_ref)
    Verifier->>Verifier: Check registry approval
    Verifier->>Verifier: Validate digest format
    Verifier-->>Facade: True (signature valid)
    Facade->>Deployer: deploy(scenario, sp)
    Deployer->>Deployer: _generate_app_name()
    Deployer->>Deployer: _build_container()
    Deployer->>Deployer: _build_template()
    Deployer->>Deployer: _build_configuration()
    Deployer->>Azure: begin_create_or_update()
    Azure-->>Deployer: Container app ID
    Deployer-->>Facade: Container app ID
    Facade-->>Client: Container app ID
```

## 4. Status Monitoring Flow

```mermaid
sequenceDiagram
    participant Client
    participant Facade as ContainerManager
    participant Monitor as ContainerMonitor
    participant Azure as Azure SDK

    Client->>Facade: get_status(app_name)
    Facade->>Monitor: get_status(app_name)
    Monitor->>Azure: container_apps.get()
    Azure-->>Monitor: App details
    Monitor->>Monitor: Extract running_status
    Monitor-->>Facade: Status string
    Facade-->>Client: Status string
```

## 5. Test Coverage Mapping

```mermaid
graph LR
    subgraph Tests
        T1[TestContainerManagerInit]
        T2[TestAppNameGeneration]
        T3[TestBuildContainer]
        T4[TestBuildConfiguration]
        T5[TestValidation]
        T6[TestDeployFunction]
        T7[TestGetStatusFunction]
        T8[TestDeleteFunction]
        T9[TestImageVerification]
    end

    subgraph Classes
        C1[ContainerManager Facade]
        C2[ContainerDeployer]
        C3[ContainerMonitor]
        C4[ContainerLifecycle]
        C5[ImageVerifier]
    end

    T1 --> C1
    T2 --> C2
    T3 --> C2
    T4 --> C2
    T5 --> C1
    T6 --> C1
    T6 --> C2
    T7 --> C3
    T8 --> C4
    T9 --> C5

    style T1 fill:#e1f5ff
    style T2 fill:#e1f5ff
    style T3 fill:#e1f5ff
    style T4 fill:#e1f5ff
    style T5 fill:#e1f5ff
    style T6 fill:#e1f5ff
    style T7 fill:#e1f5ff
    style T8 fill:#e1f5ff
    style T9 fill:#e1f5ff
```

## 6. File Structure Before and After

```mermaid
graph TD
    subgraph Before
        A1[container_manager.py<br/>593 lines<br/>1 class + 3 functions]
    end

    subgraph After
        B1[container_manager.py<br/>80 lines<br/>Facade + 3 functions]
        B2[container_deployer.py<br/>200 lines<br/>Deployment logic]
        B3[container_monitor.py<br/>150 lines<br/>Status checks]
        B4[container_lifecycle.py<br/>150 lines<br/>Deletion logic]
        B5[image_verifier.py<br/>100 lines<br/>Signature validation]
    end

    A1 -.Refactor.-> B1
    A1 -.Extract.-> B2
    A1 -.Extract.-> B3
    A1 -.Extract.-> B4
    A1 -.Extract.-> B5

    style A1 fill:#ffe1e1
    style B1 fill:#fff4e1
    style B2 fill:#e1ffe1
    style B3 fill:#e1f5ff
    style B4 fill:#f0e1ff
    style B5 fill:#ffe1f0
```

## 7. Dependency Graph

```mermaid
graph BT
    subgraph External
        E1[Azure SDK]
        E2[OrchestratorConfig]
        E3[ScenarioMetadata]
        E4[ServicePrincipalDetails]
    end

    subgraph New Classes
        C1[ImageVerifier]
        C2[ContainerMonitor]
        C3[ContainerLifecycle]
        C4[ContainerDeployer]
    end

    subgraph Facade
        F1[ContainerManager]
    end

    C1 --> E1
    C2 --> E1
    C3 --> E1
    C4 --> E1
    C4 --> E2

    F1 --> C1
    F1 --> C2
    F1 --> C3
    F1 --> C4
    F1 --> E2
    F1 --> E3
    F1 --> E4

    style C1 fill:#ffe1f0
    style C2 fill:#e1f5ff
    style C3 fill:#f0e1ff
    style C4 fill:#e1ffe1
    style F1 fill:#fff4e1
```

## 8. Implementation Phases

```mermaid
gantt
    title Container Manager Refactoring Phases
    dateFormat YYYY-MM-DD
    section Phase 1
    Extract ImageVerifier    :p1, 2025-01-01, 1d
    Run Tests               :milestone, m1, after p1, 0d
    section Phase 2
    Extract ContainerMonitor :p2, after m1, 1d
    Run Tests               :milestone, m2, after p2, 0d
    section Phase 3
    Extract ContainerLifecycle :p3, after m2, 1d
    Run Tests               :milestone, m3, after p3, 0d
    section Phase 4
    Extract ContainerDeployer :p4, after m3, 1d
    Run Tests               :milestone, m4, after p4, 0d
    section Phase 5
    Refactor Facade         :p5, after m4, 1d
    Run All Tests           :milestone, m5, after p5, 0d
    section Phase 6
    Update Public API       :p6, after m5, 1d
    Final Validation        :milestone, m6, after p6, 0d
```

## 9. Backward Compatibility Strategy

```mermaid
flowchart TD
    A[Existing Import] -->|No changes| B{Import Path}
    B -->|from orchestrator import| C[ContainerManager]
    B -->|from container_manager import| D[Functions/Classes]

    C --> E[Facade Delegates]
    D --> F[Standalone Functions]

    E --> G[ContainerDeployer]
    E --> H[ContainerMonitor]
    E --> I[ContainerLifecycle]
    E --> J[ImageVerifier]

    F --> G
    F --> H
    F --> I
    F --> J

    G --> K[Azure SDK]
    H --> K
    I --> K
    J --> K

    style A fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#fff4e1
    style E fill:#ffe1e1
    style F fill:#ffe1e1
    style G fill:#e1ffe1
    style H fill:#e1ffe1
    style I fill:#e1ffe1
    style J fill:#e1ffe1
```

## 10. Risk Mitigation Flow

```mermaid
flowchart TD
    Start[Start Extraction] --> Phase{Extract Class}
    Phase --> Test{Run Tests}
    Test -->|Pass| Next{More Classes?}
    Test -->|Fail| Debug[Debug & Fix]
    Debug --> Test
    Next -->|Yes| Phase
    Next -->|No| Final[Final Validation]
    Final --> Verify{All 566 Tests Pass?}
    Verify -->|Yes| Done[✓ Complete]
    Verify -->|No| Rollback[Review Architecture]
    Rollback --> Start

    style Start fill:#e1f5ff
    style Test fill:#fff4e1
    style Done fill:#e1ffe1
    style Rollback fill:#ffe1e1
```

---

## Key Insights from Diagrams

### Class Structure (Diagram 1)
- ContainerManager acts as a thin facade with minimal logic
- All specialized classes have clear, non-overlapping responsibilities
- Configuration flows from OrchestratorConfig to classes that need it

### Configuration Injection (Diagram 2)
- Deployer needs full config (10+ fields)
- Monitor and Lifecycle need only identifiers (2 fields)
- ImageVerifier is stateless (0 fields)
- **Design follows Interface Segregation Principle**

### Deployment Flow (Diagram 3)
- Image verification happens **before** deployment (security requirement)
- Deployer orchestrates multiple internal steps
- Clear separation between validation and deployment

### Test Coverage (Diagram 5)
- Tests map cleanly to specific classes
- Facade tests validate delegation
- Specialized class tests validate implementation
- **Zero test modifications needed**

### Implementation Phases (Diagram 8)
- Incremental extraction with test validation at each step
- Low-risk approach: stateless → minimal config → full config
- Milestone-driven with clear success criteria

### Backward Compatibility (Diagram 9)
- Multiple import paths continue working
- Facade maintains transparent delegation
- Standalone functions provide convenience wrappers
- **Zero breaking changes**

---

## Architecture Validation Questions

### Q1: Are responsibilities clearly separated?
**Yes**: Each class has one focused concern (verify, deploy, monitor, delete)

### Q2: Is configuration injection minimal?
**Yes**: Classes receive only what they need (full config vs. identifiers vs. nothing)

### Q3: Are tests preserved unchanged?
**Yes**: Facade maintains private method access for test compatibility

### Q4: Is backward compatibility guaranteed?
**Yes**: All existing imports and APIs continue working

### Q5: Is the implementation low-risk?
**Yes**: Incremental extraction with test validation at each phase

---

**Architecture validated and ready for implementation.**
