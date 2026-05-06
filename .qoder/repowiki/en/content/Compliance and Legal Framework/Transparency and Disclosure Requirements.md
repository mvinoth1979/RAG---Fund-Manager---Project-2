# Transparency and Disclosure Requirements

<cite>
**Referenced Files in This Document**
- [Problem Statement.md](file://Docs/Problem Statement.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document defines the transparency and disclosure obligations for the Mutual Fund FAQ Assistant project. It establishes the source citation requirements, last updated date implementation, and response formatting standards. It also outlines the transparency framework, including disclosure of limitations, disclaimer requirements, and source attribution mechanisms. Compliance validation processes, citation verification procedures, and quality assurance measures are detailed, along with examples of compliant disclosure formats, citation best practices, and transparency reporting requirements. Guidance for user education about source reliability and information verification is included to ensure responsible use of the assistant.

## Project Structure
The repository contains a single problem statement document that defines the transparency and disclosure requirements for the assistant. The document specifies:
- Official public sources for factual information retrieval
- Response formatting constraints (sentence limits, citation requirements, last updated date)
- Disclaimer placement and refusal handling for advisory queries
- Known limitations and compliance expectations

```mermaid
graph TB
Repo["Repository Root"]
Docs["Docs/"]
ProblemStatement["Docs/Problem Statement.md"]
Repo --> Docs
Docs --> ProblemStatement
```

**Diagram sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

## Core Components
This section summarizes the transparency and disclosure requirements derived from the problem statement document.

- Source Citation Requirements
  - Every response must include a single, clear source link.
  - Responses must be limited to a maximum of three sentences.
  - Responses must include a footer indicating the last updated date from sources.

- Last Updated Date Implementation
  - The last updated date must be included in the response footer.
  - The date must reflect the latest update observed in the cited source.

- Response Formatting Standards
  - Responses must be short, factual, and verifiable.
  - Each response must include exactly one citation link.
  - The footer must follow the format: "Last updated from sources: <date>".

- Transparency Framework
  - The assistant must strictly avoid providing investment advice, opinions, or recommendations.
  - Responses must be facts-only and verifiable.
  - The system must use only official public sources (AMC, AMFI, SEBI).
  - For performance-related queries, provide a link to the official factsheet only.

- Disclaimer Requirements
  - A visible disclaimer must be present in the user interface: "Facts-only. No investment advice."

- Refusal Handling
  - Advisory queries must be refused politely and clearly.
  - Refusal responses must reinforce the facts-only limitation.
  - Provide a relevant educational link (e.g., AMFI or SEBI resource).

- Known Limitations
  - The assistant answers only factual queries about mutual fund schemes.
  - It does not provide investment advice or recommendations.
  - It avoids performance comparisons or return calculations.

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

## Architecture Overview
The transparency and disclosure architecture centers on the assistant’s response pipeline, which enforces strict formatting and sourcing rules. The system retrieves information from official public sources and ensures every response adheres to the established transparency requirements.

```mermaid
graph TB
User["User"]
Assistant["Assistant"]
RAG["RAG Pipeline"]
Sources["Official Public Sources<br/>AMC | AMFI | SEBI"]
Output["Response with Citation and Footer"]
User --> Assistant
Assistant --> RAG
RAG --> Sources
Sources --> RAG
RAG --> Output
```

[No sources needed since this diagram shows conceptual workflow, not actual code structure]

## Detailed Component Analysis

### Source Citation Requirements
- Requirement: Every response must include a single, clear source link.
- Constraint: Responses must be limited to a maximum of three sentences.
- Footer requirement: Include a footer with the last updated date from sources.

```mermaid
flowchart TD
Start(["Response Generation"]) --> Validate["Validate Response Constraints"]
Validate --> SentenceLimit{"Sentence Count ≤ 3?"}
SentenceLimit --> |No| Adjust["Adjust Response to Meet Limit"]
SentenceLimit --> |Yes| AddCitation["Add Single Source Link"]
AddCitation --> AddFooter["Add Footer: 'Last updated from sources: <date>'"]
Adjust --> AddCitation
AddFooter --> End(["Compliant Response"])
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Last Updated Date Implementation
- Requirement: Include the last updated date in the response footer.
- Mechanism: Extract the latest update date from the cited source during retrieval.
- Format: Use the standardized footer format: "Last updated from sources: <date>".

```mermaid
sequenceDiagram
participant User as "User"
participant Assistant as "Assistant"
participant RAG as "RAG Pipeline"
participant Source as "Official Public Source"
User->>Assistant : "Query"
Assistant->>RAG : "Retrieve relevant facts"
RAG->>Source : "Fetch content"
Source-->>RAG : "Content with metadata"
RAG-->>Assistant : "Facts + Metadata"
Assistant->>Assistant : "Format response with citation and last updated date"
Assistant-->>User : "Response with footer"
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Response Formatting Standards
- Response must be short, factual, and verifiable.
- Must include exactly one citation link.
- Must include the standardized footer with the last updated date.

```mermaid
classDiagram
class Response {
+string content
+string citation
+string lastUpdatedDate
+formatResponse() string
}
class Formatter {
+applyConstraints(response) Response
+addCitation(response, url) Response
+addFooter(response, date) Response
}
Response --> Formatter : "formatted by"
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Transparency Framework
- Facts-only responses: Avoid investment advice, opinions, or recommendations.
- Official public sources only: Use AMC, AMFI, and SEBI websites.
- Performance queries: Provide a link to the official factsheet only.

```mermaid
flowchart TD
Query["User Query"] --> CheckType{"Is Query Factual?"}
CheckType --> |No| Refuse["Refuse with Educational Link"]
CheckType --> |Yes| Retrieve["Retrieve from Official Sources"]
Retrieve --> Verify["Verify Source Reliability"]
Verify --> Format["Apply Formatting Standards"]
Format --> Respond["Return Response with Citation and Footer"]
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Disclaimer Requirements
- Visible disclaimer: "Facts-only. No investment advice."
- Placement: Include in the user interface alongside welcome messages and example questions.

```mermaid
graph TB
UI["User Interface"]
Disclaimer["Disclaimer: 'Facts-only. No investment advice.'"]
Welcome["Welcome Message"]
Examples["Example Questions"]
UI --> Disclaimer
UI --> Welcome
UI --> Examples
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Refusal Handling
- Advisory queries must be refused politely and clearly.
- Reinforce the facts-only limitation.
- Provide a relevant educational link (e.g., AMFI or SEBI resource).

```mermaid
sequenceDiagram
participant User as "User"
participant Assistant as "Assistant"
participant Education as "Educational Resource"
User->>Assistant : "Advisory Query"
Assistant->>Assistant : "Identify as Advisory"
Assistant->>Assistant : "Prepare Polite Refusal"
Assistant->>Education : "Provide Educational Link"
Assistant-->>User : "Refusal with Educational Link"
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Compliance Validation Processes
- Accuracy validation: Ensure factual correctness against official sources.
- Adherence validation: Confirm response constraints (sentence limit, citation, footer).
- Refusal validation: Verify advisory queries are refused appropriately.
- Quality assurance: Maintain clean, minimal, and user-friendly interface.

```mermaid
flowchart TD
Submission["Response Submission"] --> Accuracy["Accuracy Check"]
Accuracy --> Constraints["Constraint Check"]
Constraints --> Refusal["Refusal Validation"]
Refusal --> QA["Quality Assurance"]
QA --> Approved["Approved Response"]
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Citation Verification Procedures
- Source verification: Confirm the cited URL belongs to official public sources (AMC, AMFI, SEBI).
- Content alignment: Ensure the cited content supports the response.
- Date validation: Verify the last updated date is present and reasonable.

```mermaid
flowchart TD
Citation["Citation Provided"] --> VerifyURL["Verify URL Belongs to Official Sources"]
VerifyURL --> AlignContent["Align Content with Response"]
AlignContent --> ValidateDate["Validate Last Updated Date"]
ValidateDate --> Pass["Pass Verification"]
ValidateDate --> Fail["Fail Verification"]
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Quality Assurance Measures
- Success criteria: Accurate retrieval, strict adherence to facts-only responses, consistent inclusion of valid source citations, proper refusal of advisory queries, and a clean, minimal, and user-friendly interface.
- Known limitations: The assistant answers only factual queries and avoids investment advice or recommendations.

```mermaid
graph TB
SuccessCriteria["Success Criteria"]
Accuracy["Accurate Retrieval"]
Adherence["Strict Adherence to Facts-Only"]
Citations["Consistent Valid Citations"]
Refusal["Proper Refusal of Advisory Queries"]
UI["Clean, Minimal, User-Friendly Interface"]
SuccessCriteria --> Accuracy
SuccessCriteria --> Adherence
SuccessCriteria --> Citations
SuccessCriteria --> Refusal
SuccessCriteria --> UI
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Examples of Compliant Disclosure Formats
- Response with citation and footer: Include a single, clear source link and the standardized footer with the last updated date.
- Example footer format: "Last updated from sources: <date>".
- Example citation: Provide a direct link to the official factsheet or relevant page.

```mermaid
classDiagram
class ExampleResponse {
+string content
+string citation
+string footer
+formatExample() string
}
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Citation Best Practices
- Use official public sources only (AMC, AMFI, SEBI).
- Prefer direct links to primary documents (factsheets, KIM, SID).
- Ensure the cited content directly supports the response.
- Include the last updated date from the source.

```mermaid
flowchart TD
BestPractice["Best Practice"] --> OfficialSources["Use Official Public Sources"]
BestPractice --> DirectLinks["Prefer Direct Links to Primary Documents"]
BestPractice --> ContentSupport["Ensure Content Supports Response"]
BestPractice --> IncludeDate["Include Last Updated Date"]
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### Transparency Reporting Requirements
- Expected deliverables include a README document with setup instructions, selected AMC and schemes, architecture overview (RAG approach), and known limitations.
- The README must also include a disclaimer snippet: "Facts-only. No investment advice."

```mermaid
graph TB
Deliverables["Expected Deliverables"]
README["README Document"]
Setup["Setup Instructions"]
AMC["Selected AMC and Schemes"]
Architecture["Architecture Overview (RAG Approach)"]
Limitations["Known Limitations"]
DisclaimerSnippet["Disclaimer Snippet: 'Facts-only. No investment advice.'"]
Deliverables --> README
README --> Setup
README --> AMC
README --> Architecture
README --> Limitations
Deliverables --> DisclaimerSnippet
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

### User Education About Source Reliability and Information Verification
- Educate users to rely on official public sources for accurate information.
- Encourage users to verify information by visiting the cited source directly.
- Advise users to consult educational resources (AMFI or SEBI) for broader financial literacy.

```mermaid
flowchart TD
Education["User Education"] --> OfficialSources["Reliance on Official Sources"]
Education --> VerifyDirectly["Verify by Visiting Cited Source"]
Education --> ConsultResources["Consult Educational Resources (AMFI/SEBI)"]
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

## Dependency Analysis
The transparency and disclosure requirements depend on:
- Official public sources for factual information retrieval.
- Response formatting constraints enforced by the assistant.
- Disclaimer placement within the user interface.
- Compliance validation processes ensuring adherence to facts-only guidelines.

```mermaid
graph TB
Transparency["Transparency Requirements"]
Sources["Official Public Sources"]
Formatting["Response Formatting"]
Disclaimer["Disclaimer Placement"]
Validation["Compliance Validation"]
Transparency --> Sources
Transparency --> Formatting
Transparency --> Disclaimer
Transparency --> Validation
```

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

## Performance Considerations
- Maintain response speed while enforcing formatting and sourcing constraints.
- Ensure reliable retrieval from official public sources to minimize latency.
- Optimize citation verification to reduce processing overhead.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- If a response fails constraint checks, adjust content to meet sentence limits and ensure a single citation link is included.
- If the last updated date is missing, retrieve the date from the cited source and add it to the footer.
- If a query is flagged as advisory, refuse it politely and provide an educational link.

**Section sources**
- [Problem Statement.md](file://Docs/Problem Statement.md)

## Conclusion
The Mutual Fund FAQ Assistant must prioritize transparency and disclosure by strictly adhering to facts-only responses, using official public sources, and implementing clear citation and footer requirements. Compliance validation, citation verification, and quality assurance measures ensure responsible delivery of verified financial information. User education about source reliability and information verification complements these technical controls to promote informed decision-making.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices
- Compliance checklist:
  - Response includes a single, clear source link.
  - Response is limited to a maximum of three sentences.
  - Response includes the standardized footer with the last updated date.
  - Dismissal of advisory queries is handled politely with an educational link.
  - Known limitations are documented in the README.

[No sources needed since this section provides general guidance]