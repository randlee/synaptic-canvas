# repomix-nuget Use Cases

## Introduction

The `repomix-nuget` package generates AI-optimized context from .NET/NuGet projects by combining Repomix compression technology with rich NuGet package metadata. This produces compact, structured XML containing complete API surfaces, namespace hierarchies, dependency graphs, and framework compatibility information—enabling AI tools to understand your codebase deeply.

These use cases demonstrate how `repomix-nuget` powers code review, documentation generation, architecture analysis, and team onboarding for .NET projects.

---

## Use Case 1: Analyzing .NET/NuGet Project Structure

**Scenario/Context:**
You're joining a new .NET project and need to understand its architecture: what packages does it depend on, what are the main namespaces, how are components organized, and what's the public API surface? Instead of diving through dozens of files, you want a comprehensive structural overview.

**Step-by-step Walkthrough:**

1. Clone or navigate to .NET project:
   ```bash
   git clone https://github.com/org/example-dotnet-service.git
   cd example-dotnet-service
   ```

2. Install repomix-nuget locally:
   ```
   /sc-manage --install repomix-nuget --local
   ```

3. Generate comprehensive project context:
   ```
   /repomix-nuget --generate --package-path . --output ./nuget-context.xml
   ```
   Output:
   ```
   Generating NuGet context for example-dotnet-service...

   Processing:
   ✓ Detected .csproj files: 3
   ✓ Package ID: Example.DotNet.Service (v1.2.0)
   ✓ Framework: net8.0
   ✓ Dependencies: 12 packages identified
   ✓ Namespaces: 24 public namespaces
   ✓ Running Repomix compression...

   Output:
   Context generated: ./nuget-context.xml (487 KB compressed)

   Structure:
   - Dependencies: EntityFramework, MediatR, Serilog, etc.
   - Public APIs: 156 public classes, 89 interfaces, 34 records
   - Framework Targets: net8.0, net7.0
   - Key Namespaces:
     • Example.DotNet.Service.API
     • Example.DotNet.Service.Domain
     • Example.DotNet.Service.Infrastructure
   ```

4. Ask Claude about project structure using the context:
   ```
   Using the generated nuget-context.xml, explain the overall architecture
   of this project and how the main components interact.
   ```

5. Claude analyzes the structure and explains:
   ```
   Architecture Overview:

   This is a three-tier .NET 8 service with the following structure:

   Core Layers:
   - API Layer (Example.DotNet.Service.API)
     Controllers handling HTTP requests
     Uses MediatR for command/query pattern

   - Domain Layer (Example.DotNet.Service.Domain)
     Core business logic
     Entity definitions with EF Core

   - Infrastructure Layer (Example.DotNet.Service.Infrastructure)
     Data persistence (SQL Server via EF Core)
     Logging (Serilog)
     External service integrations

   Key Dependencies:
   - EntityFramework Core 8.0 for data access
   - MediatR for CQRS pattern implementation
   - Serilog for structured logging
   - AutoMapper for DTO mapping

   Public API Surface:
   - 156 public classes providing services and models
   - 89 interfaces defining contracts
   - 34 records for value types and events

   Primary Workflows:
   1. HTTP request → API controller
   2. Controller dispatches MediatR command/query
   3. Handler executes business logic in domain
   4. Infrastructure layer persists changes
   5. Response returned to client
   ```

6. Ask follow-up questions:
   ```
   What are the main external dependencies and how might they impact deployment?
   Which namespaces should I focus on as a new team member?
   What patterns and conventions are used across the codebase?
   ```

**Expected Outcomes:**
- Complete architectural understanding in minutes
- Clear API surface and dependency graph
- Namespace organization and patterns visible
- Framework and version information available
- Answers to technical questions about project structure

**Benefits of Using This Approach:**
- Rapid onboarding for new developers
- AI-assisted architecture understanding
- No manual exploration of dozens of files
- Clear API surface documentation
- Structured data for analysis

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)
- [repomix-nuget README](README.md)
- [Generating NuGet Context Skill](skills/generating-nuget-context/SKILL.md)

**Tips and Best Practices:**
- Generate context early in project discovery
- Share generated XML with team for common reference
- Update context when major architectural changes occur
- Use with follow-up questions to explore specific areas
- Generate for each major library in monorepo separately

**Common Pitfalls to Avoid:**
- Generating context for entire monorepo at once (too large)
- Not updating context when dependencies change significantly
- Using outdated context for architecture decisions
- Ignoring framework compatibility information

**Variations for Different Scenarios:**

**Multi-library analysis (generate separately):**
```bash
# Service library
/repomix-nuget --generate --package-path ./src/Services --output ./services-context.xml

# Core library
/repomix-nuget --generate --package-path ./src/Core --output ./core-context.xml

# Data library
/repomix-nuget --generate --package-path ./src/Data --output ./data-context.xml
```

**Including documentation tier:**
```
/repomix-nuget --generate --package-path . --output ./context.xml --include-docs
```

---

## Use Case 2: AI-Assisted Code Review and Documentation

**Scenario/Context:**
You're preparing a code review for a significant feature branch in a .NET service. You want Claude to provide:
1. Code quality analysis
2. Architectural impact assessment
3. Documentation generation
4. Best practices validation

Using repomix-nuget context makes the analysis much more accurate and comprehensive.

**Step-by-step Walkthrough:**

1. Generate context for the main branch:
   ```bash
   git checkout main
   /repomix-nuget --generate --package-path . --output ./main-context.xml
   ```

2. Generate context for the feature branch:
   ```bash
   git checkout feature-major-refactor
   /repomix-nuget --generate --package-path . --output ./feature-context.xml
   ```

3. Ask Claude for comprehensive code review:
   ```
   I've generated two NuGet contexts:
   - main-context.xml (current production code)
   - feature-context.xml (proposed feature branch)

   Please analyze the differences and provide:
   1. Code quality improvements and concerns
   2. Architectural impact assessment
   3. Breaking changes or API modifications
   4. Suggested documentation updates
   5. Performance implications
   6. Security considerations
   7. Testing recommendations
   ```

4. Claude performs detailed analysis:
   ```
   Code Review Analysis

   ARCHITECTURAL CHANGES:
   ✓ Positive: Refactored Repository pattern for better testability
   ! Warning: Public API signatures changed in 3 classes
   ! Warning: New dependency on FluentValidation (check version compatibility)

   CODE QUALITY:
   ✓ Improved: 12 new unit tests added for domain logic
   ✓ Improved: Reduced cyclomatic complexity in UserService by 30%
   ! Issue: New abstract class DataProcessor has no implementations yet
   ! Issue: Async/await inconsistency in 2 methods

   PERFORMANCE:
   ✓ Improvement: Database query optimization reduces N+1 queries
   ! Concern: New caching layer adds startup time (measure impact)

   DOCUMENTATION NEEDED:
   - Update README for new Configuration namespace
   - Document breaking API changes
   - Add examples for new Result<T> pattern

   TESTING GAPS:
   - Integration tests for new Repository abstraction
   - Performance tests for cache behavior
   - API contract tests for breaking changes

   RECOMMENDATIONS:
   1. Add detailed migration guide for breaking changes
   2. Complete implementations of DataProcessor
   3. Standardize async/await across codebase
   4. Add performance benchmarks
   5. Update architecture documentation
   ```

5. Generate updated documentation:
   ```
   Based on the feature-context.xml, create:
   1. API documentation for new public classes
   2. Architecture diagram showing new components
   3. Migration guide for breaking changes
   4. Testing strategy for new patterns
   ```

6. Claude generates documentation:
   ```markdown
   # API Documentation - New Classes

   ## Result<T> Pattern
   New wrapper type for operation results, replacing exceptions for flow control.

   ```csharp
   public abstract record Result<T>
   {
       public record Success(T Value) : Result<T>;
       public record Failure(string ErrorMessage) : Result<T>;
       public record NotFound(string ResourceName) : Result<T>;
   }
   ```

   Usage example...

   ## Migration Guide

   ### Breaking Changes

   1. **Repository Interface Update**
      Old: IRepository<T>.Get(id) throws NotFoundException
      New: IRepository<T>.GetAsync(id) returns Task<Result<T>>

      Migration:
      ```csharp
      // Old
      var user = userRepository.Get(userId);

      // New
      var result = await userRepository.GetAsync(userId);
      if (result is Result<User>.Success success)
          var user = success.Value;
      ```

   [Complete migration guide...]
   ```

**Expected Outcomes:**
- Comprehensive code review with architectural impact
- AI-assisted detection of issues and improvements
- Generated documentation for new APIs
- Clear migration guides for breaking changes
- Quality recommendations backed by analysis

**Benefits of Using This Approach:**
- More thorough code reviews
- Architectural impact visible before merge
- Documentation generated automatically
- Breaking changes identified early
- Team learns from review feedback

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)
- [Generating NuGet Context Skill](skills/generating-nuget-context/SKILL.md)

**Tips and Best Practices:**
- Generate context before major review meetings
- Use context to guide reviewer focus areas
- Save contexts for baseline comparison
- Document AI recommendations in PR comments
- Include generated documentation in PR description

**Common Pitfalls to Avoid:**
- Using outdated context for analysis
- Ignoring architectural warnings from AI analysis
- Not verifying AI suggestions independently
- Over-relying on context without code inspection

---

## Use Case 3: Package Dependency Analysis

**Scenario/Context:**
Your project has accumulated many NuGet dependencies over time. You want to understand:
- What external packages are actually used
- Which dependencies have security updates available
- Where transitive dependencies come from
- Which packages could be removed
- Framework compatibility across dependencies

**Step-by-step Walkthrough:**

1. Generate comprehensive dependency context:
   ```
   /repomix-nuget --generate --package-path . --output ./dependencies-context.xml
   ```

2. Ask Claude for dependency analysis:
   ```
   Analyze all NuGet dependencies in the generated context. Provide:
   1. Direct vs. transitive dependency breakdown
   2. Unused or rarely-used packages
   3. Version ranges and compatibility risks
   4. Security update recommendations
   5. Dependency consolidation opportunities
   6. Total dependency tree depth
   ```

3. Claude analyzes dependencies:
   ```
   Dependency Analysis Report

   SUMMARY:
   - Total Direct Dependencies: 12
   - Total Transitive Dependencies: 47
   - Maximum Dependency Tree Depth: 4 levels
   - Framework Targets: net8.0, net7.0

   DIRECT DEPENDENCIES:
   ✓ EntityFrameworkCore (8.0.0) - CURRENT - Used throughout
   ✓ MediatR (12.1.1) - CURRENT - CQRS pattern core
   ✓ Serilog (3.1.1) - CURRENT - Logging in all layers
   ✓ AutoMapper (13.0.1) - CURRENT - DTO mapping
   ✓ FluentValidation (11.8.0) - CURRENT - Request validation
   ✓ Newtonsoft.Json (13.0.3) - OUTDATED - Consider System.Text.Json
   ! UNUSED: Polly (5.0.0) - No retry logic found in code
   ! UNUSED: Hangfire (1.7.35) - Commented out, never implemented
   ! SECURITY: NLog (5.1.0) - Update available to 5.2.5

   TRANSITIVE DEPENDENCIES:
   ✓ Most recent versions
   ✓ No security vulnerabilities detected
   ! Azure.Core (1.25.0) - Multiple packages depend on this
   ! System.Reactive (5.0.0) - Deep in chain from rx.net

   RECOMMENDATIONS:

   1. Remove Unused Dependencies
      - Polly: No retry logic in current codebase
      - Hangfire: Implementation was cancelled
      Save ~2MB in deployment

   2. Update Security Patches
      - NLog: 5.1.0 → 5.2.5 (security fix)
      - Dependencies: 3 minor updates available

   3. Consolidate Serialization
      - Currently: Both Newtonsoft.Json and System.Text.Json
      - Recommend: Standardize on System.Text.Json (built-in)

   4. Monitor Transitive Dependencies
      - Azure.Core shared across multiple packages
      - Monitor for compatibility issues

   5. Framework Consolidation
      - Both net8.0 and net7.0 targets
      - Consider dropping net7.0 (EOL approaching)

   ACTION ITEMS:
   1. Remove Polly and Hangfire (immediate - saves build size)
   2. Update NLog to 5.2.5 (security)
   3. Evaluate System.Text.Json migration (medium-term)
   4. Consolidate framework targets (planning)
   5. Set up dependency audit in CI/CD (ongoing)
   ```

4. Create action plan based on analysis:
   ```bash
   # Create work items
   cat > dependency-cleanup-plan.md << 'EOF'
   # Dependency Cleanup Plan

   ## Immediate Actions (This Sprint)
   - [ ] Remove Polly package and its usages
   - [ ] Remove Hangfire package
   - [ ] Update NLog to 5.2.5

   ## Short-term (Next 2 Weeks)
   - [ ] Evaluate System.Text.Json migration
   - [ ] Test with net8.0 target only
   - [ ] Consolidate Azure.Core usage

   ## Medium-term (Next Quarter)
   - [ ] Migrate to System.Text.Json fully
   - [ ] Drop net7.0 target support
   - [ ] Implement dependency auditing in CI/CD

   Expected benefits:
   - 15-20% reduction in dependency tree
   - Improved security posture
   - Easier maintenance and updates
   - Faster build times
   EOF
   ```

**Expected Outcomes:**
- Complete understanding of dependency landscape
- Clear security update recommendations
- Identification of unused packages
- Consolidation opportunities visible
- Prioritized action plan for cleanup

**Benefits of Using This Approach:**
- Reduce deployment size and complexity
- Improve security posture
- Identify consolidation opportunities
- Make informed framework decisions
- Reduce maintenance burden

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)
- [Registry Schema](skills/generating-nuget-context/registry-schema.md)

**Tips and Best Practices:**
- Analyze dependencies quarterly
- Remove unused packages immediately
- Update security patches monthly
- Document dependency decisions
- Include dependency audit in CI/CD

**Common Pitfalls to Avoid:**
- Removing packages without checking code
- Ignoring security updates
- Not considering transitive dependencies
- Consolidating too aggressively

---

## Use Case 4: Framework Compatibility Checking

**Scenario/Context:**
You're planning to upgrade from .NET 7 to .NET 8, or considering support for .NET 9. Before making changes, you want to understand:
- Which dependencies support the target framework
- What breaking changes might occur
- How to phase out old framework support
- What compatibility concerns exist

**Step-by-step Walkthrough:**

1. Generate context for current codebase:
   ```
   /repomix-nuget --generate --package-path . --output ./current-net7-context.xml
   ```

2. Ask Claude about framework compatibility:
   ```
   Based on the current-net7-context.xml, analyze compatibility for:
   1. Upgrading from net7.0 to net8.0
   2. Adding net9.0 as additional target

   For each scenario, provide:
   - Dependencies that support the framework
   - Minimum version requirements
   - Deprecation notices
   - Breaking changes likely to affect us
   - Migration effort estimate
   - Timeline recommendations
   ```

3. Claude provides compatibility analysis:
   ```
   Framework Upgrade Analysis

   CURRENT STATE:
   - Primary: net8.0
   - Secondary: net7.0 (EOL: November 2024)
   - Earliest .NET LTS: 8.0 (until November 2026)

   TARGET: Drop net7.0 (EOL) + Add net9.0

   DEPENDENCY COMPATIBILITY:

   EntityFrameworkCore 8.0.0:
   ✓ net8.0: Full support
   ✓ net9.0: Full support (tested)
   ~ net7.0: EOL (no new features)

   MediatR 12.1.1:
   ✓ net8.0: Full support
   ✓ net9.0: Full support
   ~ net7.0: Supported but deprecated

   Serilog 3.1.1:
   ✓ net8.0: Full support
   ✓ net9.0: Full support
   ~ net7.0: Supported

   [All dependencies analyzed]

   COMPATIBILITY SUMMARY:
   - 11/12 dependencies support net9.0 natively
   - 1 dependency (LegacyLib 2.0) requires net9.0-specific version (3.0)

   MIGRATION STEPS:

   1. Update LegacyLib 2.0 → 3.0
      Estimated effort: 2 hours (API surface changed)
      Tests needed: 12 unit tests in LegacyLib tests

   2. Update TargetFramework in .csproj
      From: <TargetFramework>net8.0;net7.0</TargetFramework>
      To:   <TargetFramework>net8.0;net9.0</TargetFramework>

   3. Build and test
      Estimated time: 15 minutes (local build)
      CI/CD time: 30 minutes

   4. Monitor for runtime issues
      Typical issues: None expected
      Risk level: Low

   TIMELINE RECOMMENDATION:
   - Week 1: Test with net9.0 target in feature branch
   - Week 2: Merge and deploy to staging
   - Week 3: Monitor and optimize
   - Week 4: Deploy to production

   BENEFITS:
   - Support for latest .NET version
   - Dropped net7.0 (EOL, reduces matrix)
   - Performance improvements from net9.0
   - 2+ years of LTS support (until November 2026)
   ```

4. Create upgrade plan:
   ```bash
   cat > framework-upgrade-plan.md << 'EOF'
   # .NET Framework Upgrade Plan

   Current: net8.0, net7.0
   Target: net8.0, net9.0

   ## Phase 1: Preparation (Week 1)
   - [ ] Update LegacyLib to v3.0
   - [ ] Update all NuGet dependencies to latest
   - [ ] Create net9.0 target in .csproj
   - [ ] Run full test suite

   ## Phase 2: Testing (Week 2)
   - [ ] Deploy feature branch to staging
   - [ ] Run integration tests
   - [ ] Performance testing
   - [ ] Compatibility testing with downstream services

   ## Phase 3: Rollout (Week 3)
   - [ ] Merge to main
   - [ ] Deploy to production
   - [ ] Monitor for issues

   ## Phase 4: Cleanup (Week 4)
   - [ ] Remove net7.0 target (once stable)
   - [ ] Update documentation
   - [ ] Archive EOL-related configs

   Effort estimate: 20 hours developer time
   Risk level: Low
   EOF
   ```

**Expected Outcomes:**
- Clear understanding of framework compatibility
- Identified breaking changes and migration effort
- Prioritized upgrade plan
- Risk assessment and timeline
- Dependency version requirements documented

**Benefits of Using This Approach:**
- Confident framework upgrade decisions
- Reduced compatibility surprises
- Planned rollout minimizes risk
- Technical debt addressed proactively

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)

**Tips and Best Practices:**
- Generate context before framework decisions
- Test thoroughly in feature branch
- Coordinate with team on timeline
- Plan rollout carefully
- Monitor production after deployment

**Common Pitfalls to Avoid:**
- Upgrading too aggressively without testing
- Not checking all transitive dependencies
- Ignoring known breaking changes
- Missing EOL dates for current framework

---

## Use Case 5: Documentation Generation from Code

**Scenario/Context:**
You need to generate comprehensive documentation for your .NET library's public API. Instead of manually documenting classes, methods, and patterns, you can use repomix-nuget context to generate initial documentation that Claude can review and enhance.

**Step-by-step Walkthrough:**

1. Generate context specifically for public API:
   ```
   /repomix-nuget --generate --package-path . --output ./api-docs-context.xml --include-docs
   ```

2. Ask Claude to generate documentation:
   ```
   Using the api-docs-context.xml, generate comprehensive API documentation:

   1. API Overview (1 page)
      - What this library does
      - Main use cases
      - Quick start example

   2. Core Concepts (5 pages)
      - Key interfaces and abstract classes
      - Design patterns used
      - Architectural principles

   3. API Reference (detailed)
      - All public classes documented
      - Public methods with parameters and return types
      - Example usage for complex APIs

   4. Tutorials (3-5)
      - Common workflows
      - Best practices
      - Integration patterns

   5. Troubleshooting
      - Common errors and solutions
      - Performance considerations
      - Debugging tips

   Format: Markdown suitable for GitHub Wiki or docfx
   Include: Code examples for each major feature
   ```

3. Claude generates comprehensive documentation:
   ```markdown
   # API Documentation - Example.DotNet.Service

   ## Overview

   Example.DotNet.Service is a .NET 8 library providing...
   [Comprehensive overview]

   ## Quick Start

   ```csharp
   // Install NuGet package
   dotnet add package Example.DotNet.Service

   // Basic usage
   var service = new UserService(logger, repository);
   var result = await service.GetUserAsync(userId);

   if (result is Result<User>.Success success)
       Console.WriteLine($"User: {success.Value.Name}");
   ```

   ## Core Concepts

   ### Result<T> Pattern
   This library uses the Result<T> pattern for operation outcomes...
   [Detailed explanation with examples]

   ### Repository Pattern
   Data access abstraction layer...
   [Detailed explanation]

   ## API Reference

   ### UserService

   #### GetUserAsync(int userId)
   Retrieves a user by ID.

   **Parameters:**
   - userId (int): The user's unique identifier

   **Returns:**
   - Task<Result<User>>: Success with user, NotFound if not exists, or Failure with error message

   **Example:**
   ```csharp
   var result = await userService.GetUserAsync(123);
   ```

   ### CreateUserAsync(CreateUserRequest request)
   Creates a new user...
   [Complete reference]

   [Complete API documentation with examples for all public APIs]
   ```

4. Review and publish documentation:
   ```bash
   # Save generated documentation
   cp generated-api-docs.md docs/api-reference.md

   # Commit to repository
   git add docs/api-reference.md
   git commit -m "docs: generate API documentation from repomix-nuget context"
   git push origin main
   ```

**Expected Outcomes:**
- Comprehensive API documentation generated
- Examples for all major features
- Quick start guide included
- Troubleshooting section available
- Documentation maintainable and up-to-date

**Benefits of Using This Approach:**
- Documentation always matches codebase
- Significant time savings over manual documentation
- Consistent format across all APIs
- Quick updates when code changes
- Better onboarding for new developers

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)
- [Output Formats Guide](skills/generating-nuget-context/output-formats.md)

**Tips and Best Practices:**
- Regenerate documentation when major features added
- Include XML comments in code for better docs
- Review generated documentation for accuracy
- Add domain-specific examples not in auto-generated docs
- Version documentation with releases

**Common Pitfalls to Avoid:**
- Auto-generated documentation without review
- Outdated XML comments in code
- Not regenerating after significant changes
- Missing domain-specific guidance

---

## Use Case 6: Architecture Visualization and Understanding

**Scenario/Context:**
You want to create architecture diagrams and visualizations of your .NET service. Rather than creating diagrams manually, you can use repomix-nuget context to generate architecture documentation that shows components, dependencies, and data flows.

**Step-by-step Walkthrough:**

1. Generate project context:
   ```
   /repomix-nuget --generate --package-path . --output ./arch-analysis-context.xml
   ```

2. Ask Claude to create architecture diagrams:
   ```
   Based on the arch-analysis-context.xml, create:

   1. Component Diagram (ASCII or Mermaid)
      - Show major components
      - Component responsibilities
      - Inter-component communication

   2. Layer Diagram
      - API Layer
      - Domain Layer
      - Infrastructure Layer
      - External Services

   3. Dependency Graph (partial)
      - Show major package dependencies
      - Version information
      - Key integration points

   4. Data Flow Diagram
      - User request flow
      - Data transformation
      - Persistence operations

   Format: Mermaid for GitHub compatibility
   ```

3. Claude generates architecture diagrams:
   ```markdown
   # Architecture Visualization

   ## Component Diagram

   ```mermaid
   graph TB
       API["API Layer<br/>Controllers<br/>Endpoints"]
       CQRS["CQRS Layer<br/>Commands<br/>Queries"]
       DOMAIN["Domain Layer<br/>Entities<br/>Value Objects<br/>Business Logic"]
       REPO["Repository Layer<br/>Data Abstraction"]
       DB["Database<br/>SQL Server"]
       EXT["External Services<br/>Cache<br/>Message Queue"]

       API -->|MediatR| CQRS
       CQRS -->|Calls| DOMAIN
       DOMAIN -->|Uses| REPO
       REPO -->|SQL| DB
       DOMAIN -.->|Optional| EXT
   ```

   ## Layer Architecture

   ```mermaid
   graph LR
       subgraph "API Layer"
           CTRL["User<br/>Profile<br/>Admin<br/>Controllers"]
       end

       subgraph "CQRS Layer"
           CMD["Commands<br/>Handlers"]
           QRY["Queries<br/>Handlers"]
       end

       subgraph "Domain Layer"
           USER["User<br/>Aggregate"]
           PROFILE["Profile<br/>Aggregate"]
           EVENTS["Domain<br/>Events"]
       end

       subgraph "Infrastructure Layer"
           USERREPO["User<br/>Repository"]
           CACHE["Cache<br/>Service"]
           LOG["Logging"]
       end

       CTRL --> CMD
       CTRL --> QRY
       CMD --> USER
       QRY --> PROFILE
       USER --> USERREPO
       USERREPO --> CACHE
       CMD --> LOG
   ```

   ## Request Flow Diagram

   ```mermaid
   sequenceDiagram
       actor User
       participant Controller as User Controller
       participant Command as Command Handler
       participant Domain as User Domain
       participant Repo as User Repository
       participant DB as Database

       User->>Controller: POST /users (CreateUserRequest)
       Controller->>Command: Dispatch CreateUserCommand
       Command->>Domain: Create new user
       Domain->>Repo: Save user
       Repo->>DB: INSERT
       DB-->>Repo: Success
       Repo-->>Domain: Success
       Domain-->>Command: Result<User>
       Command-->>Controller: Result<User>
       Controller-->>User: 201 Created
   ```

   ## Dependency Tree (Top Level)

   ```
   Example.DotNet.Service
   ├── EntityFrameworkCore 8.0.0
   │   ├── System.Data.SqlClient
   │   └── System.Linq
   ├── MediatR 12.1.1
   │   └── System.Reflection
   ├── Serilog 3.1.1
   │   ├── System.Console
   │   └── System.Diagnostics.Trace
   └── AutoMapper 13.0.1
       └── System.Reflection
   ```
   ```

4. Use diagrams in documentation:
   ```bash
   # Create architecture.md with diagrams
   cat > docs/ARCHITECTURE.md << 'EOF'
   # Service Architecture

   [Include diagrams from Claude output]

   ## Component Descriptions

   ### API Layer
   RESTful HTTP endpoints using ASP.NET Core Controllers.

   ### CQRS Layer
   Command and Query Responsibility Segregation implemented via MediatR.

   ### Domain Layer
   Core business logic with domain entities and value objects.

   ### Infrastructure Layer
   Data persistence, caching, and external service integration.

   [Complete architecture documentation]
   EOF
   ```

5. Share with team:
   ```bash
   # Commit architecture documentation
   git add docs/ARCHITECTURE.md
   git commit -m "docs: add architecture diagrams and visualization"
   ```

**Expected Outcomes:**
- Clear architecture visualization
- Component relationships documented
- Data flow understood
- Dependency structure visible
- New team members can quickly understand architecture

**Benefits of Using This Approach:**
- Visual understanding of complex systems
- Documentation always matches code
- Quick updates when architecture changes
- Better team communication
- Onboarding time reduced

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)

**Tips and Best Practices:**
- Use Mermaid for GitHub-friendly diagrams
- Include multiple levels of detail
- Regenerate diagrams when architecture changes
- Share diagrams in team wiki or documentation
- Document assumptions and constraints

**Common Pitfalls to Avoid:**
- Diagrams that don't match actual code
- Overly complex diagrams that confuse
- Not updating diagrams after refactoring
- Missing data flow documentation

---

## Use Case 7: Onboarding New Team Members

**Scenario/Context:**
You're onboarding three new developers to your .NET microservices platform. Instead of spending days explaining the architecture, codebase structure, and patterns, you can provide them with repomix-nuget contexts and structured guides.

**Step-by-step Walkthrough:**

1. Generate context for each major service:
   ```bash
   # Service 1: User Service
   cd ../user-service
   /repomix-nuget --generate --package-path . --output ./user-service-context.xml

   # Service 2: Order Service
   cd ../order-service
   /repomix-nuget --generate --package-path . --output ./order-service-context.xml

   # Service 3: Payment Service
   cd ../payment-service
   /repomix-nuget --generate --package-path . --output ./payment-service-context.xml
   ```

2. Create onboarding guide:
   ```bash
   cat > docs/ONBOARDING.md << 'EOF'
   # Onboarding Guide - Platform Architecture

   Welcome to the platform! This guide will help you understand our architecture
   in your first week.

   ## Day 1: Platform Overview

   Generate and review contexts for all services:
   - user-service-context.xml
   - order-service-context.xml
   - payment-service-context.xml

   Ask Claude to explain:
   "Summarize the overall platform architecture using these contexts.
    What are the main services and how do they interact?"

   Expected output: 20-minute read explaining microservices pattern,
   how services communicate, and architectural principles.

   ## Day 2: User Service Deep Dive

   Load user-service-context.xml and ask:
   "Walk me through the User Service code. Explain:
    - Main components and responsibilities
    - Database schema and relationships
    - API endpoints provided
    - CQRS pattern implementation
    - Error handling strategies"

   Expected output: Detailed explanation of service internals.

   ## Day 3: Order Service Deep Dive

   Load order-service-context.xml and explore order workflows.

   ## Day 4-5: Local Development Setup

   After understanding services:
   - Clone all three repositories
   - Generate fresh contexts locally
   - Run services locally
   - Test inter-service communication
   - Review and study code

   ## Week 2: Contribute to First Ticket

   By week 2, you should be able to:
   - Understand which service needs changes
   - Navigate to relevant code
   - Generate updated context for analysis
   - Ask Claude for implementation guidance
   - Submit PR with confidence

   ## Getting Help

   Use repomix-nuget contexts when stuck:
   ```
   I'm working on feature X in order-service.

   [Load order-service-context.xml]

   I need to modify the Order aggregate to support Y.
   How should I structure this change?
   ```

   ## Resources

   - Architecture documentation: docs/ARCHITECTURE.md
   - Development guide: docs/DEVELOPMENT.md
   - Contributing: CONTRIBUTING.md
   EOF
   ```

3. Create quick reference card:
   ```bash
   cat > docs/QUICK-START.md << 'EOF'
   # Quick Start - New Developer

   ## First 30 minutes

   1. Clone all three services:
      ```bash
      git clone https://github.com/org/user-service
      git clone https://github.com/org/order-service
      git clone https://github.com/org/payment-service
      ```

   2. Install global sc-manage:
      ```bash
      python3 tools/sc-install.py install sc-manage --global
      ```

   3. In each service, install repomix-nuget:
      ```bash
      /sc-manage --install repomix-nuget --local
      ```

   4. Generate contexts:
      ```bash
      /repomix-nuget --generate --output ./context.xml
      ```

   5. Share contexts on Slack in #dev-onboarding

   ## First Week Learning

   Day 1: Review architecture using contexts
   Day 2: Explore user service
   Day 3: Explore order service
   Day 4: Set up local development
   Day 5: Complete first small ticket

   ## Questions?

   Ask in #dev-general with:
   - What you're trying to do
   - Which service/context you're reviewing
   - Specific question

   Team is happy to help!
   EOF
   ```

4. Host virtual onboarding session:
   ```bash
   # Run Claude Code with contexts for new developers
   # Live explanation of architecture using contexts
   # Q&A session for clarifications
   # Assignment: Generate context for assigned service
   ```

5. Create feedback loop:
   ```bash
   # After one week, collect feedback
   # "Was the context helpful?"
   # "What was confusing?"
   # Update documentation based on feedback
   ```

**Expected Outcomes:**
- New developers productive in 2-3 days instead of 2-3 weeks
- Clear path for learning architecture
- Reduced ramp-up time
- Consistent onboarding for future hires
- Less pressure on existing team to explain
- New developers unblock faster

**Benefits of Using This Approach:**
- Dramatically faster onboarding
- Consistent learning material
- Scalable training for team growth
- Less time lost to training
- Better retention of new developers

**Related Documentation:**
- [/repomix-nuget command reference](commands/repomix-nuget.md)

**Tips and Best Practices:**
- Update contexts when major features added
- Create service-specific guides
- Pair with hands-on assignments
- Assign mentor for first month
- Document common questions

**Common Pitfalls to Avoid:**
- Overwhelming new hires with too much information
- Outdated contexts causing confusion
- Not checking in after first week
- Missing domain-specific knowledge

---

## Common Patterns

### Pattern 1: Generate Standard Context
```
/repomix-nuget --generate --package-path . --output ./context.xml
```

### Pattern 2: Generate with Documentation
```
/repomix-nuget --generate --package-path . --output ./context.xml --include-docs
```

### Pattern 3: Targeted Analysis
```bash
# Analyze specific library
cd src/Core
/repomix-nuget --generate --package-path . --output ./core-context.xml
```

### Pattern 4: Compare Versions
```bash
# Generate context for main
git checkout main
/repomix-nuget --generate --output ./main-context.xml

# Generate context for feature branch
git checkout feature-upgrade
/repomix-nuget --generate --output ./feature-context.xml
```

---

## Integration Examples

### With Git Workflow
```bash
#!/bin/bash
# scripts/pre-commit-context.sh
# Generate updated context before committing significant changes

if git diff --cached --name-only | grep -E '\.(cs|csproj|sln)$' > /dev/null; then
  echo "Detected C# changes, regenerating context..."
  /repomix-nuget --generate --output ./nuget-context.xml
  git add nuget-context.xml
fi
```

### With CI/CD Pipeline
```yaml
- name: Generate NuGet Context
  run: |
    /sc-manage --install repomix-nuget --local
    /repomix-nuget --generate --output ./artifacts/nuget-context.xml

- name: Analyze with Claude
  run: |
    npx claude-code --exec-mode sync <<'SCRIPT'
    Analyze nuget-context.xml for:
    1. Dependency updates needed
    2. Breaking changes in main branch
    3. Code quality improvements
    SCRIPT
```

### With Documentation Generation
```bash
#!/bin/bash
# scripts/generate-docs.sh

/repomix-nuget --generate --package-path . --output ./context.xml --include-docs

# Ask Claude to generate documentation
npx claude-code --exec-mode sync <<'SCRIPT'
Generate comprehensive API documentation from the context.
Include: overview, quick start, tutorials, troubleshooting.
SCRIPT
```

---

## Team Workflows

### Architecture Review Process
1. Feature owner generates context
2. Team reviews context + code
3. Architectural decisions documented
4. Context becomes reference material

### Documentation Maintenance
1. Before PR merge: regenerate context
2. Claude generates updated documentation
3. Documentation reviewed with PR
4. Merged together with code

### Dependency Auditing
1. Monthly: Generate fresh context
2. Claude analyzes for updates
3. Security patches prioritized
4. Unused packages removed

---

## Troubleshooting

### Scenario: Context too large or time-consuming to generate
**Solution:**
- Generate context for specific libraries/projects only
- Split large monorepo into separate contexts
- Use targeted package-path parameter

### Scenario: Context seems incomplete
**Solution:**
```bash
# Verify .nuget-context.json exists
cat .nuget-context.json

# If missing, regenerate from scratch
/repomix-nuget --generate --package-path . --output ./context.xml
```

### Scenario: Claude analysis seems generic
**Solution:**
- Include domain-specific questions
- Reference specific components in question
- Load context explicitly before asking detailed questions
- Ask for examples relevant to your domain

### Scenario: Old context causing confusion
**Solution:**
```bash
# Delete old context
rm nuget-context.xml

# Generate fresh
/repomix-nuget --generate --output ./nuget-context.xml
```

---

## Getting Started

### Minimum Setup
```bash
# Install repomix-nuget in .NET project
/sc-manage --install repomix-nuget --local

# Generate context
/repomix-nuget --generate --output ./context.xml

# Ask Claude about it
# "Explain the architecture of this project"
```

### First Use
1. Generate context: `/repomix-nuget --generate --output ./context.xml`
2. Ask Claude a question: "What does this project do?"
3. Ask for specific analysis: "What are the main components?"
4. Request documentation: "Generate API documentation"
5. Share context with team

### Common Starting Patterns
- **New to project**: `/repomix-nuget --generate` then "Explain architecture"
- **Code review**: Generate context for branch, ask for review
- **Dependency analysis**: Generate context, ask "Analyze dependencies"
- **Documentation**: Generate context, ask for "API documentation"
- **Onboarding**: Generate context, send to new developers

---

## See Also

- [repomix-nuget README](README.md)
- [/repomix-nuget Command Reference](commands/repomix-nuget.md)
- [Generating NuGet Context Skill](skills/generating-nuget-context/SKILL.md)
- [Output Formats Guide](skills/generating-nuget-context/output-formats.md)
- [Registry Schema](skills/generating-nuget-context/registry-schema.md)
- [Synaptic Canvas Contributing Guide](/CONTRIBUTING.md)
- [Synaptic Canvas Repository](https://github.com/randlee/synaptic-canvas)

---

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Maintainer:** Synaptic Canvas Contributors
